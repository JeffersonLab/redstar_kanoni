import hashlib
import importlib.util
import io
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
    def test_corrupt_download_not_installed(self):
        (self.source/'meson.sdb').unlink()
        module=self.download_module()
        with mock.patch.dict(os.environ,self.env), mock.patch.object(sys,'argv',['setup-data','--source-dir',str(self.source),'--base-url','https://example.invalid/v1']), mock.patch.object(module.urllib.request,'urlopen',return_value=io.BytesIO(b'wrong')):
            with self.assertRaises(RuntimeError):module.main()
        self.assertFalse((self.cache/'meson.sdb').exists())
        self.assertEqual(list(self.cache.iterdir()),[])
    def test_runner_isolates_outputs(self):
        self.assertEqual(self.setup('--adopt').returncode,0)
        (self.repo/'test_inputs/pion.xml').write_text('<input/>')
        binaries=self.home/'binary path';binaries.mkdir()
        for name in ('redstar_corr_graph','redstar_npt'):
            p=binaries/name
            p.write_text('#!/bin/sh\n[ -f meson.sdb ] || exit 3\nprintf generated > out.xml\nprintf result > output.sdb1\n')
            p.chmod(0o755)
        env=dict(self.env,REDSTAR_BIN=str(binaries))
        for unused in range(2):
            result=subprocess.run([str(self.repo/'run_colorvec.csh'),'pion.xml'],cwd=str(self.home),env=env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
        runs=list((self.repo/'runs').iterdir());self.assertEqual(len(runs),2)
        for run in runs:
            self.assertEqual((run/'output.sdb1').read_text(),'result')
            (run/'meson.sdb').unlink()
        self.assertTrue((self.cache/'meson.sdb').is_file())
        self.assertEqual((self.repo/'test_inputs/pion.xml').read_text(),'<input/>')
        self.assertFalse((self.repo/'out.xml').exists())

if __name__=='__main__':unittest.main()
