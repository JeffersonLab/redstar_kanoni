#!/usr/bin/env python3
"""Audit the checked derivative-only vertex fixture without modifying references."""
import argparse
from functools import lru_cache
import itertools
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


# Circular derivative convention from Redstar lib/operators/twoquark_deriv_ops.cc.
CIRCULAR = {1: {1: -1j / math.sqrt(2), 2: 1 / math.sqrt(2)},
            0: {3: 1j}, -1: {1: 1j / math.sqrt(2), 2: 1 / math.sqrt(2)}}


def definition(node):
    return (node.tag, tuple(sorted(node.attrib.items())),
            ' '.join((node.text or '').split()), tuple(definition(x) for x in node))


def cg(a, b, total, m, n, projection):
    """Integer-spin SU(2) Clebsch–Gordan coefficient, Condon–Shortley phase."""
    if (abs(m) > a or abs(n) > b or m + n != projection or
            abs(projection) > total or total < abs(a - b) or total > a + b):
        return 0.0
    f = math.factorial
    prefactor = math.sqrt(
        (2 * total + 1) * f(total + a - b) * f(total - a + b) * f(a + b - total) /
        f(a + b + total + 1) * f(total + projection) * f(total - projection) *
        f(a - m) * f(a + m) * f(b - n) * f(b + n))
    value = 0.0
    for k in range(a + b + total + 1):
        args = [k, a + b - total - k, a - m - k, b + n - k,
                total - b + m + k, total - a - n + k]
        if min(args) >= 0:
            value += (-1) ** k / math.prod(f(q) for q in args)
    return prefactor * value


@lru_cache(maxsize=None)
def basis(n, total, j13):
    if n not in (1, 2, 3) or not 0 <= total <= n:
        raise ValueError('Only the checked one-, two-, three-derivative spins are supported')
    if (n == 1 and total != 1) or (n == 3 and j13 not in (0, 1, 2)):
        raise ValueError('Unsupported derivative coupling')
    paths = list(itertools.product((1, 2, 3), repeat=n))
    index = {p: i for i, p in enumerate(paths)}
    matrix = [[0j] * (2 * total + 1) for _ in paths]
    for column, projection in enumerate(range(total, -total - 1, -1)):
        for ms in itertools.product((1, 0, -1), repeat=n):
            if n == 1:
                weight = float(ms[0] == projection)
            elif n == 2:
                weight = cg(1, 1, total, *ms, projection)
            else:
                weight = (cg(1, 1, j13, ms[0], ms[2], ms[0] + ms[2]) *
                          cg(j13, 1, total, ms[0] + ms[2], ms[1], projection))
            if not weight:
                continue
            for directions in itertools.product(*(CIRCULAR[m].items() for m in ms)):
                # Stored paths reverse the nested derivative-application order.
                path = tuple(d[0] for d in directions)[::-1]
                matrix[index[path]][column] += weight * math.prod(d[1] for d in directions)
    return paths, matrix


def vertex_identity(record):
    return tuple(record[k] for k in ('name', 'creation', 'mom', 'row'))


def audit_vertices(root, tolerance=1e-10):
    if root.tag == 'Correlators':
        entries = root.find('VertexCoeffMap')
    elif root.tag == 'SelectedVertexCoefficients':
        entries = root
    else:
        raise ValueError('Expected a dump_corr_graph Correlators export')
    if entries is None or not len(entries):
        raise ValueError('Empty/missing vertex coefficient map')
    records, pairs, vertices, errors = [], {}, {}, []
    coefficients = 0
    worst_orthogonality = 0.0
    for entry in entries:
        key = entry.find('Key')
        if key is None:
            raise ValueError('Missing vertex Key')
        name = key.findtext('name') or ''
        match = re.search(r'a0xD(\d+)(?:_J13(\d+))?_J(\d+)__', name)
        if not match:
            raise ValueError('Expected a derivative-only a0 spin-identity vertex: ' + name)
        n, j13, total = int(match[1]), int(match[2]) if match[2] else None, int(match[3])
        for field, expected in [('type', 'M'), ('piece_num', '1'), ('Cconj', 'false'),
                                ('twoI_z', '0'), ('row', '1'), ('smearedP', 'true')]:
            if key.findtext(field) != expected:
                raise ValueError('Unexpected fixture ' + field + ': ' + name)
        if key.findtext('creation_op') not in ('true', 'false'):
            raise ValueError('Invalid creation flag: ' + name)
        phasings = [tuple(map(int, (p.text or '').split())) for p in key.findall('phasings/elem')]
        if phasings != [(0, 0, 0)]:
            raise ValueError('Expected one explicit zero phasing: ' + name)
        blocks = entry.findall('Val/elem')
        if len(blocks) != 1:
            raise ValueError('Expected one color/flavor block: ' + name)
        flavor = blocks[0].find('Key')
        if (flavor is None or flavor.findtext('color') != '3barx3->1' or
                [(q.findtext('anti'), q.findtext('flavor')) for q in flavor.findall('Quarks/elem')]
                != [('true', 'q'), ('false', 'q')]):
            raise ValueError('Unexpected color/flavor block: ' + name)
        values = {}
        for term in blocks[0].findall('Val/elem'):
            paths = [tuple(map(int, (p.text or '').split()))
                     for p in term.findall('Key/derivs/elem/deriv')]
            if len(paths) != 2 or paths[0] or len(paths[1]) != n or any(x not in (1, 2, 3) for x in paths[1]):
                raise ValueError('Malformed derivative path: ' + name)
            path = paths[1]
            if path in values:
                raise ValueError('Duplicate derivative path: ' + name)
            spin = {}
            for node in term.findall('Val/elem'):
                indices = tuple(map(int, node.findtext('Key/diracs').split()))
                if indices in spin:
                    raise ValueError('Duplicate spin coefficient: ' + name)
                value = complex(float(node.findtext('Val/re')), float(node.findtext('Val/im')))
                if not math.isfinite(value.real) or not math.isfinite(value.imag):
                    raise ValueError('Nonfinite spin coefficient: ' + name)
                spin[indices] = value
            if set(spin) != {(i, i) for i in range(4)}:
                raise ValueError('Expected all four diagonal spin coefficients: ' + name)
            if max(abs(z - spin[0, 0]) for z in spin.values()) > tolerance:
                errors.append(name + ': spin is not the identity')
            values[path] = spin[0, 0]
            coefficients += len(spin)
        if not values:
            raise ValueError('Empty derivative coefficients: ' + name)
        paths, matrix = basis(n, total, j13)
        size = 2 * total + 1
        orthogonality = max(abs(sum(row[a].conjugate() * row[b] for row in matrix) - (a == b))
                            for a in range(size) for b in range(size))
        worst_orthogonality = max(worst_orthogonality, orthogonality)
        vector = [values.get(p, 0j) for p in paths]
        weights = [sum(row[c].conjugate() * v for row, v in zip(matrix, vector)) for c in range(size)]
        residual = max(abs(v - sum(a * b for a, b in zip(row, weights)))
                       for row, v in zip(matrix, vector))
        norm = math.sqrt(sum(abs(w) ** 2 for w in weights))
        record = dict(name=name, creation=key.findtext('creation_op') == 'true',
                      mom=' '.join((key.findtext('mom') or '').split()), row=key.findtext('row'),
                      n=n, J=total, J13=j13, paths=len(values),
                      basis_residual=residual, weight_norm=norm)
        if residual > tolerance or abs(norm - 1) > tolerance:
            errors.append(name + ': incorrect derivative subspace or unit normalization')
        records.append(record)
        full_key = definition(key)
        if full_key in vertices:
            raise ValueError('Duplicate vertex key: ' + name)
        vertices[full_key] = values
        identity = tuple(definition(child) for child in key if child.tag != 'creation_op')
        pair = pairs.setdefault(identity, {})
        if record['creation'] in pair:
            raise ValueError('Duplicate creation/annihilation vertex: ' + name)
        pair[record['creation']] = values, record
    worst_adjoint = 0.0
    for pair in pairs.values():
        if set(pair) != {True, False}:
            errors.append('Unpaired creation/annihilation vertex')
            continue
        creation, a = pair[True]
        annihilation, b = pair[False]
        expected = {p[::-1]: (-1) ** len(p) * z.conjugate() for p, z in creation.items()}
        residual = max(abs(annihilation.get(p, 0j) - expected.get(p, 0j)) for p in set(annihilation) | set(expected))
        worst_adjoint = max(worst_adjoint, residual)
        a['adjoint_residual'] = b['adjoint_residual'] = residual
    if worst_adjoint > tolerance or worst_orthogonality > tolerance:
        errors.append('Incorrect adjoint relation or nonorthonormal analytic basis')
    report = dict(vertices=len(records), pairs=len(pairs), spin_coefficients=coefficients,
                  path_terms=sum(r['paths'] for r in records), errors=errors,
                  max_basis_residual=max(r['basis_residual'] for r in records),
                  max_adjoint_residual=worst_adjoint,
                  max_basis_orthogonality_residual=worst_orthogonality, records=records)
    return report, vertices


def check_reference(report, reference, tolerance):
    for field in ('vertices', 'pairs', 'spin_coefficients', 'path_terms'):
        if report[field] != reference[field]:
            raise ValueError('Reference coverage differs: ' + field)
    expected = {vertex_identity(r): r for r in reference['records']}
    actual = {vertex_identity(r): r for r in report['records']}
    if len(expected) != len(reference['records']) or len(actual) != len(report['records']) or actual.keys() != expected.keys():
        raise ValueError('Reference vertex identities differ')
    for key, value in actual.items():
        for field in ('n', 'J', 'J13', 'paths'):
            if value[field] != expected[key][field]:
                raise ValueError('Reference derivative structure differs: ' + field)
        if abs(value['weight_norm'] - expected[key]['weight_norm']) > tolerance:
            raise ValueError('Reference normalization differs: ' + value['name'])


def main():
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph', type=Path, help='full dump_corr_graph XML export')
    parser.add_argument('--output', required=True, type=Path, help='new report; existing files are never replaced')
    parser.add_argument('--reference', type=Path, default=base / 'derivative_vertex_audit.json')
    parser.add_argument('--selected-reference', type=Path, default=base / 'selected_derivative_vertices.xml')
    parser.add_argument('--tolerance', type=float, default=1e-10)
    args = parser.parse_args()
    if not math.isfinite(args.tolerance) or args.tolerance <= 0:
        parser.error('Tolerance must be positive and finite')
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output already exists; choose a fresh report')
    report, vertices = audit_vertices(ET.parse(args.graph).getroot(), args.tolerance)
    report['tolerance'] = args.tolerance
    try:
        check_reference(report, json.loads(args.reference.read_text()), args.tolerance)
        subset_report, subset = audit_vertices(ET.parse(args.selected_reference).getroot(), args.tolerance)
        if subset_report['errors'] or len(subset) != 4:
            raise ValueError('The four selected reference vertices are invalid')
        for key, values in subset.items():
            if key not in vertices or values.keys() != vertices[key].keys():
                raise ValueError('Selected reference key/path coverage differs')
            if max(abs(z - vertices[key][p]) for p, z in values.items()) > args.tolerance:
                raise ValueError('Selected reference coefficients differ')
        report['reference_checked'] = True
        report['selected_reference_vertices'] = len(subset)
    except (ValueError, KeyError) as error:
        report['errors'].append(str(error))
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'records'}, indent=2))
    if report['errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as error:
        sys.exit('Derivative audit: ' + str(error))
