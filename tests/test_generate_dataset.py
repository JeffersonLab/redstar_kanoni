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
