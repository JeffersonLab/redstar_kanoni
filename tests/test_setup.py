import hashlib
import importlib.util
import io
import urllib.error
import sys
from unittest import mock
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

BASE=Path(__file__).resolve().parents[1]
class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='kanoni test ')
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.repo=self.home/'repo'; self.repo.mkdir()
        shutil.copytree(str(BASE/'scripts'),str(self.repo/'scripts'))
        for name in ('setup-data','run_colorvec.csh','run_redstar.csh'): shutil.copy2(str(BASE/name),str(self.repo/name))
        (self.repo/'test_inputs').mkdir()
        self.source=self.home/'original'; self.source.mkdir()
        self.data=self.repo/'data'
        contents=b'real database contents\x00\xff'
        (self.source/'meson.sdb').write_bytes(contents)
        entry=dict(name='meson.sdb',bytes=len(contents),sha256=hashlib.sha256(contents).hexdigest())
        (self.repo/'test_inputs/data-manifest.json').write_text(json.dumps(dict(files=[entry])))
        self.env=dict(os.environ);self.env.pop('KANONI_DATA_DIR',None)
    def setup(self,*args):
        return subprocess.run([str(self.repo/'setup-data'),'--source-dir',str(self.source),*args],env=self.env,text=True,capture_output=True)
    def test_copy_regular_files_and_repeat(self):
        result=self.setup();self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(self.source.joinpath('meson.sdb').is_symlink())
        self.assertFalse(self.data.is_symlink())
        self.assertFalse(self.data.joinpath('meson.sdb').is_symlink())
        self.assertEqual((self.source/'meson.sdb').read_bytes(),(self.data/'meson.sdb').read_bytes())
        self.assertFalse((self.repo/'test_inputs/data').exists())
        self.assertEqual(self.setup().returncode,0)
        self.assertEqual((self.data/'meson.sdb').stat().st_mode & 0o222,0)
    def test_corrupt_source_preserved(self):
        (self.source/'meson.sdb').write_bytes(b'wrong')
        self.assertNotEqual(self.setup().returncode,0)
        self.assertEqual((self.source/'meson.sdb').read_bytes(),b'wrong')
        self.assertFalse(self.data.exists())
    def test_corrupt_destination_preserved(self):
        self.data.mkdir();(self.data/'meson.sdb').write_bytes(b'wrong')
        self.assertNotEqual(self.setup().returncode,0)
        self.assertEqual((self.data/'meson.sdb').read_bytes(),b'wrong')
        self.assertFalse((self.source/'meson.sdb').is_symlink())
    def download_module(self):
        spec=importlib.util.spec_from_file_location('setup_data_under_test', self.repo/'scripts/setup_data.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module
    def test_manifest_download_without_local_source(self):
        contents=(self.source/'meson.sdb').read_bytes()
        (self.source/'meson.sdb').unlink()
        manifest_path=self.repo/'test_inputs/data-manifest.json'
        manifest=json.loads(manifest_path.read_text())
        manifest['base_url']='https://example.invalid/releases/v1'
        manifest_path.write_text(json.dumps(manifest))
        module=self.download_module()
        with mock.patch.dict(os.environ,self.env), mock.patch.object(sys,'argv',['setup-data','--source-dir',str(self.source)]), mock.patch.object(module.urllib.request,'urlopen',return_value=io.BytesIO(contents)) as fetch:
            module.main()
            fetch.assert_called_once_with('https://example.invalid/releases/v1/meson.sdb',timeout=120)
        self.assertEqual((self.data/'meson.sdb').read_bytes(),contents)
    def test_transient_download_failure_retried(self):
        module=self.download_module()
        failure=urllib.error.URLError('temporary interruption')
        with mock.patch.object(module,'download_once',side_effect=[failure,None]) as fetch, mock.patch.object(module.time,'sleep'):
            module.download('https://example.invalid/meson.sdb',self.home/'download')
        self.assertEqual(fetch.call_count,2)
    def test_download_retry_count_bounded(self):
        module=self.download_module()
        with mock.patch.object(module,'download_once',side_effect=TimeoutError('timeout')) as fetch, mock.patch.object(module.time,'sleep'):
            with self.assertRaises(TimeoutError):
                module.download('https://example.invalid/meson.sdb',self.home/'download')
        self.assertEqual(fetch.call_count,3)
    def test_private_release_uses_authenticated_gh(self):
        module=self.download_module()
        target=self.home/'download'
        url='https://github.com/JeffersonLab/redstar_kanoni/releases/download/kanoni-data-v1/meson.sdb'
        def fake_gh(command, **kwargs):
            Path(command[command.index('--output')+1]).write_bytes(b'authenticated data')
            return subprocess.CompletedProcess(command,0,stdout='',stderr='')
        error=urllib.error.HTTPError(url,404,'Not Found',{},None)
        with mock.patch.object(module.urllib.request,'urlopen',side_effect=error), mock.patch.object(module.shutil,'which',return_value='/bin/gh'), mock.patch.object(module.subprocess,'run',side_effect=fake_gh) as gh:
            module.download(url,target)
        self.assertEqual(target.read_bytes(),b'authenticated data')
        self.assertIn('JeffersonLab/redstar_kanoni',gh.call_args[0][0])
    def test_private_release_missing_gh_has_actionable_error(self):
        module=self.download_module()
        url='https://github.com/JeffersonLab/redstar_kanoni/releases/download/kanoni-data-v1/meson.sdb'
        error=urllib.error.HTTPError(url,404,'Not Found',{},None)
        with mock.patch.object(module.urllib.request,'urlopen',side_effect=error), mock.patch.object(module.shutil,'which',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'gh auth login'):
                module.download(url,self.home/'download')
    def test_corrupt_download_not_installed(self):
        (self.source/'meson.sdb').unlink()
        module=self.download_module()
        with mock.patch.dict(os.environ,self.env), mock.patch.object(sys,'argv',['setup-data','--source-dir',str(self.source),'--base-url','https://example.invalid/v1']), mock.patch.object(module.urllib.request,'urlopen',return_value=io.BytesIO(b'wrong')):
            with self.assertRaises(RuntimeError):module.main()
        self.assertFalse((self.data/'meson.sdb').exists())
        self.assertEqual(list(self.data.iterdir()),[])
    def binaries(self):
        folder=self.home/'binary path';folder.mkdir()
        script=('#!'+sys.executable+'\n'
                'import pathlib,sys,xml.etree.ElementTree as E\n'
                'root=E.parse(sys.argv[1])\n'
                'for e in root.findall("ColorVec/DBFiles/*/elem"):\n'
                ' p=pathlib.Path(e.text);assert not p.is_absolute()\n'
                ' assert p.is_file() and not p.is_symlink()\n'
                'assert not list(pathlib.Path.cwd().glob("*.sdb"))\n'
                'pathlib.Path(sys.argv[2]).write_text("generated")\n'
                'pathlib.Path("corr_graph.bin").write_text("graph")\n'
                'pathlib.Path("output.npt.sdb1").write_text("result")\n')
        for name in ('redstar_corr_graph','redstar_npt'):
            p=folder/name;p.write_text(script);p.chmod(0o755)
        return folder

    def test_runner_isolates_outputs(self):
        self.assertEqual(self.setup().returncode,0)
        input_xml = '<RedstarNPt><Param><version>14</version><diagnostic_level>20</diagnostic_level></Param><NPointList><elem/></NPointList><DBFiles/><ColorVec><DBFiles><prop_dbs><elem>meson.sdb</elem></prop_dbs></DBFiles></ColorVec></RedstarNPt>'
        (self.repo/'test_inputs/pion.xml').write_text(input_xml)
        binaries=self.binaries()
        env=dict(self.env,REDSTAR_BIN=str(binaries))
        for cwd,source in [(self.repo,'test_inputs/pion.xml'),(self.home,str(self.repo/'test_inputs/pion.xml'))]:
            result=subprocess.run([str(self.repo/'run_colorvec.csh'),source],cwd=str(cwd),env=env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
        runs=list((self.repo/'runs').iterdir());self.assertEqual(len(runs),2)
        for run in runs:
            self.assertEqual((run/'output.npt.sdb1').read_text(),'result')
            self.assertTrue((run/'graph.out.xml').is_file())
            self.assertTrue((run/'npt.out.xml').is_file())
            record=json.loads((run/'run.json').read_text())
            self.assertEqual(record['status'],'executables_passed')
            self.assertEqual(record['source'],str((self.repo/'test_inputs/pion.xml').resolve()))
            self.assertFalse(record['numerical_readback_validated'])
            import xml.etree.ElementTree as ET
            prepared=ET.parse(run/'input.xml')
            relative=prepared.findtext('ColorVec/DBFiles/prop_dbs/elem')
            self.assertFalse(Path(relative).is_absolute())
            self.assertEqual((run/relative).resolve(),(self.data/'meson.sdb').resolve())
            self.assertEqual(prepared.findtext('Param/diagnostic_level'),'0')
            self.assertFalse(list(run.glob('*.sdb')))
        self.assertTrue((self.data/'meson.sdb').is_file())
        self.assertEqual((self.repo/'test_inputs/pion.xml').read_text(),input_xml)
        self.assertFalse((self.repo/'out.xml').exists())

    def test_runner_rejects_legacy_schema_before_creating_output(self):
        (self.repo/'test_inputs/old.xml').write_text('<RedstarNPt><Param><version>12</version></Param></RedstarNPt>')
        result=subprocess.run([str(self.repo/'run_colorvec.csh'),str(self.repo/'test_inputs/old.xml')],cwd=self.home,env=self.env,text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Expected RedstarNPt v14',result.stderr)
        self.assertFalse((self.repo/'runs').exists())

    def test_runner_explicit_data_home_overrides_environment(self):
        self.assertEqual(self.setup().returncode,0)
        (self.repo/'test_inputs/pion.xml').write_text('<RedstarNPt><Param><version>14</version><diagnostic_level>0</diagnostic_level></Param><NPointList><elem/></NPointList><DBFiles/><ColorVec><DBFiles><prop_dbs><elem>meson.sdb</elem></prop_dbs></DBFiles></ColorVec></RedstarNPt>')
        binaries=self.binaries()
        env=dict(self.env,REDSTAR_BIN=str(binaries),KANONI_DATA_DIR=str(self.home/'does not exist'))
        result=subprocess.run([str(self.repo/'run_redstar.csh'),str(self.repo/'test_inputs/pion.xml'),'--database-dir',str(self.data),'--threads','2'],env=env,cwd=self.home,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        record=json.loads(next((self.repo/'runs').glob('*/run.json')).read_text())
        self.assertEqual(record['data_home'],str(self.data.resolve()))
        self.assertEqual(record['threads'],2)

    def test_runner_requires_explicit_input_path(self):
        (self.repo/'test_inputs/pipi_i1.xml').write_text('<RedstarNPt/>')
        result=subprocess.run([str(self.repo/'run_colorvec.csh'),'pipi_i1.xml'],cwd=self.repo,env=self.env,text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('does not exist: pipi_i1.xml',result.stderr)
        self.assertIn('test_inputs/pipi_i1.xml',result.stderr)
        self.assertFalse((self.repo/'runs').exists())

    def test_canonical_xml_inputs_have_no_top_level_aliases(self):
        inputs=list((BASE/'test_inputs').glob('*.xml'))
        self.assertTrue(inputs)
        for source in inputs:
            self.assertFalse(source.is_symlink(),str(source))
            self.assertFalse((BASE/source.name).is_symlink(),source.name)

    def test_setup_rejects_symlink_destination_directory(self):
        actual=self.home/'actual';actual.mkdir();self.data.symlink_to(actual,target_is_directory=True)
        result=self.setup();self.assertNotEqual(result.returncode,0)
        self.assertIn('real directory',result.stderr)
        self.assertFalse(list(actual.iterdir()))

    def test_setup_rejects_symlink_database(self):
        self.data.mkdir();(self.data/'meson.sdb').symlink_to(self.source/'meson.sdb')
        result=self.setup();self.assertNotEqual(result.returncode,0)
        self.assertIn('symlink',result.stderr)
        self.assertTrue((self.source/'meson.sdb').is_file())

    def test_setup_explicit_destination_creates_no_alias(self):
        alternate=self.home/'alternate data'
        result=self.setup('--data-dir',str(alternate));self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((alternate/'meson.sdb').is_file());self.assertFalse((alternate/'meson.sdb').is_symlink())
        self.assertFalse(self.data.exists());self.assertFalse((self.repo/'test_inputs/data').exists())

    def test_runner_rejects_symlink_database(self):
        self.data.mkdir();(self.data/'meson.sdb').symlink_to(self.source/'meson.sdb')
        (self.repo/'test_inputs/pion.xml').write_text('<RedstarNPt><Param><version>14</version></Param><NPointList><elem/></NPointList><DBFiles/><ColorVec><DBFiles><prop_dbs><elem>../data/meson.sdb</elem></prop_dbs></DBFiles></ColorVec></RedstarNPt>')
        env=dict(self.env,REDSTAR_BIN=str(self.binaries()))
        result=subprocess.run([str(self.repo/'run_colorvec.csh'),'test_inputs/pion.xml'],cwd=self.repo,env=env,text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('regular file',result.stderr)
        self.assertFalse((self.repo/'runs').exists())

    def test_setup_retires_verified_legacy_aliases(self):
        (self.repo/'test_inputs/data').symlink_to(self.source,target_is_directory=True)
        (self.repo/'meson.sdb').symlink_to(self.source/'meson.sdb')
        result=self.setup();self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse((self.repo/'test_inputs/data').is_symlink())
        self.assertFalse((self.repo/'meson.sdb').is_symlink())
        self.assertTrue((self.source/'meson.sdb').is_file())
        self.assertTrue((self.data/'meson.sdb').is_file())

    def test_setup_preserves_different_legacy_alias(self):
        other=self.home/'other.sdb';other.write_bytes(b'other private data')
        (self.repo/'meson.sdb').symlink_to(other)
        result=self.setup();self.assertNotEqual(result.returncode,0)
        self.assertIn('different data',result.stderr)
        self.assertTrue((self.repo/'meson.sdb').is_symlink())
        self.assertEqual(other.read_bytes(),b'other private data')

if __name__=='__main__':unittest.main()
