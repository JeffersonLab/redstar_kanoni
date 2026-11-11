#!/usr/bin/env python3
"""Run standalone devel CORR_SUPERB with the checksum-pinned saved MOD fields."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from contraction_workflow import graph_summary
from redstar_runtime import required_tools, run_limited

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def regular_file(path):
    path = path.expanduser().absolute()
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected a regular file, not a symlink: ' + str(path))
    return path


def mpi_plan(args, config):
    """The driver runs once; the launcher only executes guarded MPI stages."""
    if any(name in os.environ for name in ('OMPI_COMM_WORLD_RANK', 'PMI_RANK', 'PMIX_RANK', 'MV2_COMM_WORLD_RANK')):
        raise ValueError('Run the driver once outside mpiexec; use --mpi-ranks instead')
    if args.mpi_ranks is None:
        if args.mpi_arg or args.mpiexec:
            raise ValueError('--mpiexec/--mpi-arg require --mpi-ranks')
        return None
    if args.mpi_ranks < 1 or 1024 % args.mpi_ranks:
        raise ValueError('--mpi-ranks must be positive and divide the saved lattice volume 1024')
    selected = args.mpiexec or os.environ.get('MPIEXEC')
    if not selected:
        raise ValueError('Set MPIEXEC or --mpiexec to the matching absolute MPI launcher path')
    launcher = Path(selected).expanduser()
    if not launcher.is_absolute() or not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise ValueError('MPIEXEC must be an existing absolute executable path')
    rank_flags = ('-n', '-np', '--np', '--n', '--num-procs')
    if any(arg.split('=', 1)[0] in rank_flags or arg in ('--', ':') for arg in args.mpi_arg):
        raise ValueError('Set rank count only through --mpi-ranks')
    if not config.is_file():
        raise ValueError('MPI mode requires CHROMA_BIN/chroma-config')
    prefix = [str(config)] if os.access(config, os.X_OK) else ['sh', str(config)]
    arch = subprocess.check_output(prefix + ['--parallel-arch'], text=True, timeout=30).strip()
    if arch != 'parscalar':
        raise ValueError('MPI mode requires QDP parscalar; selected Chroma reports ' + arch)
    return {'ranks': args.mpi_ranks, 'launcher': str(launcher), 'launcher_args': args.mpi_arg,
            'launcher_sha256': digest(launcher), 'parallel_arch': arch,
            'config': str(config), 'config_sha256': digest(config), 'rank_resources': {}}


def verify_mpi_layout(path, ranks):
    geometry = ET.parse(path).find('ProgramInfo/Setgeom')
    if geometry is None:
        raise RuntimeError('Missing Chroma MPI geometry in ' + str(path))
    logical = list(map(int, geometry.findtext('logical_size', '').split()))
    subgrid = list(map(int, geometry.findtext('subgrid_size', '').split()))
    if len(logical) != 4 or min(logical) < 1 or math.prod(logical) != ranks:
        raise RuntimeError('Chroma did not run with the requested MPI rank count')
    if len(subgrid) != 4 or min(subgrid) < 1 or [a * b for a, b in zip(logical, subgrid)] != [4, 4, 4, 16]:
        raise RuntimeError('Chroma MPI subgrid does not reconstruct the saved lattice')
    return {'logical_size': logical, 'subgrid_size': subgrid, 'ranks': ranks}


def prepare_sources(chroma_source, graph_source, data):
    """Validate inputs before creating any output; do not alter physics settings."""
    chroma = ET.parse(chroma_source)
    graph = ET.parse(graph_source)
    x, g = chroma.getroot(), graph.getroot()
    measurements = x.findall('Param/InlineMeasurements/elem')
    if x.tag != 'chroma' or [m.findtext('Name') for m in measurements] != ['CORR_SUPERB']:
        raise ValueError('Expected one CORR_SUPERB measurement using saved fields; generated-vector inputs use run_corr_superb.py')
    if g.tag != 'RedstarNPt' or g.findtext('Param/version') != '14' or g.find('ColorVec') is not None:
        raise ValueError('Expected graph-only RedstarNPt v14 XML with a root NPointList')
    points = g.findall('NPointList/elem')
    if not points or g.findall('.//mom_type'):
        raise ValueError('Graph selection is empty or uses legacy momentum keys')
    corr = measurements[0]
    param, named = corr.find('Param'), corr.find('NamedObject')
    if param is None or named is None or g.find('DBFiles') is None:
        raise ValueError('Missing CORR_SUPERB Param/NamedObject or graph DBFiles')
    manifest = json.loads((ROOT / 'test_inputs/mod-manifest.json').read_text())
    entries = {e['name']: e for e in manifest['files']}
    verified = {}
    for name in ('colorvec.mod', 'gauge.mod'):
        entry = entries[name]
        path = regular_file(data / name)
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError('Saved MOD checksum/size mismatch: ' + str(path))
        verified[str(path)] = {'bytes': entry['bytes'], 'sha256': entry['sha256']}
    lattice = list(map(int, g.findtext('Param/Layout/lattSize', '').split()))
    chroma_lattice = list(map(int, x.findtext('Param/nrow', '').split()))
    saved_lattice = list(map(int, entries['colorvec.mod']['metadata']['lattSize'].split()))
    if lattice != chroma_lattice or lattice != saved_lattice or lattice != [4, 4, 4, 16]:
        raise ValueError('Graph, Chroma and pinned MOD geometry must all be 4 x 4 x 4 x 16')
    nt = int(g.findtext('Param/Nt_corr', '0'))
    origin = int(g.findtext('Param/t_origin', '-1'))
    vectors = int(param.findtext('num_vecs', '0'))
    if nt < 1 or int(param.findtext('Nt_forward', '0')) != nt:
        raise ValueError('Graph Nt_corr and Chroma Nt_forward must match and be positive')
    if not 0 <= origin < lattice[-1] or int(param.findtext('t_origin', '-1')) != origin:
        raise ValueError('Graph and Chroma source origins must match')
    if g.findtext('Param/Layout/decayDir') != entries['colorvec.mod']['metadata']['decay_dir']:
        raise ValueError('Graph and saved fields have different decay directions')
    if not 1 <= vectors <= int(entries['colorvec.mod']['metadata']['num_vecs']):
        raise ValueError('Chroma vector count exceeds the saved MOD coverage')
    if g.findtext('Param/ensemble') != param.findtext('ensemble'):
        raise ValueError('Graph and Chroma ensemble labels differ')
    for flag in ('average_1pt_diagrams', 'zeroUnsmearedGraphsP'):
        if param.find(flag) is not None and param.findtext(flag) != g.findtext('Param/' + flag):
            raise ValueError('Graph and Chroma physics flag differs: ' + flag)
    if any(n.text == 'true' for n in x.findall('.//fake_data_modeP')):
        raise ValueError('The saved-field runner does not support fake-data mode')
    if x.findtext('Cfg/cfg_type') != 'SZINQIO' or x.findtext('Cfg/cfg_file') != 'gauge.lime':
        raise ValueError('Expected SZINQIO gauge.lime from the matching saved gauge.mod')
    colors = named.findall('colorvec_files/elem')
    if len(colors) != 1 or Path((colors[0].text or '').strip()).name != 'colorvec.mod':
        raise ValueError('Expected exactly one saved colorvec.mod input')
    supplied_color = Path(colors[0].text.strip()).expanduser()
    if supplied_color.is_absolute() and supplied_color.resolve() != data / 'colorvec.mod':
        raise ValueError('Absolute color-vector path differs from --database-dir')
    colors[0].text = str(data / 'colorvec.mod')
    for group in ('props', 'genprops', 'mesons', 'baryons'):
        for node in param.findall(group + '/elem'):
            path = Path((node.text or '').strip()).expanduser()
            if not (node.text or '').strip():
                raise ValueError('Empty tensor filename in ' + group)
            if not path.is_absolute():
                if len(path.parts) != 1:
                    raise ValueError('Use an absolute tensor path or a basename in --database-dir: ' + str(path))
                path = data / path
            path = regular_file(path)
            node.text = str(path)
            verified[str(path)] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
    support = []
    for node in g.findall('DBFiles/proj_op_xmls/elem'):
        path = regular_file(graph_source.parent / (node.text or '').strip())
        support.append(path)
    expected = {'correlators': len(points), 'time_samples': nt, 'symmetry_zero': False}
    metadata = graph_source.parent / 'case.json'
    if graph_source.name == 'graph.xml' and metadata.is_file():
        case = json.loads(metadata.read_text())
        if case['correlators'] != len(points) or case['time_samples'] != nt or case['t_origin'] != origin or case['num_vecs'] != vectors:
            raise ValueError('Graph/Chroma coverage differs from the adjacent case.json')
        expected['symmetry_zero'] = case.get('symmetry_zero', False)
    return chroma, graph, expected, verified, support


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='explicit Chroma XML path, relative to the caller')
    parser.add_argument('--graph-input', type=Path, required=True, help='explicit graph-only RedstarNPt v14 XML')
    parser.add_argument('--redstar-bin', type=Path, help='absolute bin directory (or REDSTAR_BIN)')
    parser.add_argument('--chroma-bin', type=Path, help='absolute bin directory (or CHROMA_BIN)')
    parser.add_argument('--database-dir', type=Path, default=os.environ.get('KANONI_DATA_DIR'), help='saved MOD home (default: KANONI_DATA_DIR or data/)')
    parser.add_argument('--gauge-importer', type=Path, help='prebuilt compatible MOD-to-QIO converter; otherwise build with CHROMA_BIN/chroma-config')
    parser.add_argument('--output', type=Path, help='fresh output directory; default: unique runs/chroma-* directory')
    parser.add_argument('--threads', type=int, default=os.environ.get('OMP_NUM_THREADS', '4'))
    parser.add_argument('--timeout', type=int, default=1800, help='seconds per executable')
    parser.add_argument('--memory-limit-mb', type=int, default=8192, help='per-process RSS cap; 0 disables')
    parser.add_argument('--contraction-memory-gb', type=int, default=6)
    parser.add_argument('--mpi-ranks', type=int, help='launch Chroma with this many MPI ranks, including 1 for an MPI baseline')
    parser.add_argument('--mpiexec', type=Path, help='matching absolute MPI launcher path (or MPIEXEC)')
    parser.add_argument('--mpi-arg', action='append', default=[], help='repeatable launcher argument, e.g. --mpi-arg=--bind-to --mpi-arg=none')
    args = parser.parse_args(argv)
    if min(args.threads, args.timeout, args.contraction_memory_gb) < 1 or args.memory_limit_mb < 0:
        parser.error('threads, timeout and contraction budget must be positive; RSS cap must be nonnegative')
    try:
        source, graph_source = regular_file(args.input), regular_file(args.graph_input)
        tools = required_tools('redstar', ('redstar_corr_graph', 'view_corr_graph'), args.redstar_bin)
        tools.update(required_tools('chroma', ('chroma',), args.chroma_bin))
        data = (args.database_dir or ROOT / 'data').expanduser().absolute()
        if data.is_symlink() or not data.is_dir():
            raise ValueError('Saved MOD home must be a real directory: ' + str(data))
        data = data.resolve()
        chroma, graph, expected, verified, support = prepare_sources(source, graph_source, data)
        importer = args.gauge_importer.expanduser().absolute() if args.gauge_importer else None
        if importer is not None and (not importer.is_file() or not os.access(importer, os.X_OK)):
            raise ValueError('Gauge importer is not executable: ' + str(importer))
        config = tools['chroma'].parent / 'chroma-config'
        mpi = mpi_plan(args, config)
        if importer is None and not config.is_file():
            raise ValueError('Missing CHROMA_BIN/chroma-config; supply --gauge-importer or select a complete installed Chroma bin directory')
        if args.output:
            run = args.output.expanduser().absolute()
            if run.exists() or run.is_symlink():
                raise ValueError('Output exists; choose a fresh directory: ' + str(run))
        else:
            (ROOT / 'runs').mkdir(exist_ok=True)
            run = Path(tempfile.mkdtemp(prefix='chroma-' + graph_source.stem + '-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-', dir=ROOT / 'runs'))
        prepared = ROOT / 'run_inputs' / run.name
        if prepared.exists() or prepared.is_symlink():
            raise ValueError('Prepared inputs already exist; choose a new output name: ' + str(prepared))
        run.mkdir(parents=True, exist_ok=args.output is None)
        prepared.mkdir(parents=True)
    except (OSError, ValueError, RuntimeError, ET.ParseError, KeyError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    record = {'status': 'running', 'mode': 'standalone saved-field devel CORR_SUPERB',
              'cwd': str(run), 'source': str(source), 'graph_source': str(graph_source),
              'data_home': str(data), 'threads': args.threads, 'timeout': args.timeout,
              'memory_limit_mb': args.memory_limit_mb, 'contraction_memory_gb': args.contraction_memory_gb,
              'verified_inputs': verified, 'expected': expected, 'commands': [],
              'numerical_readback_validated': False,
              'tools': {name: {'path': str(path), 'sha256': digest(path)} for name, path in tools.items()}}
    if mpi is not None:
        record['mpi'] = mpi
    env = dict(os.environ, OMP_NUM_THREADS=str(args.threads), OMP_DYNAMIC='FALSE', OMP_MAX_ACTIVE_LEVELS='1',
               VECLIB_MAXIMUM_THREADS='1', OPENBLAS_NUM_THREADS='1', REDSTAR_SB_MEM_GB=str(args.contraction_memory_gb))

    def save():
        temporary = run / 'run.json.tmp'
        temporary.write_text(json.dumps(record, indent=2) + '\n')
        temporary.replace(run / 'run.json')

    def execute(stage, command, ranks=None):
        if ranks is not None:
            command = [mpi['launcher'], *mpi['launcher_args'], '-n', str(ranks), sys.executable,
                       ROOT / 'scripts/run_mpi_rank.py', '--stage', stage, '--ranks', str(ranks),
                       '--threads', str(args.threads), '--timeout', str(args.timeout),
                       '--memory-limit-mb', str(args.memory_limit_mb),
                       '--contraction-memory-gb', str(args.contraction_memory_gb), '--', *command]
        step = {'stage': stage, 'argv': list(map(str, command)), 'cwd': str(run)}
        record['commands'].append(step)
        save()
        try:
            with (run / (stage + '.log')).open('w') as log:
                step['returncode'] = run_limited(step['argv'], cwd=run, env=env, stdout=log,
                                                 timeout=args.timeout + (30 if ranks is not None else 0),
                                                 memory_limit_mb=0 if ranks is not None else args.memory_limit_mb,
                                                 terminate_grace_seconds=5 if ranks is not None else 0)
        finally:
            if ranks is not None:
                resources = []
                for rank in range(ranks):
                    path = run / ('resource-{}-rank-{}.json'.format(stage, rank))
                    if path.is_file():
                        resources.append(json.loads(path.read_text()))
                mpi['rank_resources'][stage] = resources
            save()
        if step['returncode']:
            raise RuntimeError(stage + ' failed; see ' + str(run / (stage + '.log')))
        if ranks is not None:
            if len(resources) != ranks or any(row['rank'] != rank or row['ranks'] != ranks
                    or row.get('returncode') != 0 or row['status'] != 'passed' for rank, row in enumerate(resources)):
                raise RuntimeError('Missing or unsuccessful actual MPI rank records for ' + stage)

    print('Run directory: ' + str(run), flush=True)
    save()
    try:
        shutil.copyfile(source, prepared / 'source-chroma.xml')
        shutil.copyfile(graph_source, prepared / 'source-graph.xml')
        db = graph.find('DBFiles')
        projected = deepcopy(db.find('proj_op_xmls'))
        db.clear()
        if projected is not None:
            db.append(projected)
        for index, (path, node) in enumerate(zip(support, db.findall('proj_op_xmls/elem'))):
            snapshot = prepared / ('weights-{:03d}.xml'.format(index))
            shutil.copyfile(path, snapshot)
            node.text = str(snapshot)
            record['verified_inputs'][str(path)] = {'bytes': path.stat().st_size, 'sha256': digest(snapshot)}
        ET.SubElement(db, 'corr_graph_bin').text = 'corr_graph.bin'
        diagnostic = graph.find('Param/diagnostic_level')
        if diagnostic is None:
            diagnostic = ET.SubElement(graph.find('Param'), 'diagnostic_level')
        diagnostic.text = '0'
        corr = chroma.find('Param/InlineMeasurements/elem')
        named = corr.find('NamedObject')
        for tag, value in [('corr_graph_file', 'corr_graph.bin'), ('corr_file', 'output.sdb1')]:
            node = named.find(tag)
            if node is None:
                node = ET.SubElement(named, tag)
            node.text = value
        chroma.find('Cfg/cfg_file').text = 'gauge.lime'
        xml_report = corr.find('xml_file')
        if xml_report is not None and (xml_report.text or '').strip():
            xml_report.text = 'corr.measurement.xml'
        record['prepared_inputs'] = {}
        for label, tree in [('graph', graph), ('chroma', chroma)]:
            path = prepared / (label + '.xml')
            tree.write(path, encoding='utf-8', xml_declaration=True)
            record['prepared_inputs'][label] = {'path': str(path), 'sha256': digest(path)}
        record['original_inputs'] = {str(path): digest(path) for path in (prepared / 'source-chroma.xml', prepared / 'source-graph.xml')}
        save()
        execute('graph', [tools['redstar_corr_graph'], prepared / 'graph.xml', 'graph.out.xml'])
        ET.parse(run / 'graph.out.xml')
        if not (run / 'corr_graph.bin').is_file():
            raise RuntimeError('Graph generator did not produce corr_graph.bin')
        execute('view', [tools['view_corr_graph'], 'corr_graph.bin'])
        record['graph'] = graph_summary((run / 'view.log').read_text(), expected)
        record['graph_sha256'] = digest(run / 'corr_graph.bin')
        save()
        if mpi is not None:
            probe = run / 'chroma_mpi_probe'
            execute('build-mpi-probe', [sys.executable, ROOT / 'scripts/build_chroma_mpi_probe.py',
                                        '--chroma-config', config, '--output', probe])
            execute('mpi-runtime', [probe, str(mpi['ranks']), str(args.threads)], ranks=mpi['ranks'])
            runtime = [json.loads((run / ('mpi-runtime-rank-{}.json'.format(rank))).read_text()) for rank in range(mpi['ranks'])]
            for rank, row in enumerate(runtime):
                if (row['rank'] != rank or row['mpi_ranks'] != mpi['ranks'] or row['qmp_rank'] != rank
                        or row['qmp_nodes'] != mpi['ranks'] or row['openmp_threads'] != args.threads
                        or row['global_sum'] != 1024 or row['local_volume'] * mpi['ranks'] != 1024):
                    raise RuntimeError('QDP/QMP/MPI runtime probe did not confirm the selected profile')
            mpi['runtime_probe'] = runtime
            # Verify the selected Chroma binary itself, before the real gauge
            # and contraction job. Multiple ranks reject a stale SINGLE binary.
            layout = ET.Element('chroma')
            param = ET.SubElement(layout, 'Param')
            ET.SubElement(param, 'InlineMeasurements')
            ET.SubElement(param, 'nrow').text = '4 4 4 16'
            if chroma.find('RNG') is not None:
                layout.append(deepcopy(chroma.find('RNG')))
            cfg = ET.SubElement(layout, 'Cfg')
            ET.SubElement(cfg, 'cfg_type').text = 'WEAK_FIELD'
            ET.SubElement(cfg, 'cfg_file').text = 'dummy'
            layout_input = prepared / 'mpi-layout.xml'
            ET.ElementTree(layout).write(layout_input, encoding='utf-8', xml_declaration=True)
            record['prepared_inputs']['mpi_layout'] = {'path': str(layout_input), 'sha256': digest(layout_input)}
            execute('mpi-layout', [tools['chroma'], '-i', layout_input, '-o', 'mpi-layout.out.xml'], ranks=mpi['ranks'])
            mpi['layout_probe'] = verify_mpi_layout(run / 'mpi-layout.out.xml', mpi['ranks'])
            save()
        if importer is None:
            importer = run / 'mod_gauge_to_qio'
            record['chroma_config'] = {'path': str(config), 'sha256': digest(config)}
            execute('build-importer', [sys.executable, ROOT / 'scripts/build_gauge_importer.py', '--chroma-config', config, '--output', importer])
        record['tools']['gauge_importer'] = {'path': str(importer), 'sha256': digest(importer)}
        execute('gauge-import', [importer, data / 'gauge.mod', run / 'gauge.lime'], ranks=1 if mpi is not None else None)
        if not re.search(r'\bsquared error=0(?:\.0*)?(?:\s|$)', (run / 'gauge-import.log').read_text()):
            raise RuntimeError('Gauge importer did not confirm an exact QIO roundtrip')
        record['derived_gauge_sha256'] = digest(run / 'gauge.lime')
        execute('chroma', [tools['chroma'], '-i', prepared / 'chroma.xml', '-o', 'chroma.out.xml'],
                ranks=mpi['ranks'] if mpi is not None else None)
        ET.parse(run / 'chroma.out.xml')
        log = (run / 'chroma.log').read_text()
        output = run / 'output.sdb1'
        if 'CHROMA: ran successfully' not in log or not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError('Missing Chroma completion marker or nonempty correlator output')
        if mpi is not None:
            mpi['chroma_geometry'] = verify_mpi_layout(run / 'chroma.out.xml', mpi['ranks'])
            if args.memory_limit_mb and any(row['rss_samples'] < 1 for row in mpi['rank_resources']['chroma']):
                raise RuntimeError('Actual Chroma rank RSS was not observed')
        record.update(status='executables_passed', CG_solves=log.count('CG_SOLVER_TIME:'), output_sha256=digest(output))
        save()
    except Exception as error:
        record.update(status='failed', error=str(error))
        save()
        print(str(error), file=sys.stderr)
        return 1
    print('Completed: ' + str(run))
    print('output.sdb1 contains the correlators; independent numerical readback is a separate validation step.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
