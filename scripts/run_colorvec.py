#!/usr/bin/env python3
"""Run one current Redstar input in a fresh Kanoni output directory."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

DIAGNOSTICS = ('corr_graph_xml', 'eval_graph_xml', 'noneval_graph_xml',
               'vertex_coeff_xml', 'export_dag_xml', 'contraction_info_db',
               'final_eval_graph_db', 'final_noneval_graph_db')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='explicit XML path, e.g. test_inputs/pipi_i1.xml; relative to the current directory')
    parser.add_argument('--database-dir', type=Path, default=os.environ.get('KANONI_DATA_DIR'),
                        help='prepared SDB home (default: KANONI_DATA_DIR or data/)')
    parser.add_argument('--threads', type=int, default=os.environ.get('OMP_NUM_THREADS', '4'))
    parser.add_argument('--keep-diagnostics', action='store_true',
                        help='retain the input diagnostic level and graph XML/database dumps')
    args = parser.parse_args()
    if args.threads < 1:
        parser.error('--threads must be positive')
    root = Path(__file__).resolve().parents[1]
    supplied = args.input.expanduser()
    if not supplied.is_file():
        parser.error('Redstar input does not exist: ' + str(supplied) +
                     '; pass an explicit path such as test_inputs/pipi_i1.xml')
    source = supplied.resolve()
    tree = ET.parse(source)
    xml = tree.getroot()
    if xml.tag != 'RedstarNPt' or xml.findtext('Param/version') != '14' or xml.find('NPointList') is None:
        parser.error('Expected RedstarNPt v14 with a root NPointList; see scripts/migrate_inputs.py')
    if xml.findall('.//mom_type'):
        parser.error('Legacy mom_type keys require typed SUNClass conversion')
    names = ('redstar_corr_graph', 'redstar_npt')
    bindir = os.environ.get('REDSTAR_BIN')
    if bindir:
        programs = [Path(bindir).expanduser() / name for name in names]
    else:
        located = [shutil.which(name) for name in names]
        programs = [Path(p) for p in located] if all(located) else [root.parent / 'redstar.devel/build/src' / name for name in names]
    if not all(p.is_file() and os.access(p, os.X_OK) for p in programs):
        parser.error('Set REDSTAR_BIN to one installed bin or build/src directory, or put the tools on PATH')
    programs = [p.resolve() for p in programs]
    data = (args.database_dir or root / 'data').expanduser().absolute()
    if not data.is_dir() and args.database_dir is None:
        subprocess.run([str(root / 'setup-data')], check=True)
    if data.is_symlink():
        parser.error('Database directory must be a real directory: ' + str(data))
    if not data.is_dir():
        parser.error('Missing prepared database home: ' + str(data) + '; run ./setup-data first')
    data = data.resolve()
    database_entries = []
    # Resolve all inputs before creating a run; never derive paths from a personal Downloads alias.
    for group in xml.findall('ColorVec/DBFiles/*'):
        for item in list(group.findall('elem')):
            if not (item.text or '').strip():
                group.remove(item)
                continue
            path = data / Path(item.text.strip()).name
            if not path.is_file() or path.is_symlink():
                parser.error('Source database must be a regular file: ' + str(path))
            database_entries.append((item, path))
    if not args.keep_diagnostics:
        xml.find('Param/diagnostic_level').text = '0'
        for name in DIAGNOSTICS:
            for item in xml.findall('DBFiles/' + name):
                xml.find('DBFiles').remove(item)
    else:
        # Even explicit diagnostics stay inside the fresh run, regardless of template paths.
        for name in DIAGNOSTICS:
            item = xml.find('DBFiles/' + name)
            if item is not None:
                item.text = name + ('.xml' if name.endswith('_xml') else '.sdb1')
    for name, value in [('corr_graph_bin', 'corr_graph.bin'), ('output_db', 'output.npt.sdb1')]:
        item = xml.find('DBFiles/' + name)
        if item is None:
            item = ET.SubElement(xml.find('DBFiles'), name)
        item.text = value
    runs = root / 'runs'
    runs.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=source.stem + '-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-', dir=runs))
    # Copy portable support inputs, keeping all output away from the checkout originals.
    for item in (root / 'test_inputs').iterdir():
        if item.name in ('data', 'data-manifest.json'):
            continue
        if item.is_dir():
            shutil.copytree(item, run / item.name)
        elif item.is_file():
            shutil.copyfile(item, run / item.name)
    for item in source.parent.iterdir():
        if not (run / item.name).exists() and item.is_file() and item.suffix in ('.list', '.dat'):
            shutil.copyfile(item, run / item.name)
    for item, database in database_entries:
        item.text = os.path.relpath(database.resolve(), run.resolve())
    ET.indent(tree, space='  ')
    tree.write(run / 'input.xml', encoding='utf-8', xml_declaration=True)
    env = dict(os.environ, OMP_NUM_THREADS=str(args.threads), OMP_DYNAMIC='FALSE',
               OMP_MAX_ACTIVE_LEVELS='1', VECLIB_MAXIMUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    record = dict(status='running', source=str(source), input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  data_home=str(data), resolved_data_home=str(data.resolve()), threads=args.threads,
                  keep_diagnostics=args.keep_diagnostics, commands=[], numerical_readback_validated=False)
    def save():
        (run / 'run.json').write_text(json.dumps(record, indent=2) + '\n')
    save()
    print('Run directory: ' + str(run), flush=True)
    try:
        for program, phase in zip(programs, ('graph', 'npt')):
            log = run / (phase + '.log')
            command = [str(program), 'input.xml', phase + '.out.xml']
            step = dict(argv=command, log=str(log)); record['commands'].append(step); save()
            with log.open('wb') as stream:
                result = subprocess.run(command, cwd=run, env=env, stdout=stream, stderr=subprocess.STDOUT)
            step['returncode'] = result.returncode; save()
            if result.returncode:
                raise RuntimeError('{} failed ({}); see {}'.format(program.name, result.returncode, log))
        if not (run / 'corr_graph.bin').is_file() or not (run / 'output.npt.sdb1').is_file():
            raise RuntimeError('Executables returned success without the expected graph/correlator output')
        record['status'] = 'executables_passed'; save()
    except Exception as error:
        record.update(status='failed', error=str(error)); save(); raise
    print('Completed: ' + str(run))
    print('Use scripts/validate_inputs.py for independent key and finite-value readback checks.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError, ET.ParseError) as error:
        sys.exit('run_colorvec: ' + str(error))
