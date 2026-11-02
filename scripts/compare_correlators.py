#!/usr/bin/env python3
"""Compare saved correlators with exact key coverage and finite-value checks."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def definition(node, tag=None):
    return (tag or node.tag, ' '.join((node.text or '').split()),
            tuple(definition(child) for child in node))


def inspect_export(directory, keys_file):
    keys = [definition(k) for k in ET.parse(keys_file).getroot()]
    entries = ET.parse(directory / 'index.xml').getroot().findall('elem')
    indexed = [definition(e.find('Key'), 'elem') for e in entries]
    if not keys or len(set(keys)) != len(keys) or len(set(indexed)) != len(indexed) or set(keys) != set(indexed):
        raise RuntimeError('Empty, duplicate, or inconsistent exported keys')
    shapes = {}
    filenames = set()
    for entry, key in zip(entries, indexed):
        filename = entry.findtext('filename') or ''
        if Path(filename).name != filename or filename in filenames:
            raise RuntimeError('Invalid/duplicate export filename')
        filenames.add(filename)
        lines = (directory / filename).read_text().splitlines()
        header = list(map(int, lines[0].split()))
        if len(header) != 5 or header[0] < 1 or header[1] < 1 or header[2:] != [1, 0, 1]:
            raise RuntimeError('Invalid correlator shape')
        configs, times = header[:2]
        if len(lines) != 1 + configs * times:
            raise RuntimeError('Incomplete numerical export')
        for i, line in enumerate(lines[1:]):
            values = list(map(float, line.split()))
            if len(values) != 3 or not all(math.isfinite(v) for v in values) or values[0] != i % times:
                raise RuntimeError('Nonfinite/malformed numerical value')
        shapes[key] = (configs, times)
    return shapes


def compare(reference, candidate, dbutil, exporter, output, tolerance=1e-12, timeout=600):
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError('Tolerance must be finite and nonnegative')
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'relative_tolerance': tolerance, 'ignore_tolerance': 0,
              'databases': {}, 'commands': []}
    def command(name, argv):
        log = output / (name + '.log')
        step = {'argv': list(map(str, argv)), 'log': str(log)}
        report['commands'].append(step)
        with log.open('w') as stream:
            try:
                result = subprocess.run(step['argv'], stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
            except subprocess.TimeoutExpired:
                step['status'] = 'timeout'
                raise RuntimeError(name + ' timed out')
        step['returncode'] = result.returncode
        if result.returncode:
            raise RuntimeError(name + ' failed; see ' + str(log))
    try:
        report['tools'] = {name: {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                           for name, path in [('dbutil', dbutil), ('exporter', exporter)]}
        shapes = []
        for label, database in [('reference', reference), ('candidate', candidate)]:
            database = database.resolve(strict=True)
            report['databases'][label] = {'path': str(database), 'sha256': hashlib.sha256(database.read_bytes()).hexdigest()}
            keys = output / (label + '-keys.xml')
            directory = output / label
            command(label + '-keys', [dbutil, database, 'keysxml', keys])
            command(label + '-export', [exporter, database, directory])
            shapes.append(inspect_export(directory, keys))
        if shapes[0].keys() != shapes[1].keys():
            raise RuntimeError('Reference/candidate key sets differ (missing or extra keys)')
        if shapes[0] != shapes[1]:
            raise RuntimeError('Reference/candidate configuration/time shapes differ')
        report.update(keys=len(shapes[0]), finite_complex_values_per_database=sum(c*t for c,t in shapes[0].values()), exact_key_coverage=True)
        command('compare', [dbutil, reference.resolve(), 'compare', candidate.resolve(), '-tol', str(tolerance), '0'])
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--dbutil', type=Path, required=True)
    parser.add_argument('--exporter', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='new evidence directory')
    parser.add_argument('--tolerance', type=float, default=1e-12)
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    if args.timeout < 1: parser.error('timeout must be positive')
    try:
        compare(args.reference, args.candidate, args.dbutil.absolute(), args.exporter.absolute(), args.output.absolute(), args.tolerance, args.timeout)
    except Exception as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__': main()
