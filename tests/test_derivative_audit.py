"""Reject corruption that a projection-only audit could otherwise miss."""
import copy
import importlib.util
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
        self.vertices = ET.parse(ROOT / 'selected_derivative_vertices.xml').getroot()

    def test_selected_vertices_have_unit_normalization_and_adjoint_pairs(self):
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

    def test_existing_report_is_never_overwritten(self):
        with tempfile.TemporaryDirectory(prefix='audit output ') as folder:
            output = Path(folder) / 'report.json'; output.write_text('preserve me')
            result = subprocess.run([sys.executable, str(ROOT / 'audit_derivative_vertices.py'),
                                     str(ROOT / 'selected_derivative_vertices.xml'), '--output', str(output)],
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Output already exists', result.stderr)
            self.assertEqual(output.read_text(), 'preserve me')


if __name__ == '__main__':
    unittest.main()
