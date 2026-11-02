import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('comparison', Path(__file__).resolve().parents[1]/'scripts/compare_correlators.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ExportChecks(unittest.TestCase):
    def check_export(self, value='1', key='a', extra='', header='1 1 1 0 1'):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory/'keys.xml').write_text('<Keys><elem><id>a</id></elem></Keys>')
            (directory/'index.xml').write_text('<Exports><elem><filename>0.dat</filename><Key><id>'+key+'</id></Key></elem>'+extra+'</Exports>')
            (directory/'0.dat').write_text(header+'\n0 '+value+' 0\n')
            return m.inspect_export(directory, directory/'keys.xml')

    def test_finite(self):
        self.assertEqual(list(self.check_export().values()), [(1, 1)])

    def test_nonfinite(self):
        for value in ['nan', 'inf', '-inf']:
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, 'Nonfinite'):
                self.check_export(value=value)

    def test_wrong_key(self):
        with self.assertRaisesRegex(RuntimeError, 'keys'):
            self.check_export(key='b')

    def test_duplicate_key(self):
        with self.assertRaisesRegex(RuntimeError, 'keys'):
            self.check_export(extra='<elem><filename>1.dat</filename><Key><id>a</id></Key></elem>')

    def test_incomplete_shape(self):
        with self.assertRaisesRegex(RuntimeError, 'Incomplete'):
            self.check_export(header='2 1 1 0 1')

    def test_invalid_tolerance(self):
        for tolerance in [float('nan'), float('inf'), -1]:
            with self.assertRaises(ValueError):
                m.compare(None, None, None, None, None, tolerance)


class ComparisonChecks(unittest.TestCase):
    def run_comparison(self, shapes, returncode=0):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            database = base/'db'
            database.write_bytes(b'fixture')
            with patch.object(m, 'inspect_export', side_effect=shapes), patch.object(m.subprocess, 'run') as run:
                from types import SimpleNamespace
                run.side_effect = [SimpleNamespace(returncode=0)] * 4 + [SimpleNamespace(returncode=returncode)]
                try:
                    m.compare(database, database, database, database, base/'evidence')
                finally:
                    import json
                    self.report = json.loads((base/'evidence/comparison.json').read_text())
                    self.calls = run.call_args_list

    def test_extra_and_missing_keys(self):
        for shapes in [[{'a': (1, 2)}, {'a': (1, 2), 'b': (1, 2)}], [{'a': (1, 2)}, {'b': (1, 2)}]]:
            with self.assertRaisesRegex(RuntimeError, 'key sets differ'):
                self.run_comparison(shapes)
            self.assertEqual(self.report['status'], 'failed')
            self.assertEqual(len(self.calls), 4)

    def test_shape_mismatch(self):
        with self.assertRaisesRegex(RuntimeError, 'shapes differ'):
            self.run_comparison([{'a': (1, 2)}, {'a': (2, 2)}])

    def test_compare_explicit_tolerance(self):
        self.run_comparison([{'a': (1, 2)}, {'a': (1, 2)}])
        self.assertEqual(self.report['status'], 'passed')
        self.assertEqual(self.calls[-1].args[0][-3:], ['-tol', '1e-12', '0'])

    def test_dbutil_failure_retained(self):
        with self.assertRaisesRegex(RuntimeError, 'failed'):
            self.run_comparison([{'a': (1, 2)}, {'a': (1, 2)}], returncode=1)
        self.assertEqual(self.report['status'], 'failed')
