import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as E
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from disco_dataset import load_disco_collection


class DiscoCollectionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'inputs').mkdir()
        xml = '<chroma><Param><nrow>4 4 4 16</nrow></Param><RNG><Seed><elem>11</elem></Seed></RNG><Cfg><cfg_type>WEAK_FIELD</cfg_type></Cfg></chroma>'
        (self.root / 'inputs/colorvec.ini.xml').write_text(xml)
        (self.root / 'generation-input.xml').write_text(xml)
        self.report = dict(status='generated_and_readback_validated', lattice=[4,4,4,16], RsdCG=1e-14, finite_complex_values=3584, keys=224, mass_labels=['U0.05','U0.1'], time_slices=list(range(16)), displacements=[[0],[3],[3,3],[3,3,3],[-3],[-3,-3],[-3,-3,-3]], momenta=[[0,0,0]], input_sha256=hashlib.sha256(xml.encode()).hexdigest(), files=[])
        name = 'disco.sdb'
        (self.root / name).write_bytes(b'fixture')
        self.report['files'].append(dict(name=name, bytes=7, sha256=hashlib.sha256(b'fixture').hexdigest(), validation=dict(status='passed', checksums='passed', rank=5, stored_blocks=224, finite_complex_values=3584)))

    def load(self):
        (self.root / 'dataset-manifest.json').write_text(json.dumps(self.report))
        return load_disco_collection(self.root, self.root, dict(RsdCG=1e-14))

    def test_complete_collection(self):
        self.assertEqual(len(self.load()[1]), 1)

    def test_reject_unvalidated(self):
        self.report['status'] = 'running'
        with self.assertRaisesRegex(ValueError, 'readback'): self.load()

    def test_reject_missing_coverage(self):
        self.report['files'].pop()
        with self.assertRaisesRegex(ValueError, 'coverage'): self.load()

    def test_reject_changed_payload(self):
        (self.root / self.report['files'][0]['name']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'): self.load()

    def test_reject_changed_generation_input(self):
        (self.root / 'generation-input.xml').write_text('<chroma/>')
        with self.assertRaisesRegex(ValueError, 'input checksum'): self.load()

    def test_reject_different_gauge(self):
        p = self.root / 'inputs/colorvec.ini.xml'
        p.write_text(p.read_text().replace('WEAK_FIELD', 'UNIT'))
        with self.assertRaisesRegex(ValueError, 'Cfg'): self.load()

    def test_reject_different_rng(self):
        p = self.root / 'inputs/colorvec.ini.xml'
        p.write_text(p.read_text().replace('11', '12'))
        with self.assertRaisesRegex(ValueError, 'RNG'): self.load()

    def test_reject_different_accuracy(self):
        self.report['RsdCG'] = 1e-12
        with self.assertRaisesRegex(ValueError, 'solver'): self.load()

    def test_reject_partial_gamma_readback(self):
        self.report['files'][0]['validation']['finite_complex_values'] = 8
        with self.assertRaisesRegex(ValueError, 'readback coverage'): self.load()


class DirectDiscoRecipeTest(unittest.TestCase):
    def test_one_output_complete_mass_time_dictionary(self):
        recipe = Path(__file__).resolve().parents[1] / 'chroma_inputs/superb-double/disco.probing.ini.xml'
        root = E.parse(recipe).getroot()
        entries = root.findall('Param/InlineMeasurements/elem')
        self.assertEqual(len(entries),32)
        self.assertEqual({e.findtext('NamedObject/sdb_file') for e in entries},{'disco.sdb'})
        coverage = set()
        for e in entries:
            p = e.find('Param')
            self.assertEqual([n.text for n in p.findall('mass_labels/elem')],['U0.05','U0.1'])
            self.assertEqual(p.findtext('max_path_length'),'3')
            self.assertEqual(p.findtext('Propagator/InvertParam/RsdCG'),'1e-14')
            coverage.add((p.findtext('mass_label'),int(p.findtext('t_sources'))))
        self.assertEqual(coverage,{(mass,t) for mass in ['U0.05','U0.1'] for t in range(16)})
