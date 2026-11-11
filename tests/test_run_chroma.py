from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]


class ChromaRunnerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='chroma runner ')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name).resolve()
        self.repo = self.home / 'repo'
        shutil.copytree(BASE / 'scripts', self.repo / 'scripts')
        shutil.copyfile(BASE / 'run_chroma.csh', self.repo / 'run_chroma.csh')
        (self.repo / 'run_chroma.csh').chmod(0o755)
        self.inputs = self.repo / 'inputs'
        self.inputs.mkdir()
        self.data = self.repo / 'data'
        self.data.mkdir()
        self.graph = self.inputs / 'graph.xml'
        self.chroma = self.inputs / 'chroma.xml'
        shutil.copyfile(BASE / 'regressions/direct/pion/graph.xml', self.graph)
        shutil.copyfile(BASE / 'regressions/corr_superb/chroma.xml', self.chroma)
        (self.inputs / 'unrelated.xml').write_text('<do-not-copy/>')
        tree = ET.parse(self.graph)
        ET.SubElement(tree.find('DBFiles/proj_op_xmls'), 'elem').text = 'weights.xml'
        tree.write(self.graph)
        (self.inputs / 'weights.xml').write_text('<Weights/>')
        entries = []
        for name, metadata in [('gauge.mod', {'lattSize': '4 4 4 16', 'decay_dir': '3'}),
                               ('colorvec.mod', {'lattSize': '4 4 4 16', 'decay_dir': '3', 'num_vecs': '10'})]:
            payload = ('pinned ' + name).encode()
            (self.data / name).write_bytes(payload)
            entries.append({'name': name, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(), 'metadata': metadata})
        (self.repo / 'test_inputs').mkdir()
        (self.repo / 'test_inputs/mod-manifest.json').write_text(json.dumps({'files': entries}))
        self.redstar = self.home / 'redstar bin'
        self.chroma_bin = self.home / 'chroma bin'
        self.redstar.mkdir()
        self.chroma_bin.mkdir()
        self.executable(self.redstar / 'redstar_corr_graph', '''
import pathlib,sys,xml.etree.ElementTree as E
x=E.parse(sys.argv[1])
assert pathlib.Path(sys.argv[1]).is_absolute()
assert pathlib.Path(sys.argv[1]).parent.parent.name=='run_inputs'
assert pathlib.Path(x.findtext('DBFiles/proj_op_xmls/elem')).read_text()=='<Weights/>'
assert not pathlib.Path('graph.xml').exists()
pathlib.Path('corr_graph.bin').write_bytes(b'graph')
pathlib.Path(sys.argv[2]).write_text('<GraphReport/>')
''')
        self.executable(self.redstar / 'view_corr_graph', '''
print('Version = 3\\nNumber of corrs = 3\\nNumber of graphs = 3\\nNt_corr = 16\\nLattice size = 4 4 4 16')
''')
        self.executable(self.chroma_bin / 'chroma', '''
import pathlib,sys,xml.etree.ElementTree as E
x=E.parse(sys.argv[sys.argv.index('-i')+1])
assert pathlib.Path(x.findtext('.//colorvec_files/elem')).is_file()
assert pathlib.Path(x.findtext('.//colorvec_files/elem')).is_absolute()
assert pathlib.Path(x.findtext('Cfg/cfg_file')).read_bytes()==b'QIO gauge'
assert pathlib.Path(x.findtext('.//corr_graph_file')).read_bytes()==b'graph'
assert not pathlib.Path('chroma.xml').exists()
pathlib.Path(x.findtext('.//corr_file')).write_bytes(b'correlators')
pathlib.Path(sys.argv[sys.argv.index('-o')+1]).write_text('<ChromaReport/>')
print('CG_SOLVER_TIME: fixture')
print('CHROMA: ran successfully')
''')
        self.importer = self.home / 'import gauge'
        self.executable(self.importer, '''
import pathlib,sys
assert pathlib.Path(sys.argv[1]).read_bytes()==b'pinned gauge.mod'
pathlib.Path(sys.argv[2]).write_bytes(b'QIO gauge')
print('PASS: squared error=0')
''')
        self.env = dict(os.environ)
        for name in ('REDSTAR_BIN', 'CHROMA_BIN', 'CHROMA', 'KANONI_DATA_DIR'):
            self.env.pop(name, None)
        self.env.update(REDSTAR_BIN=str(self.redstar), CHROMA_BIN=str(self.chroma_bin))

    def executable(self, path, body):
        path.write_text('#!' + sys.executable + '\n' + body)
        path.chmod(0o755)

    def run_job(self, *extra, env=None, cwd=None, output_name='result'):
        command = [str(self.repo / 'run_chroma.csh'), str(self.chroma), '--graph-input', str(self.graph),
                   '--gauge-importer', str(self.importer), '--memory-limit-mb', '0',
                   '--output', str(self.home / output_name), *extra]
        return subprocess.run(command, cwd=cwd or self.home, env=env or self.env, capture_output=True, text=True)

    def test_outputs_only_and_input_and_data_preservation_from_external_cwd(self):
        sources = [self.chroma, self.graph, self.inputs / 'weights.xml', *self.data.iterdir()]
        before = {p: p.read_bytes() for p in sources}
        result = self.run_job('--threads', '2')
        self.assertEqual(result.returncode, 0, result.stderr)
        run = self.home / 'result'
        self.assertEqual({p.name for p in run.iterdir()}, {'run.json', 'graph.out.xml', 'graph.log', 'view.log', 'corr_graph.bin', 'gauge.lime', 'gauge-import.log', 'chroma.log', 'chroma.out.xml', 'output.sdb1'})
        record = json.loads((run / 'run.json').read_text())
        self.assertEqual(record['status'], 'executables_passed')
        self.assertFalse(record['numerical_readback_validated'])
        self.assertEqual(record['CG_solves'], 1)
        self.assertEqual(record['threads'], 2)
        for entry in record['prepared_inputs'].values():
            path = Path(entry['path'])
            self.assertEqual(path.parent, self.repo / 'run_inputs/result')
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry['sha256'])
        self.assertFalse((self.repo / 'run_inputs/result/unrelated.xml').exists())
        self.assertEqual({p: p.read_bytes() for p in sources}, before)

    def test_default_output_directory_with_explicit_relative_inputs(self):
        result = subprocess.run([str(self.repo / 'run_chroma.csh'), 'inputs/chroma.xml',
                                 '--graph-input', 'inputs/graph.xml', '--gauge-importer', str(self.importer),
                                 '--memory-limit-mb', '0'], cwd=self.repo, env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        runs = list((self.repo / 'runs').iterdir())
        self.assertEqual(len(runs), 1)
        record = json.loads((runs[0] / 'run.json').read_text())
        self.assertEqual(record['cwd'], str(runs[0]))
        self.assertEqual(record['source'], str(self.chroma))
        self.assertEqual(record['graph_source'], str(self.graph))
        self.assertFalse((runs[0] / 'chroma.xml').exists())
        self.assertTrue((self.repo / 'run_inputs' / runs[0].name / 'chroma.xml').is_file())

    def test_explicit_data_directory_overrides_environment(self):
        env = dict(self.env, KANONI_DATA_DIR=str(self.home / 'missing'))
        result = self.run_job('--database-dir', str(self.data), env=env)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_existing_output_is_preserved(self):
        output = self.home / 'result'
        output.mkdir()
        (output / 'keep').write_text('existing work')
        result = self.run_job()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((output / 'keep').read_text(), 'existing work')
        self.assertFalse((self.repo / 'run_inputs').exists())

    def test_missing_bins_cannot_fall_back_to_path_or_legacy_chroma(self):
        for missing in ('REDSTAR_BIN', 'CHROMA_BIN'):
            with self.subTest(missing=missing):
                env = dict(self.env, PATH=str(self.redstar) + os.pathsep + str(self.chroma_bin) + os.pathsep + self.env['PATH'], CHROMA=str(self.chroma_bin / 'chroma'))
                env.pop(missing)
                result = self.run_job(env=env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(missing, result.stderr)
                self.assertFalse((self.home / 'result').exists())

    def test_mismatched_time_window_is_rejected_before_creating_a_run(self):
        tree = ET.parse(self.chroma)
        tree.find('.//Nt_forward').text = '7'
        tree.write(self.chroma)
        result = self.run_job()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Nt_forward', result.stderr)
        self.assertFalse((self.home / 'result').exists())

    def test_corrupt_and_symlink_mod_files_are_rejected(self):
        vector = self.data / 'colorvec.mod'
        vector.write_bytes(b'corrupt')
        result = self.run_job()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum', result.stderr)
        vector.unlink()
        vector.symlink_to(self.data / 'gauge.mod')
        result = self.run_job()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('regular file', result.stderr)
        self.assertFalse((self.home / 'result').exists())

    def test_wrong_graph_version_stops_before_chroma(self):
        self.executable(self.redstar / 'view_corr_graph', "print('Version = 4\\nNumber of corrs = 3\\nNumber of graphs = 3\\nNt_corr = 16\\nLattice size = 4 4 4 16')")
        result = self.run_job()
        self.assertNotEqual(result.returncode, 0)
        record = json.loads((self.home / 'result/run.json').read_text())
        self.assertEqual(record['status'], 'failed')
        self.assertIn('format 3', record['error'])
        self.assertEqual([step['stage'] for step in record['commands']], ['graph', 'view'])

    def test_inexact_gauge_roundtrip_stops_before_chroma(self):
        self.executable(self.importer, "print('PASS: squared error=0.1')")
        result = self.run_job()
        self.assertNotEqual(result.returncode, 0)
        record = json.loads((self.home / 'result/run.json').read_text())
        self.assertEqual(record['status'], 'failed')
        self.assertIn('exact QIO roundtrip', record['error'])
        self.assertFalse((self.home / 'result/chroma.log').exists())

    def test_auto_build_requires_config_in_the_selected_chroma_bin(self):
        result = subprocess.run([str(self.repo / 'run_chroma.csh'), str(self.chroma),
                                 '--graph-input', str(self.graph)], cwd=self.home,
                                env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('CHROMA_BIN/chroma-config', result.stderr)
        self.assertFalse((self.repo / 'runs').exists())

    def test_missing_completion_marker_is_not_a_success(self):
        self.executable(self.chroma_bin / 'chroma', '''
import pathlib,sys
pathlib.Path('output.sdb1').write_bytes(b'db')
pathlib.Path(sys.argv[-1]).write_text('<Chroma/>')
''')
        result = self.run_job()
        self.assertNotEqual(result.returncode, 0)
        record = json.loads((self.home / 'result/run.json').read_text())
        self.assertEqual(record['status'], 'failed')
        self.assertIn('completion marker', record['error'])


if __name__ == '__main__':
    unittest.main()
