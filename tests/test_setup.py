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
        for name in ('setup-data','run_colorvec.csh'): shutil.copy2(str(BASE/name),str(self.repo/name))
        (self.repo/'test_inputs').mkdir()
        self.source=self.home/'original'; self.source.mkdir()
        self.cache=self.home/'shared'
        contents=b'real database contents\x00\xff'
        (self.source/'meson.sdb').write_bytes(contents)
        entry=dict(name='meson.sdb',bytes=len(contents),sha256=hashlib.sha256(contents).hexdigest())
        (self.repo/'test_inputs/data-manifest.json').write_text(json.dumps(dict(files=[entry])))
        self.env=dict(os.environ,KANONI_DATA_DIR=str(self.cache))
    def setup(self,*args):
        return subprocess.run([str(self.repo/'setup-data'),'--source-dir',str(self.source),*args],env=self.env,text=True,capture_output=True)
    def test_adopt_and_repeat(self):
        result=self.setup('--adopt'); self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.source/'meson.sdb').is_symlink())
        self.assertEqual((self.source/'meson.sdb').resolve(),(self.cache/'meson.sdb').resolve())
        self.assertEqual(self.setup('--adopt').returncode,0)
        self.assertEqual((self.cache/'meson.sdb').stat().st_mode & 0o222,0)
    def test_corrupt_source_preserved(self):
        (self.source/'meson.sdb').write_bytes(b'wrong')
        self.assertNotEqual(self.setup('--adopt').returncode,0)
        self.assertEqual((self.source/'meson.sdb').read_bytes(),b'wrong')
        self.assertFalse(self.cache.exists())
    def test_corrupt_cache_preserved(self):
        self.cache.mkdir();(self.cache/'meson.sdb').write_bytes(b'wrong')
        self.assertNotEqual(self.setup('--adopt').returncode,0)
        self.assertEqual((self.cache/'meson.sdb').read_bytes(),b'wrong')
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
        self.assertEqual((self.cache/'meson.sdb').read_bytes(),contents)
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
        self.assertFalse((self.cache/'meson.sdb').exists())
        self.assertEqual(list(self.cache.iterdir()),[])
    def test_runner_isolates_outputs(self):
        self.assertEqual(self.setup('--adopt').returncode,0)
        input_xml = '<RedstarNPt><Param><version>14</version><diagnostic_level>20</diagnostic_level></Param><NPointList><elem/></NPointList><DBFiles/><ColorVec><DBFiles><prop_dbs><elem>meson.sdb</elem></prop_dbs></DBFiles></ColorVec></RedstarNPt>'
        (self.repo/'test_inputs/pion.xml').write_text(input_xml)
        binaries=self.home/'binary path';binaries.mkdir()
        for name in ('redstar_corr_graph','redstar_npt'):
            p=binaries/name
            p.write_text('#!/bin/sh\n[ -f meson.sdb ] || exit 3\nprintf generated > "$2"\nprintf graph > corr_graph.bin\nprintf result > output.npt.sdb1\n')
            p.chmod(0o755)
        env=dict(self.env,REDSTAR_BIN=str(binaries))
        for unused in range(2):
            result=subprocess.run([str(self.repo/'run_colorvec.csh'),'pion.xml'],cwd=str(self.home),env=env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
        runs=list((self.repo/'runs').iterdir());self.assertEqual(len(runs),2)
        for run in runs:
            self.assertEqual((run/'output.npt.sdb1').read_text(),'result')
            self.assertTrue((run/'graph.out.xml').is_file())
            self.assertTrue((run/'npt.out.xml').is_file())
            record=json.loads((run/'run.json').read_text())
            self.assertEqual(record['status'],'executables_passed')
            self.assertFalse(record['numerical_readback_validated'])
            import xml.etree.ElementTree as ET
            prepared=ET.parse(run/'input.xml')
            self.assertEqual(prepared.findtext('ColorVec/DBFiles/prop_dbs/elem'),str(self.cache/'meson.sdb'))
            self.assertEqual(prepared.findtext('Param/diagnostic_level'),'0')
            (run/'meson.sdb').unlink()
        self.assertTrue((self.cache/'meson.sdb').is_file())
        self.assertEqual((self.repo/'test_inputs/pion.xml').read_text(),input_xml)
        self.assertFalse((self.repo/'out.xml').exists())

    def test_runner_rejects_legacy_schema_before_creating_output(self):
        (self.repo/'test_inputs/old.xml').write_text('<RedstarNPt><Param><version>12</version></Param></RedstarNPt>')
        result=subprocess.run([str(self.repo/'run_colorvec.csh'),'old.xml'],cwd=self.home,env=self.env,text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Expected RedstarNPt v14',result.stderr)
        self.assertFalse((self.repo/'runs').exists())

    def test_runner_explicit_data_home_overrides_environment(self):
        self.assertEqual(self.setup().returncode,0)
        (self.repo/'test_inputs/pion.xml').write_text('<RedstarNPt><Param><version>14</version><diagnostic_level>0</diagnostic_level></Param><NPointList><elem/></NPointList><DBFiles/><ColorVec><DBFiles><prop_dbs><elem>meson.sdb</elem></prop_dbs></DBFiles></ColorVec></RedstarNPt>')
        binaries=self.home/'tools';binaries.mkdir()
        for name in ('redstar_corr_graph','redstar_npt'):
            p=binaries/name;p.write_text('#!/bin/sh\nprintf report > "$2"\nprintf graph > corr_graph.bin\nprintf result > output.npt.sdb1\n');p.chmod(0o755)
        env=dict(self.env,REDSTAR_BIN=str(binaries),KANONI_DATA_DIR=str(self.home/'does not exist'))
        result=subprocess.run([str(self.repo/'run_colorvec.csh'),'pion.xml','--database-dir',str(self.cache),'--threads','2'],env=env,cwd=self.home,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        record=json.loads(next((self.repo/'runs').glob('*/run.json')).read_text())
        self.assertEqual(record['data_home'],str(self.cache))
        self.assertEqual(record['threads'],2)

if __name__=='__main__':unittest.main()
