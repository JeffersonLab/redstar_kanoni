#!/usr/bin/env python3
"""Run combined development XMLs, validate, and compare saved numerical baselines.

Production normally uses separate corr_graph and npt inputs; these test XMLs
combine NPointList and ColorVec settings as a development convenience.
Requires Python 3.11+ (or tomli on Python 3.9/3.10).
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

from compare_correlators import compare
from redstar_runtime import OUTPUT_DATABASE, configured_tools, load_toml
from validate_inputs import main as validate

ROOT = Path(__file__).resolve().parents[1]
REGRESSIONS = ROOT / 'regressions'


def read_tests(path):
    config = load_toml(path)
    if config.get('schema_version') != 1:
        raise ValueError('Expected test-list schema_version = 1')
    tests = [({'xml': test} if isinstance(test, str) else test) for test in config.get('tests', [])]
    names = [test['xml'] for test in tests]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate XML names in test list')
    for name in names:
        if Path(name).name != name or not name.endswith('.xml'):
            raise ValueError('Test-list XMLs must be filenames ending in .xml')
    return tests


def write_tests(path, tests):
    excluded = load_toml(path).get('excluded', []) if path.exists() else []
    active = {test['xml'] for test in tests}
    excluded = [test for test in excluded if test['xml'] not in active]
    lines = ['# Reproducible baselines; explicit exclusions and reasons follow the active list.', 'schema_version = 1']
    if not tests:
        lines.append('tests = []')
    for test in sorted(tests, key=lambda test: test['xml']):
        lines.append('\n[[tests]]')
        for key in ('xml', 'kind', 'sha256'):
            if key in test:
                lines.append(key + ' = ' + json.dumps(test[key]))
    for test in sorted(excluded, key=lambda test: test['xml']):
        lines.append('\n[[excluded]]')
        for key, value in test.items():
            lines.append(key + ' = ' + json.dumps(value))
    temp = path.with_suffix('.tmp')
    temp.write_text('\n'.join(lines) + '\n')
    temp.replace(path)


def baseline_directory(source, root=None):
    # Path.stem strips only the final suffix: fred.george.xml -> fred.george.
    return (root or REGRESSIONS) / source.stem


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xml', nargs='?', type=Path, help='one explicit XML path; otherwise run --list')
    parser.add_argument('--tools', type=Path, default=REGRESSIONS/'tools.toml', help='separate executable-path TOML')
    parser.add_argument('--baseline-root',type=Path,default=REGRESSIONS,help='separate destination/reference inventory; never overwrite')
    parser.add_argument('--input-dir',type=Path,default=ROOT/'test_inputs',help='directory containing the selected XML filenames')
    parser.add_argument('--database-dir',type=Path,help='explicit regenerated data directory')
    parser.add_argument('--data-manifest',type=Path,help='checksum manifest for the selected dataset')
    parser.add_argument('--list', type=Path, default=REGRESSIONS/'tests.toml', help='test-list TOML (XML filenames in test_inputs)')
    parser.add_argument('--establish', action='store_true', help='save only validated new baselines and add them to --list; never overwrite')
    parser.add_argument('--all', action='store_true', help='attempt every RedstarNPt XML in test_inputs (including known failures)')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--timeout', type=int, default=120, help='seconds per executable')
    parser.add_argument('--memory-limit-mb', type=int, default=8192, help='per-process RSS cap, 0 disables')
    parser.add_argument('--tolerance', type=float, default=1e-12)
    args = parser.parse_args(argv)
    if args.xml and args.all:
        parser.error('Choose a single XML or --all')
    tests = read_tests(args.list)
    try:
        tools = configured_tools(args.tools)
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))
    if args.xml:
        files = [args.xml.expanduser().absolute()]
    elif args.all:
        files = [p for p in sorted(args.input_dir.glob('*.xml')) if ET.parse(p).getroot().tag == 'RedstarNPt']
    else:
        files = [args.input_dir/test['xml'] for test in tests]
    if not files:
        parser.error('No tests selected; establish with --all or pass an XML path')
    if args.establish:
        for source in files:
            if baseline_directory(source,args.baseline_root).exists():
                parser.error('Baseline already exists; preserve it: ' + str(baseline_directory(source,args.baseline_root)))
    validation_args = ['--tools', str(args.tools), '--threads', str(args.threads),
                       '--timeout', str(args.timeout), '--memory-limit-mb', str(args.memory_limit_mb)]
    args.baseline_root.mkdir(parents=True,exist_ok=True)
    if args.database_dir:validation_args += ['--database-dir',str(args.database_dir)]
    if args.data_manifest:validation_args += ['--data-manifest',str(args.data_manifest)]
    if not args.establish:
        validation_args += ['--reference-dir', str(args.baseline_root), '--relative-tolerance', str(args.tolerance)]
    output, report = validate(validation_args + list(map(str, files)))
    if not args.establish:
        pinned = {test['xml']: test for test in tests}
        for source, case in zip(files, report['cases']):
            baseline = baseline_directory(source,args.baseline_root)/OUTPUT_DATABASE
            entry = pinned.get(source.name)
            if entry and entry.get('sha256') and baseline.is_file() and hashlib.sha256(baseline.read_bytes()).hexdigest() != entry['sha256']:
                case.update(status='failed',error='Saved baseline checksum differs from test-list pin')
        report['summary'] = {status: sum(case['status'] == status for case in report['cases'])
                             for status in ('passed', 'passed_fake_data', 'passed_symmetry_zero', 'failed')}
        if report['summary']['failed']:
            report['status'] = 'attention_required'
        (output/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    summary = {'mode': 'establish' if args.establish else 'compare', 'validation_report': str(output/'results.json'),
               'started_from_tools': str(args.tools.absolute()), 'cases': []}
    exporter = tools.get('exporter')
    for source, case in zip(files, report['cases']):
        result = {'xml': source.name, 'status': case['status'], 'error': case.get('error')}
        summary['cases'].append(result)
        if not args.establish or not case['status'].startswith('passed'):
            continue
        try:
            if case.get('fake_data_mode') == 'true' and ET.parse(source).findtext('ColorVec/Param/fake_data_seed', '-1').strip() == '-1':
                raise RuntimeError('Unseeded/time-seeded fake data cannot establish a reproducible numerical baseline; run evidence is preserved')
            if exporter is None:
                exporter = output/'baseline-exporter'
                if not exporter.exists():
                    import subprocess
                    with (output/'build-baseline-exporter.log').open('w') as log:
                        subprocess.run([sys.executable, str(ROOT/'scripts/build_exporter.py'), '--adat-config',
                                        report['adat_config'],
                                        '--output', str(exporter)], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=args.timeout)
            run = output/source.stem
            database = run/OUTPUT_DATABASE
            # Independently verify numbered readback and dbutil comparison before promotion.
            compare(database, database, Path(report['dbutil']), exporter, run/'baseline-check', args.tolerance, args.timeout)
            destination = baseline_directory(source,args.baseline_root)
            temporary = Path(tempfile.mkdtemp(prefix='.baseline-', dir=args.baseline_root))
            try:
                shutil.copy2(database, temporary/OUTPUT_DATABASE)
                (temporary/OUTPUT_DATABASE).chmod(0o444)
                shutil.copy2(run/'input.xml', temporary/'input.xml')
                if (run/'weights').exists():
                    shutil.copytree(run/'weights', temporary/'weights')
                digest = hashlib.sha256((temporary/OUTPUT_DATABASE).read_bytes()).hexdigest()
                metadata = {'created_at': datetime.now().astimezone().isoformat(), 'xml': source.name,
                            'sha256': digest, 'validation_report': str(output/'results.json'),
                            'case': case, 'programs': report['programs'], 'program_sha256': report['program_sha256'],
                            'dataset': report['dataset'], 'verified_data': report['verified_data'],
                            'readback_report': str(run/'baseline-check/comparison.json')}
                (temporary/'baseline.json').write_text(json.dumps(metadata, indent=2)+'\n')
                if destination.exists():
                    raise RuntimeError('Refusing to overwrite baseline ' + str(destination))
                temporary.rename(destination)
            except BaseException:
                # Preserve staging evidence for diagnosis rather than removing any data.
                raise
            tests = [test for test in tests if test['xml'] != source.name]
            tests.append({'xml': source.name, 'kind': case['status'], 'sha256': digest})
            write_tests(args.list, tests)
            result.update(status='baseline_established', baseline=str(destination/OUTPUT_DATABASE), sha256=digest)
        except Exception as error:
            result.update(status='failed', error=str(error))
        print(source.name, result['status'], flush=True)
    summary['failed'] = sum(case['status'] == 'failed' for case in summary['cases'])
    (output/'regressions.json').write_text(json.dumps(summary, indent=2)+'\n')
    print('Regression report:', output/'regressions.json', flush=True)
    return bool(summary['failed'])


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        sys.exit(str(error))
