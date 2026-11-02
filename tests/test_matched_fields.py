from pathlib import Path
import json,subprocess,sys,tempfile,unittest
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_npt_superb import provenance,exported_values

class MatchedFields(unittest.TestCase):
    def test_shared_default_reads_mod_without_generating_vectors(self):
        x=E.parse(ROOT/'regressions/corr_superb/chroma.xml')
        self.assertEqual([n.text for n in x.findall('Param/InlineMeasurements/elem/Name')],['CORR_SUPERB'])
        self.assertEqual(x.findtext('Cfg/cfg_type'),'SZINQIO')
        self.assertEqual(x.findtext('Cfg/reunit'),'false')
        self.assertTrue(x.findtext('.//colorvec_files/elem').endswith('colorvec.mod'))
        m=json.loads((ROOT/'regressions/direct/pion/case.json').read_text())
        self.assertTrue((ROOT/'regressions/direct/pion'/m['chroma_template']).is_file())

    def test_generated_basis_references_are_explicit_legacy_cases(self):
        for p in (ROOT/'regressions/corr_superb').glob('*/case.json'):
            m=json.loads(p.read_text())
            self.assertEqual(m['chroma_template'],'../chroma.generated.xml')
            self.assertIn('legacy',m['field_source'])

    def test_provenance_records_eigenvalue_difference_without_asserting_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'meta.log'
            p.write_text('<DBMetaData><id>propElemOp</id><lattSize>4 4 4 16</lattSize><ProgramInfo><code_version><basePrecision>32</basePrecision></code_version></ProgramInfo><Weights><elem>1 2.000001</elem></Weights></DBMetaData>')
            result=provenance(p,[[1.,2.]])
            self.assertAlmostEqual(result['max_abs_eigenvalue_metadata_difference'],1e-6)
            self.assertIn('does not pin',result['note'])

    def test_export_keeps_the_imaginary_component(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);(d/'index.xml').write_text('<Exports><elem><filename>key.dat</filename><Key><test>1</test></Key></elem></Exports>')
            (d/'key.dat').write_text('1 1 1 0 1\n0 1 -0.000001\n')
            self.assertEqual(next(iter(exported_values(d).values())),[complex(1,-1e-6)])

    def test_bad_mod_source_cannot_partially_install_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'source';src.mkdir();(src/'gauge.mod').write_bytes(b'not the pinned payload')
            result=subprocess.run([sys.executable,str(ROOT/'scripts/import_mod_data.py'),'--source-dir',str(src),'--data-dir',str(root/'data')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.assertNotEqual(result.returncode,0);self.assertFalse((root/'data').exists())

if __name__=='__main__':unittest.main()
