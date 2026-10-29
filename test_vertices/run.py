#!/usr/bin/env python3
"""Rebuild and audit the derivative-only graph fixture in a fresh directory."""
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
import time
import xml.etree.ElementTree as ET


def definition(node):
    return (node.tag, tuple(sorted(node.attrib.items())),
            ' '.join((node.text or '').split()), tuple(definition(x) for x in node))


def operator_map(path):
    root = ET.parse(path).getroot()
    if root.tag != 'OpsList' or root.findall('.//mom_type'):
        raise ValueError('Expected a current OpsList: ' + str(path))
    entries = {e.findtext('Key'): definition(e.find('Val')) for e in root}
    if len(entries) != len(root):
        raise ValueError('Duplicate operator-map keys')
    return entries


def operator_list(path):
    rows = [tuple(line.split()) for line in path.read_text().splitlines() if line.strip()]
    if any(len(row) != 2 for row in rows) or len(set(rows)) != len(rows):
        raise ValueError('Malformed/duplicate operator-list rows')
    return set(rows)


def main():
    source = Path(__file__).resolve().parent
    repo = source.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--redstar-bin', type=Path, default=os.environ.get('REDSTAR_BIN'))
    parser.add_argument('--output', type=Path, help='new output directory (default: a unique runs/derivative-audit-*)')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--timeout', type=int, default=180, help='seconds per executable')
    args = parser.parse_args()
    if args.threads < 1 or args.timeout < 1:
        parser.error('Threads and timeout must be positive')
    names = ('generate_redstar_onehadron', 'generate_redstar_2pt', 'redstar_corr_graph', 'dump_corr_graph')
    tools = {name: (args.redstar_bin.expanduser() / name if args.redstar_bin else Path(shutil.which(name) or '/missing-' + name)).absolute() for name in names}
    if not all(p.is_file() and os.access(p, os.X_OK) for p in tools.values()):
        parser.error('Set REDSTAR_BIN/--redstar-bin to one installed Redstar bin directory')
    if len({p.resolve().parent for p in tools.values()}) != 1:
        parser.error('Use tools from one installation/compiler/ABI')
    if args.output:
        run = args.output.expanduser().absolute()
        if run.exists() or run.is_symlink():
            parser.error('Output exists; choose a fresh directory')
        run.mkdir(parents=True, exist_ok=False)
    else:
        (repo / 'runs').mkdir(exist_ok=True)
        run = Path(tempfile.mkdtemp(prefix='derivative-audit-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-', dir=repo / 'runs'))
    record = dict(status='running', threads=args.threads, timeout=args.timeout,
                  python=sys.version, numerical_evaluation=False, inputs={}, commands=[],
                  programs={n: dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for n, p in tools.items()})
    for p in [source / n for n in ('single.cont.list', 'single.ops.list', 'single.ops.xml', 'gen.2pt.ini.xml', 'red.xml')]:
        record['inputs'][str(p.relative_to(repo))] = hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [repo / n for n in ('audit_derivative_vertices.py', 'derivative_vertex_audit.json', 'selected_derivative_vertices.xml')]:
        record['inputs'][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    def save():
        temporary = run / 'run.tmp'
        temporary.write_text(json.dumps(record, indent=2) + '\n'); temporary.replace(run / 'run.json')
    env = dict(os.environ, OMP_NUM_THREADS=str(args.threads), OMP_DYNAMIC='FALSE', OMP_MAX_ACTIVE_LEVELS='1',
               OPENBLAS_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    def command(phase, argv, stdin=None):
        step = dict(phase=phase, argv=list(map(str, argv)), started_at=datetime.now().astimezone().isoformat(), status='running')
        record['commands'].append(step); save(); started = time.monotonic()
        with (run / (phase + '.log')).open('w') as log:
            try:
                result = subprocess.run(step['argv'], cwd=run, env=env, stdin=stdin, stdout=log,
                                        stderr=subprocess.STDOUT, timeout=args.timeout)
            except subprocess.TimeoutExpired:
                step.update(status='timeout', seconds=time.monotonic() - started); save(); raise RuntimeError(phase + ' timed out')
        step.update(returncode=result.returncode, seconds=time.monotonic() - started,
                    status='passed' if not result.returncode else 'failed'); save()
        if result.returncode:
            raise RuntimeError(phase + ' failed; see ' + str(run / (phase + '.log')))
    save(); print('Run directory:', run, flush=True)
    try:
        shutil.copy2(source / 'single.cont.list', run / 'single.cont.list')
        shutil.copy2(source / 'gen.2pt.ini.xml', run / 'gen.2pt.ini.xml')
        with (run / 'single.cont.list').open() as stream:
            command('onehadron', [tools['generate_redstar_onehadron'], '0', '4', 'single.ops.list', 'single.ops.xml'], stream)
        rows = operator_list(run / 'single.ops.list'); generated = operator_map(run / 'single.ops.xml')
        if rows != operator_list(source / 'single.ops.list') or generated != operator_map(source / 'single.ops.xml'):
            raise RuntimeError('Generated operator basis differs from the staged reference')
        if {row[1] for row in rows} != set(generated) or len(rows) != 139:
            raise RuntimeError('Operator list/map coverage differs')
        record['operators'] = 139; save()
        command('two_point', [tools['generate_redstar_2pt'], 'gen.2pt.ini.xml', 'red.xml'])
        points = ET.parse(run / 'red.xml').getroot(); reference = ET.parse(source / 'red.xml').getroot()
        if points.tag != 'NPointList' or len(points) != 482 or len({definition(p) for p in points}) != 482:
            raise RuntimeError('Expected 482 unique two-point selections')
        if {definition(p) for p in points} != {definition(p) for p in reference}:
            raise RuntimeError('Generated NPoint selection differs from the staged reference')
        graph = ET.Element('RedstarNPt'); params = ET.SubElement(graph, 'Param')
        for name, value in [('version', '14'), ('diagnostic_level', '0'), ('Nt_corr', '16'), ('bc_spec', '-1'),
                            ('convertUDtoL', 'true'), ('convertUDtoS', 'false'), ('ensemble', 'fred')]:
            ET.SubElement(params, name).text = value
        cg = ET.SubElement(params, 'cgc_options')
        for name, value in [('autoIrrepCG', 'true'), ('rephaseIrrepCG', 'true'),
                            ('enableCGTargetMomRotation', 'true'), ('autoCGVersion', '1')]:
            ET.SubElement(cg, name).text = value
        layout = ET.SubElement(params, 'Layout'); ET.SubElement(layout, 'lattSize').text = '4 4 4 16'; ET.SubElement(layout, 'decayDir').text = '3'
        graph.append(points); files = ET.SubElement(graph, 'DBFiles'); ET.SubElement(files, 'proj_op_xmls'); ET.SubElement(files, 'corr_graph_bin').text = 'corr_graph.bin'
        tree = ET.ElementTree(graph); ET.indent(tree, space='  '); tree.write(run / 'graph.ini.xml', encoding='utf-8', xml_declaration=True)
        command('graph', [tools['redstar_corr_graph'], 'graph.ini.xml', 'graph.out.xml'])
        command('dump', [tools['dump_corr_graph'], 'corr_graph.bin', 'corr_graph.inspect.xml'])
        dumped = ET.parse(run / 'corr_graph.inspect.xml').getroot()
        counts = {name: len(dumped.find(name)) for name in ('CorrGraphMap', 'GraphList', 'VertexCoeffMap')}
        if dumped.tag != 'Correlators' or counts != dict(CorrGraphMap=482, GraphList=482, VertexCoeffMap=220):
            raise RuntimeError('Graph or vertex coverage differs: ' + str(counts))
        command('audit', [sys.executable, repo / 'audit_derivative_vertices.py', run / 'corr_graph.inspect.xml', '--output', run / 'audit.json'])
        audit = json.loads((run / 'audit.json').read_text())
        record.update(status='passed', correlators=482, graphs=482, vertices=220, pairs=110,
                      path_terms=audit['path_terms'], spin_coefficients=audit['spin_coefficients'],
                      max_basis_residual=audit['max_basis_residual'], max_adjoint_residual=audit['max_adjoint_residual'],
                      reference_checked=audit['reference_checked'], selected_reference_vertices=audit['selected_reference_vertices'])
        save(); print(json.dumps({k: v for k, v in record.items() if k not in ('inputs', 'programs', 'commands')}, indent=2))
    except Exception as error:
        record.update(status='failed', error=str(error)); save(); raise


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, ET.ParseError) as error:
        sys.exit('Derivative workflow: ' + str(error))
