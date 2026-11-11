from pathlib import Path
import sys
import tempfile
import unittest
import os
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0, str(SCRIPTS))
import redstar_runtime as runtime
import run_regressions as runner
try:
    import tomllib
    HAS_TOML = True
except ImportError:
    try:
        import tomli
        HAS_TOML = True
    except ImportError:
        HAS_TOML = False


class NamingTests(unittest.TestCase):
    def test_multi_dot_name(self):
        self.assertEqual(runner.baseline_directory(Path('test_inputs/fred.george.xml')).name, 'fred.george')

    def test_shared_output_and_stage_commands(self):
        import xml.etree.ElementTree as ET
        xml = ET.fromstring('<RedstarNPt><DBFiles><output_db>arbitrary.sdb</output_db></DBFiles></RedstarNPt>')
        runtime.prepare_outputs(xml)
        self.assertEqual(xml.findtext('DBFiles/output_db'), 'output.sdb1')
        self.assertEqual(runtime.stage_command({'redstar_npt': Path('/build/src/redstar_npt')}, 'numerical'),
                         [Path('/build/src/redstar_npt'), 'input.xml', 'npt.out.xml'])


@unittest.skipUnless(HAS_TOML, 'TOML tests require Python 3.11+ or tomli')
class ConfigTests(unittest.TestCase):
    def test_absolute_bin_directories_expand_to_fixed_executables(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'tools.toml'
            path.write_text('[executables]\nredstar_bin = "/installed/redstar/bin"\nchroma_bin = "/installed/chroma/bin"\n')
            tools = runtime.configured_tools(path)
            self.assertEqual(tools['redstar_npt'], Path('/installed/redstar/bin/redstar_npt'))
            self.assertEqual(tools['chroma'], Path('/installed/chroma/bin/chroma'))

    def test_relative_build_paths_and_individual_overrides_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'tools.toml'
            for entry in ['redstar_bin = "../old/build/src"', 'chroma_bin = "local/bin"',
                          'redstar_npt = "/other/npt"', 'chroma = "/other/chroma"']:
                path.write_text('[executables]\n'+entry+'\n')
                with self.assertRaises(ValueError):
                    runtime.configured_tools(path)

    def test_test_list_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'tests.toml'
            tests = [{'xml': 'fred.george.xml', 'kind': 'passed', 'sha256': 'a'*64}]
            runner.write_tests(path, tests)
            self.assertEqual(runner.read_tests(path), tests)

    def test_exclusions_preserved_and_promoted_case_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'tests.toml'
            path.write_text('schema_version = 1\ntests = []\n[[excluded]]\nxml = "a.xml"\nreason = "old failure"\n[[excluded]]\nxml = "b.xml"\nreason = "missing data"\n')
            runner.write_tests(path, [{'xml': 'a.xml'}])
            config = runtime.load_toml(path)
            self.assertEqual(config['excluded'], [{'xml': 'b.xml', 'reason': 'missing data'}])
            self.assertEqual(runner.read_tests(path), [{'xml': 'a.xml'}])

    def test_simple_filename_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'tests.toml'
            path.write_text('schema_version = 1\ntests = ["fred.george.xml", "pion.xml"]\n')
            self.assertEqual(runner.read_tests(path), [{'xml': 'fred.george.xml'}, {'xml': 'pion.xml'}])

    def test_duplicate_and_escaping_names_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'tests.toml'
            for names in [['a.xml', 'a.xml'], ['../a.xml'], ['/a.xml'], ['a.dat']]:
                import json
                path.write_text('schema_version = 1\n'+'\n'.join('[[tests]]\nxml = '+json.dumps(name) for name in names))
                with self.assertRaises(ValueError):
                    runner.read_tests(path)


class ToolDirectoryTests(unittest.TestCase):
    def test_path_and_legacy_chroma_environment_are_not_fallbacks(self):
        with patch.dict(os.environ, {'PATH':str(Path(sys.executable).parent), 'CHROMA':sys.executable}, clear=True):
            for family, names in [('redstar', ('redstar_npt',)), ('chroma', ('chroma',))]:
                with self.assertRaisesRegex(ValueError, family.upper()+'_BIN'):
                    runtime.required_tools(family, names)

    def test_explicit_directory_wins_and_incomplete_directory_fails(self):
        with tempfile.TemporaryDirectory(prefix='bin path ') as tmp:
            folder=Path(tmp)
            (folder/'chroma').symlink_to(sys.executable)
            with patch.dict(os.environ, {'CHROMA_BIN':'/missing'}):
                self.assertEqual(runtime.required_tools('chroma', ('chroma',), folder)['chroma'],folder/'chroma')
            with self.assertRaisesRegex(ValueError, 'Missing executable'):
                runtime.required_tools('redstar', ('redstar_npt',), folder)
            with self.assertRaisesRegex(ValueError, 'absolute'):
                runtime.required_tools('chroma', ('chroma',), Path('.'))


class LimitsTests(unittest.TestCase):
    def test_timeout_reaps_child(self):
        import subprocess
        with tempfile.TemporaryFile() as log:
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                runtime.run_limited([sys.executable, '-c', 'import time;time.sleep(30)'],
                                    cwd=None, env=None, stdout=log, timeout=0.1)


@unittest.skipUnless(HAS_TOML, 'TOML tests require Python 3.11+ or tomli')
class EstablishmentTests(unittest.TestCase):
    def test_only_validated_cases_promoted_and_existing_baseline_preserved(self):
        from unittest.mock import patch
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root/'test_inputs'
            inputs.mkdir()
            for name in ['fred.george.xml', 'bad.xml', 'fake.xml']:
                (inputs/name).write_text('<RedstarNPt/>')
            regressions = root/'regressions'
            regressions.mkdir()
            tools = regressions/'tools.toml'
            tools.write_text('[executables]\ndbutil = '+repr(str(root/'dbutil'))+'\nexporter = '+repr(str(root/'exporter'))+'\n')
            tests = regressions/'tests.toml'
            tests.write_text('schema_version = 1\ntests = []\n')
            output = root/'runs'/'attempt'
            run = output/'fred.george'
            run.mkdir(parents=True)
            (run/'output.sdb1').write_bytes(b'validated bytes')
            (run/'input.xml').write_text('prepared snapshot')
            report = {'cases': [{'file': 'bad.xml', 'status': 'failed', 'error': 'missing data'},
                                {'file': 'fake.xml', 'status': 'passed_fake_data', 'fake_data_mode': 'true'},
                                {'file': 'fred.george.xml', 'status': 'passed'}],
                      'dbutil': str(root/'dbutil'), 'programs': {}, 'program_sha256': {},
                      'dataset': 'fixture', 'verified_data': {}}
            with patch.object(runner, 'ROOT', root), patch.object(runner, 'REGRESSIONS', regressions), \
                 patch.object(runner, 'validate', return_value=(output, report)) as validate, \
                 patch.object(runner, 'compare') as compare:
                args = ['--establish', '--all', '--tools', str(tools), '--list', str(tests)]
                self.assertTrue(runner.main(args))
                self.assertFalse((regressions/'bad').exists())
                self.assertFalse((regressions/'fake').exists())
                self.assertEqual((regressions/'fred.george/output.sdb1').read_bytes(), b'validated bytes')
                self.assertEqual([t['xml'] for t in runner.read_tests(tests)], ['fred.george.xml'])
                summary = json.loads((output/'regressions.json').read_text())
                self.assertEqual(summary['failed'], 2)
                self.assertEqual(compare.call_count, 1)
                with self.assertRaises(SystemExit):
                    runner.main(args)
                self.assertEqual(validate.call_count, 1)
