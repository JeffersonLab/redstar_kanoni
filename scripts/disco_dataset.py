"""Validate the supplemental 4^3x16 native DISCO collection before comparisons."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as E


def _xml_value(node):
    if node is None:
        raise ValueError('Missing generation provenance XML')
    return node.tag, (node.text or '').strip(), tuple(_xml_value(c) for c in node)


def load_disco_collection(directory, baseline, primary_manifest):
    directory, baseline = Path(directory), Path(baseline)
    manifest_path = directory / 'dataset-manifest.json'
    report = json.loads(manifest_path.read_text())
    if report.get('status') != 'generated_and_readback_validated':
        raise ValueError('DISCO collection has not passed full readback')
    if report.get('lattice') != [4, 4, 4, 16] or report.get('RsdCG') != primary_manifest['RsdCG']:
        raise ValueError('DISCO lattice/solver provenance mismatch')
    source = directory / 'generation-input.xml'
    if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != report.get('input_sha256'):
        raise ValueError('DISCO generation input checksum mismatch')
    recipe = E.parse(source).getroot()
    original = E.parse(baseline / 'inputs/colorvec.ini.xml').getroot()
    for tag in ('Cfg', 'RNG'):
        if _xml_value(recipe.find(tag)) != _xml_value(original.find(tag)):
            raise ValueError('DISCO ' + tag + ' differs from baseline')
    if recipe.findtext('Param/nrow').split() != ['4', '4', '4', '16']:
        raise ValueError('DISCO generation lattice mismatch')
    expected_paths = {(0,), (3,), (3,3), (3,3,3), (-3,), (-3,-3), (-3,-3,-3)}
    if report.get('mass_labels') != ['U0.05', 'U0.1'] or report.get('time_slices') != list(range(16)) or set(map(tuple,report.get('displacements',[]))) != expected_paths or report.get('momenta') != [[0,0,0]]:
        raise ValueError('Incomplete DISCO mass/time/path coverage')
    if len(report['files']) != 1 or report.get('keys') != 224 or report.get('finite_complex_values') != 3584:
        raise ValueError('Incomplete single-file DISCO coverage')
    item = report['files'][0]
    name = item['name']
    path = directory / name
    if Path(name).name != name or path.is_symlink() or not path.is_file():
        raise ValueError('Invalid DISCO payload path')
    if path.stat().st_size != item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise ValueError('DISCO payload checksum/size mismatch: ' + name)
    check = item['validation']
    if check.get('status') != 'passed' or check.get('checksums') != 'passed' or check.get('rank') != 5 or check.get('stored_blocks',0) <= 0 or check.get('finite_complex_values') != 3584:
        raise ValueError('DISCO payload readback coverage mismatch')
    return manifest_path, [path.resolve()]
