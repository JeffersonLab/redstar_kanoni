from pathlib import Path
from copy import deepcopy
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import contraction_workflow as workflow


class SplitCases(unittest.TestCase):
    def test_all_validated_cases_are_split_without_changing_selection(self):
        cases=list((ROOT/'regressions/redstar').glob('*/case.json'))
        self.assertEqual(len(cases),34)
        for meta in cases:
            case,m,graph=workflow.read_case(meta.parent)
            npt=ET.parse(case/'npt.xml')
            self.assertIsNone(npt.find('NPointList'))
            self.assertIsNotNone(npt.find('ColorVec'))
            source=ET.parse(ROOT/m['provenance']['source_xml'])
            self.assertEqual(workflow.definition(graph.find('NPointList')),workflow.definition(source.find('NPointList')))
            self.assertEqual(npt.findtext('ColorVec/Param/fake_data_modeP'),'false')

    def test_graph_staging_does_not_require_data_or_npt(self):
        case,meta,graph=workflow.read_case(ROOT/'regressions/redstar/pion')
        before=(case/'graph.xml').read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            workflow.prepare_graph(case,graph,Path(tmp))
            tree=ET.parse(Path(tmp)/'graph.xml')
            self.assertIsNone(tree.find('ColorVec'))
            self.assertEqual(tree.findtext('DBFiles/corr_graph_bin'),'corr_graph.bin')
            self.assertFalse((Path(tmp)/'npt.xml').exists())
        self.assertEqual((case/'graph.xml').read_bytes(),before)

    def test_graph_format_and_geometry_are_not_silently_accepted(self):
        meta={'correlators':81,'time_samples':7}
        good='Version = 3\nNumber of corrs = 81\nNumber of graphs = 5924\nNt_corr = 7\nLattice size = 4 4 4 16\n'
        workflow.graph_summary(good,meta)
        for bad in (good.replace('Version = 3','Version = 4'),good.replace('4 4 4 16','12 12 12 16'),good.replace('corrs = 81','corrs = 80'),good.replace('graphs = 5924','graphs = 0')):
            with self.assertRaises(RuntimeError):workflow.graph_summary(bad,meta)

    def test_shared_chroma_template_has_no_operator_selection(self):
        for path in (ROOT/'regressions/corr_superb').glob('*/case.json'):
            case,meta,graph=workflow.read_case(path.parent)
            with tempfile.TemporaryDirectory() as tmp:
                workflow.prepare_chroma(case,Path(tmp),meta,graph)
                tree=ET.parse(Path(tmp)/'chroma.xml')
                self.assertFalse(tree.findall('.//NPointList'))
                self.assertFalse(tree.findall('.//Operators'))
                self.assertEqual(tree.findtext('.//corr_graph_file'),'corr_graph.bin')
                self.assertEqual([n.text for n in tree.findall('.//InlineMeasurements/elem/Name')],['CREATE_COLORVECS_SUPERB','CORR_SUPERB'])
                graph.find('NPointList/elem/NPoint/elem[t_slice="0"]/t_slice').text='3'
                with self.assertRaises(ValueError):workflow.prepare_chroma(case,Path(tmp),meta,graph)

    def test_weight_paths_cannot_escape_case(self):
        case,meta,graph=workflow.read_case(ROOT/'regressions/redstar/pion')
        ET.SubElement(graph.find('DBFiles/proj_op_xmls'),'elem').text='../outside.xml'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):workflow.prepare_graph(case,graph,Path(tmp))

    def test_existing_output_is_never_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'existing';run.mkdir();(run/'run.json').write_text('preserve me')
            tools={'redstar_corr_graph':Path(sys.executable),'view_corr_graph':Path(sys.executable)}
            with patch.object(workflow,'configured_tools',return_value=tools):
                code=workflow.main('graph',[str(ROOT/'regressions/redstar/pion'),'--tools','unused.toml','--output',str(run)])
            self.assertEqual(code,1)
            self.assertEqual((run/'run.json').read_text(),'preserve me')

    def test_per_value_gate_catches_small_channel_outlier(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)
            for label,small in [('reference','0.000001'),('candidate','0.001')]:
                d=run/'comparison'/label;d.mkdir(parents=True)
                (d/'index.xml').write_text('<Exports><elem><filename>key.dat</filename><Key><test>1</test></Key></elem></Exports>')
                (d/'key.dat').write_text('1 2 1 0 1\n0 100000000 0\n1 '+small+' 0\n')
            with self.assertRaisesRegex(RuntimeError,'per-value'):
                workflow.validate_values(run,{'kind':'corr_superb','correlators':1,'time_samples':2})

    def test_symmetry_zero_control_is_preserved(self):
        m=json.loads((ROOT/'regressions/redstar/eta_eta_3pt/case.json').read_text())
        self.assertTrue(m['symmetry_zero'])
        self.assertEqual(m['correlators'],1)


if __name__=='__main__':unittest.main()
