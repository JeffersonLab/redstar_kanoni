#!/usr/bin/env python3
"""Run standalone devel CORR_SUPERB with the checksum-pinned saved MOD fields."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
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
    except (OSError, ValueError, RuntimeError, ET.ParseError, KeyError) as error:
        parser.error(str(error))
    record = {'status': 'running', 'mode': 'standalone saved-field devel CORR_SUPERB',
              'cwd': str(run), 'source': str(source), 'graph_source': str(graph_source),
              'data_home': str(data), 'threads': args.threads, 'timeout': args.timeout,
              'memory_limit_mb': args.memory_limit_mb, 'contraction_memory_gb': args.contraction_memory_gb,
              'verified_inputs': verified, 'expected': expected, 'commands': [],
              'numerical_readback_validated': False,
              'tools': {name: {'path': str(path), 'sha256': digest(path)} for name, path in tools.items()}}
    env = dict(os.environ, OMP_NUM_THREADS=str(args.threads), OMP_DYNAMIC='FALSE', OMP_MAX_ACTIVE_LEVELS='1',
               VECLIB_MAXIMUM_THREADS='1', OPENBLAS_NUM_THREADS='1', REDSTAR_SB_MEM_GB=str(args.contraction_memory_gb))

    def save():
        temporary = run / 'run.json.tmp'
        temporary.write_text(json.dumps(record, indent=2) + '\n')
        temporary.replace(run / 'run.json')

    def execute(stage, command):
        step = {'stage': stage, 'argv': list(map(str, command)), 'cwd': str(run)}
        record['commands'].append(step)
        save()
        with (run / (stage + '.log')).open('w') as log:
            step['returncode'] = run_limited(step['argv'], cwd=run, env=env, stdout=log,
                                             timeout=args.timeout, memory_limit_mb=args.memory_limit_mb)
        save()
        if step['returncode']:
            raise RuntimeError(stage + ' failed; see ' + str(run / (stage + '.log')))

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
        if importer is None:
            importer = run / 'mod_gauge_to_qio'
            record['chroma_config'] = {'path': str(config), 'sha256': digest(config)}
            execute('build-importer', [sys.executable, ROOT / 'scripts/build_gauge_importer.py', '--chroma-config', config, '--output', importer])
        record['tools']['gauge_importer'] = {'path': str(importer), 'sha256': digest(importer)}
        execute('gauge-import', [importer, data / 'gauge.mod', run / 'gauge.lime'])
        if not re.search(r'\bsquared error=0(?:\.0*)?(?:\s|$)', (run / 'gauge-import.log').read_text()):
            raise RuntimeError('Gauge importer did not confirm an exact QIO roundtrip')
        record['derived_gauge_sha256'] = digest(run / 'gauge.lime')
        execute('chroma', [tools['chroma'], '-i', prepared / 'chroma.xml', '-o', 'chroma.out.xml'])
        ET.parse(run / 'chroma.out.xml')
        log = (run / 'chroma.log').read_text()
        output = run / 'output.sdb1'
        if 'CHROMA: ran successfully' not in log or not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError('Missing Chroma completion marker or nonempty correlator output')
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
