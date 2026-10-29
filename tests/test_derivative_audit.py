"""Reject corruption that a projection-only audit could otherwise miss."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('derivative_audit', ROOT / 'audit_derivative_vertices.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class DerivativeAuditTests(unittest.TestCase):
    def setUp(self):
        # Independent analytic fixtures: Cartesian scalar D2 and symmetric traceless D3.
        # These test the auditor, rather than regenerating coefficients with its basis().
        self.vertices = ET.Element('SelectedVertexCoefficients')
        examples = [('a_a0xD2_J0__J0_A1', {(1, 1): 1 / math.sqrt(3),
                                          (2, 2): 1 / math.sqrt(3),
                                          (3, 3): 1 / math.sqrt(3)}),
                    ('rho_a0xD3_J132_J3__J3_H2D3E2',
                     {(3, 3, 3): 2 / math.sqrt(10),
                      (1, 1, 3): -1 / math.sqrt(10), (1, 3, 1): -1 / math.sqrt(10),
                      (3, 1, 1): -1 / math.sqrt(10), (2, 2, 3): -1 / math.sqrt(10),
                      (2, 3, 2): -1 / math.sqrt(10), (3, 2, 2): -1 / math.sqrt(10)})]
        for name, coefficients in examples:
            for creation in (True, False):
                entry = ET.SubElement(self.vertices, 'elem')
                key = ET.SubElement(entry, 'Key')
                fields = dict(name=name, type='M', piece_num='1', Cconj='false',
                              twoI_z='0', row='1', mom='0 0 0',
                              creation_op=str(creation).lower(), smearedP='true')
                for field, value in fields.items():
                    ET.SubElement(key, field).text = value
                ET.SubElement(ET.SubElement(key, 'phasings'), 'elem').text = '0 0 0'
                block = ET.SubElement(ET.SubElement(entry, 'Val'), 'elem')
                flavor = ET.SubElement(block, 'Key')
                ET.SubElement(flavor, 'color').text = '3barx3->1'
                quarks = ET.SubElement(flavor, 'Quarks')
                for anti in ('true', 'false'):
                    quark = ET.SubElement(quarks, 'elem')
                    ET.SubElement(quark, 'anti').text = anti
                    ET.SubElement(quark, 'flavor').text = 'q'
                terms = ET.SubElement(block, 'Val')
                for path, coefficient in coefficients.items():
                    if not creation:
                        coefficient = (-1) ** len(path) * coefficient.conjugate()
                        path = path[::-1]
                    term = ET.SubElement(terms, 'elem')
                    derivs = ET.SubElement(ET.SubElement(term, 'Key'), 'derivs')
                    ET.SubElement(ET.SubElement(derivs, 'elem'), 'deriv')
                    ET.SubElement(ET.SubElement(derivs, 'elem'), 'deriv').text = ' '.join(map(str, path))
                    spin = ET.SubElement(term, 'Val')
                    for index in range(4):
                        item = ET.SubElement(spin, 'elem')
                        ET.SubElement(ET.SubElement(item, 'Key'), 'diracs').text = f'{index} {index}'
                        value = ET.SubElement(item, 'Val')
                        ET.SubElement(value, 're').text = str(coefficient.real)
                        ET.SubElement(value, 'im').text = str(coefficient.imag)

    def test_analytic_vertices_have_unit_normalization_and_adjoint_pairs(self):
        report, vertices = AUDIT.audit_vertices(self.vertices)
        self.assertEqual((report['vertices'], report['pairs']), (4, 2))
        self.assertEqual(report['errors'], [])
        self.assertLess(report['max_adjoint_residual'], 1e-10)

    def test_nonfinite_coefficient_is_rejected(self):
        self.vertices.find('.//Val/re').text = 'nan'
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            AUDIT.audit_vertices(self.vertices)

    def test_duplicate_spin_coefficient_is_rejected(self):
        term = self.vertices.find('elem/Val/elem/Val/elem/Val')
        term.append(copy.deepcopy(term[0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate spin'):
            AUDIT.audit_vertices(self.vertices)

    def test_duplicate_derivative_path_is_rejected(self):
        block = self.vertices.find('elem/Val/elem/Val')
        block.append(copy.deepcopy(block[0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate derivative path'):
            AUDIT.audit_vertices(self.vertices)

    def test_zero_coefficients_do_not_pass_projection_check(self):
        for node in self.vertices.findall('.//Val/re') + self.vertices.findall('.//Val/im'):
            node.text = '0'
        report, vertices = AUDIT.audit_vertices(self.vertices)
        self.assertTrue(any('normalization' in e for e in report['errors']))

    def test_wrong_adjoint_is_rejected_even_with_unit_norm(self):
        vertex = next(e for e in self.vertices if e.findtext('Key/creation_op') == 'false')
        for node in vertex.findall('.//Val/re') + vertex.findall('.//Val/im'):
            node.text = str(-float(node.text))
        report, vertices = AUDIT.audit_vertices(self.vertices)
        self.assertTrue(any('adjoint' in e for e in report['errors']))

    def test_missing_vertex_cannot_pass_reference_coverage(self):
        reference, vertices = AUDIT.audit_vertices(self.vertices)
        self.vertices.remove(self.vertices[0])
        actual, vertices = AUDIT.audit_vertices(self.vertices)
        self.assertTrue(any('Unpaired' in e for e in actual['errors']))
        with self.assertRaisesRegex(ValueError, 'coverage'):
            AUDIT.check_reference(actual, reference, 1e-10)

    def test_cli_with_optional_selected_reference(self):
        with tempfile.TemporaryDirectory(prefix='audit fixture ') as folder:
            folder = Path(folder)
            graph, reference = (folder / name for name in ('graph.xml', 'reference.json'))
            ET.ElementTree(self.vertices).write(graph)
            report, _ = AUDIT.audit_vertices(self.vertices)
            reference.write_text(json.dumps(report))
            for selected in (False, True):
                with self.subTest(selected=selected):
                    output = folder / f'report-{selected}.json'
                    command = [sys.executable, str(ROOT / 'audit_derivative_vertices.py'),
                               str(graph), '--reference', str(reference), '--output', str(output)]
                    if selected:
                        command.extend(['--selected-reference', str(graph)])
                    result = subprocess.run(command, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                    actual = json.loads(output.read_text())
                    self.assertTrue(actual['reference_checked'])
                    self.assertEqual(actual['errors'], [])
                    if selected:
                        self.assertEqual(actual['selected_reference_vertices'], 4)
                    else:
                        self.assertNotIn('selected_reference_vertices', actual)

    def test_existing_report_is_never_overwritten(self):
        with tempfile.TemporaryDirectory(prefix='audit output ') as folder:
            output = Path(folder) / 'report.json'; output.write_text('preserve me')
            result = subprocess.run([sys.executable, str(ROOT / 'audit_derivative_vertices.py'),
                                     str(Path(folder) / 'unused-graph.xml'), '--output', str(output)],
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Output already exists', result.stderr)
            self.assertEqual(output.read_text(), 'preserve me')


if __name__ == '__main__':
    unittest.main()
