import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/generate_dataset.py'

class GenerationProvenanceTests(unittest.TestCase):
    def run_candidate(self, recipe_rsd, input_rsd):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        inputs = root / 'inputs'
        inputs.mkdir()
        (inputs / 'recipe.json').write_text(json.dumps({'dataset':'unit-provenance', 'RsdCG':recipe_rsd, 'stages':[{'input':'input.xml','outputs':[]}]}))
        (inputs / 'input.xml').write_text('<chroma><RsdCG>' + str(input_rsd) + '</RsdCG></chroma>')
        fake = root / 'stage'
        fake.write_text('#!' + sys.executable + '\nimport pathlib,sys\npathlib.Path(sys.argv[-1]).write_text("<chroma><basePrecision>64</basePrecision></chroma>")\nprint("CHROMA: ran successfully")\n')
        fake.chmod(0o755)
        output = root / 'candidate'
        result = subprocess.run([sys.executable,str(SCRIPT),'--chroma',str(fake),'--inputs',str(inputs),'--output',str(output),'--dbutil',str(fake)],capture_output=True,text=True)
        return output,result

    def test_actual_recipe_precision_is_preserved_in_both_reports(self):
        output,result = self.run_candidate(1e-14,1e-14)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads((output/'generation.json').read_text())['RsdCG'],1e-14)
        self.assertEqual(json.loads((output/'dataset-manifest.json').read_text())['RsdCG'],1e-14)
        self.assertEqual(json.loads((output/'generation.json').read_text())['status'],'generated_not_promoted')

    def test_mismatched_solver_recipe_is_rejected_before_running_stage(self):
        output,result = self.run_candidate(1e-14,1e-12)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('solver residual mismatch',result.stderr)
        self.assertFalse((output/'input.xml.log').exists())
        self.assertEqual(json.loads((output/'generation.json').read_text())['status'],'failed')

    def run_native_sdb(self, masses):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        root=Path(folder.name);inputs=root/'inputs';inputs.mkdir()
        (inputs/'recipe.json').write_text(json.dumps({'dataset':'direct-disco-unit','RsdCG':1e-14,'stages':[{'input':'input.xml','outputs':['disco.sdb'],'storage':'SUPERB','expected_id':'DiscoBlocks','mass_labels':{'disco.sdb':['U0.05','U0.1']}}]}))
        (inputs/'input.xml').write_text('<chroma><RsdCG>1e-14</RsdCG></chroma>')
        fake=root/'chroma';fake.write_text('#!'+sys.executable+'\nimport pathlib,sys\npathlib.Path(sys.argv[-1]).write_text("<chroma><basePrecision>64</basePrecision></chroma>")\npathlib.Path("disco.sdb").write_bytes(b"native fixture")\nprint("CHROMA: ran successfully")\n');fake.chmod(0o755)
        metadata='<DBMetaData><id>DiscoBlocks</id><mass_labels>'+''.join('<elem>'+m+'</elem>'for m in masses)+'</mass_labels></DBMetaData>'
        inspector=root/'inspect';inspector.write_text('#!'+sys.executable+'\nprint('+repr('SUPERB complex<double> rank=5 dimensions=16 16 7 1 2\n'+metadata)+')\n');inspector.chmod(0o755)
        dbutil=root/'dbutil';dbutil.write_text('#!'+sys.executable+'\nraise SystemExit("legacy dbutil must not read native disco.sdb")\n');dbutil.chmod(0o755)
        output=root/'candidate';result=subprocess.run([sys.executable,str(SCRIPT),'--chroma',str(fake),'--inputs',str(inputs),'--output',str(output),'--dbutil',str(dbutil),'--storage-info',str(inspector)],capture_output=True,text=True)
        return output,result

    def test_native_disco_sdb_uses_tensor_inspector_and_mass_dictionary(self):
        output,result=self.run_native_sdb(['U0.05','U0.1'])
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads((output/'generation.json').read_text())
        self.assertEqual(report['files'][0]['storage'],'SUPERB')
        self.assertEqual(report['status'],'generated_not_promoted')

    def test_native_disco_rejects_incomplete_mass_dictionary(self):
        output,result=self.run_native_sdb(['U0.05'])
        self.assertNotEqual(result.returncode,0)
        self.assertIn('mass coverage mismatch',result.stderr)
