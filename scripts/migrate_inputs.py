#!/usr/bin/env python3
"""Migrate legacy Kanoni Redstar inputs using Redstar's SUN-to-SUNClass converter."""
import argparse
import copy
from datetime import datetime
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from xml.parsers import expat


# Keep large v14 inputs reviewable: preserve every unchanged XML byte.
def semantic(node):
    return (node.tag, ' '.join((node.text or '').split()), tuple(semantic(x) for x in node))


def preserve_layout(original, desired):
    old = ET.fromstring(original)
    if semantic(old) == semantic(desired):
        return original
    positions = []
    stack = []
    parser = expat.ParserCreate()
    def start(tag, attrs):
        begin = parser.CurrentByteIndex
        opened = original.index(b'>', begin) + 1
        entry = [begin, opened, None, None, original[begin:opened].endswith(b'/>')]
        positions.append(entry); stack.append(entry)
    def end(tag):
        entry = stack.pop()
        entry[2] = entry[1] if entry[4] else parser.CurrentByteIndex
        entry[3] = entry[1] if entry[4] else original.index(b'>', parser.CurrentByteIndex) + 1
    parser.StartElementHandler = start; parser.EndElementHandler = end
    parser.Parse(original, True)
    spans = dict(zip(old.iter(), positions))
    edits = []
    def diff(a, b):
        if semantic(a) == semantic(b):
            return
        start, opened, closing, end, empty = spans[a]
        if a.tag != b.tag or [e.tag for e in a] != [e.tag for e in b]:
            if not a.tag.endswith('_dbs') and a.tag != 'proj_op_xmls':
                raise ValueError('Structural XML conversion requires full serialization: ' + a.tag)
            element = copy.deepcopy(b); element.tail = None
            edits.append((start, end, ET.tostring(element, encoding='utf-8')))
        elif len(a):
            if ' '.join((a.text or '').split()) != ' '.join((b.text or '').split()):
                raise ValueError('Mixed-content XML is unsupported')
            for left, right in zip(a, b): diff(left, right)
        elif empty:
            element = copy.deepcopy(b); element.tail = None
            edits.append((start, end, ET.tostring(element, encoding='utf-8')))
        else:
            edits.append((opened, closing, escape(b.text or '').encode('utf-8')))
    diff(old, desired)
    payload = original
    for start, end, value in sorted(edits, reverse=True):
        payload = payload[:start] + value + payload[end:]
    if semantic(ET.fromstring(payload)) != semantic(desired):
        raise ValueError('Layout-preserving XML verification failed')
    return payload


def signature(node):
    return (node.tag, (node.text or '').strip(), tuple(signature(x) for x in node if isinstance(x.tag,str)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--redstar-bin', type=Path, default=os.environ.get('REDSTAR_BIN'))
    parser.add_argument('files', nargs='*', type=Path, help='selected inputs; default: every RedstarNPt XML')
    parser.add_argument('--fsq-database', type=Path, help='select a modern FSq database for the unchanged current/smearing')
    parser.add_argument('--repair-rest-pairs', action='store_true', help='repair identical nonzero constituent vectors in explicitly zero-total two-body CGs')
    parser.add_argument('--enable-target-rotation', action='store_true', help='explicitly enable rotation to the requested physical target momentum')
    parser.add_argument('--write', action='store_true', help='apply validated structural conversions; otherwise report only')
    parser.add_argument('--enable-auto-cg', action='store_true', help='replace unsupported fixed-CG mode while retaining phase/rotation settings')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    executable=(args.redstar_bin/'convert_proj_weights_util' if args.redstar_bin else Path(shutil.which('convert_proj_weights_util') or '/missing-converter')).expanduser().absolute()
    if not executable.is_file():parser.error('Set REDSTAR_BIN/--redstar-bin or put convert_proj_weights_util on PATH')
    (root/'runs').mkdir(exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='input-migration-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-',dir=root/'runs'))
    inputs={};ops={};requests={};index={}
    def add(op):
        key=signature(op)
        if key not in index:
            if len(op.findall('Operators/elem')) not in (1,2):
                raise RuntimeError('Legacy converter supports one/two constituent operators only')
            for field in op.findall('.//phasings/elem'):
                if any(int(x) for x in (field.text or '').split()):
                    raise RuntimeError('Nonzero explicit legacy quark phasing requires a dedicated rotation audit')
            identifier='kanoni_migration_'+str(len(index));index[key]=identifier;ops[identifier]=copy.deepcopy(op)
        return index[key]
    for p in (args.files or sorted((root/'test_inputs').glob('*.xml'))):
        p=p.expanduser().absolute()
        tree=ET.parse(p);r=tree.getroot()
        if r.tag!='RedstarNPt':continue
        version=r.findtext('Param/version')
        if version not in ('12','14'):raise RuntimeError(f'Unsupported input version {version}: {p}')
        inputs[p]=(tree,version,p.read_bytes())
        if version=='12':
            for op in r.findall('.//Irrep/Op'):requests[id(op)]=add(op)
    synthetic=ET.Element('ProjectedOpWeights');ET.SubElement(synthetic,'version').text='3';entries=ET.SubElement(synthetic,'ProjectedOps')
    for identifier,op in ops.items():
        entry=ET.SubElement(entries,'elem');key=ET.SubElement(entry,'Key');ET.SubElement(key,'name').text=identifier;ET.SubElement(key,'mom_type').text='0 0 0'
        value=ET.SubElement(ET.SubElement(entry,'Val'),'elem');converted=copy.deepcopy(op);converted.tag='Key';value.append(converted);ET.SubElement(value,'Val').text='1'
    ET.ElementTree(synthetic).write(work/'legacy-operators.xml',encoding='utf-8',xml_declaration=True)
    with (work/'operator-conversion.log').open('w') as log:
        subprocess.run([str(executable),str(work/'legacy-operators.xml'),str(work/'class-operators.xml')],stdout=log,stderr=subprocess.STDOUT,check=True)
    converted={}
    for entry in ET.parse(work/'class-operators.xml').findall('ProjectedOps/elem'):
        values=entry.findall('Val/elem');assert len(values)==1
        converted[entry.findtext('Key/name')]=values[0].find('Key')
    assert converted.keys()==ops.keys()
    # Version-14 files can still contain obsolete projected names. Convert names only,
    # using the published factory alias map; do not rotate their already-classed momenta.
    old_names=sorted({node.text for tree,_,_ in inputs.values() for node in tree.findall('.//Op/Operators/elem/name') if re.search(r'_proj[0-9]+_p[0-9]+_', node.text or '')})
    aliases={}
    if old_names:
        alias_root=ET.Element('ProjectedOpWeights');ET.SubElement(alias_root,'version').text='3';alias_entries=ET.SubElement(alias_root,'ProjectedOps')
        for number,name in enumerate(old_names):
            entry=ET.SubElement(alias_entries,'elem');key=ET.SubElement(entry,'Key');ET.SubElement(key,'name').text=name;ET.SubElement(key,'mom_type').text='0 0 0'
            value=ET.SubElement(ET.SubElement(entry,'Val'),'elem');key=ET.SubElement(value,'Key');particle=ET.SubElement(ET.SubElement(key,'Operators'),'elem');ET.SubElement(particle,'name').text='alias_identity_'+str(number);ET.SubElement(particle,'mom_type').text='0 0 0';ET.SubElement(key,'CGs');ET.SubElement(value,'Val').text='1'
        ET.ElementTree(alias_root).write(work/'legacy-projected-names.xml',encoding='utf-8',xml_declaration=True)
        with (work/'projected-name-conversion.log').open('w') as log:subprocess.run([str(executable),str(work/'legacy-projected-names.xml'),str(work/'class-projected-names.xml')],stdout=log,stderr=subprocess.STDOUT,check=True)
        for entry in ET.parse(work/'class-projected-names.xml').findall('ProjectedOps/elem'):
            identity=entry.findtext('Val/elem/Key/Operators/elem/name');number=int(identity[len('alias_identity_'):]);aliases[old_names[number]]=entry.findtext('Key/name')
        if set(aliases)!=set(old_names):raise RuntimeError('Incomplete projected-name factory conversion')
    generated_weights={};report=[];pending=[]
    for path,(tree,version,original) in inputs.items():
        r=tree.getroot();param=r.find('Param');changes=[]
        if version=='12':
            for irrep in r.findall('.//Irrep'):
                old=irrep.find('Op')
                if old is None:continue
                new=copy.deepcopy(converted[requests[id(old)]]);new.tag='Op'
                # Preserve explicit zero phasing lists, which legacy particle keys do not serialize.
                for a,b in zip(old.findall('Operators/elem'),new.findall('Operators/elem')):
                    for phasing in a.findall('phasings'):
                        previous=b.find('phasings')
                        if previous is not None:b.remove(previous)
                        b.append(copy.deepcopy(phasing))
                i=list(irrep).index(old);irrep.remove(old);irrep.insert(i,new)
            param.find('version').text='14';options=param.find('cgc_options')
            if options is None:options=ET.SubElement(param,'cgc_options')
            for name,default in [('autoIrrepCG','true'),('rephaseIrrepCG','false'),('enableCGTargetMomRotation','false'),('autoCGVersion','1')]:
                old=param.find(name);new=options.find(name)
                if new is None:new=ET.SubElement(options,name);new.text=old.text if old is not None else default
                if old is not None:param.remove(old)
            changes+=['v12 to v14','SUN operator conversion through convert_proj_weights_util','explicit legacy target-momentum rotation=false']
        for node in r.findall('.//Op/Operators/elem/name'):
            old=node.text
            if old in aliases and aliases[old]!=old:
                node.text=aliases[old];changes.append('factory projected-name alias '+old+' -> '+node.text)
        if args.repair_rest_pairs:
            for op in r.findall('.//Irrep/Op'):
                particles=op.findall('Operators/elem');cgs=op.findall('CGs/elem')
                if len(particles)!=2 or len(cgs)!=1:continue
                a=particles[0].find('mom_class');b=particles[1].find('mom_class');target=cgs[0].findtext('target/mom_class')
                if a is None or b is None:continue
                first=list(map(int,a.text.split()));second=list(map(int,b.text.split()))
                if target=='0 0 0' and any(first) and first==second:
                    if cgs[0].findtext('left')!='1' or cgs[0].findtext('right')!='2':raise RuntimeError('Ambiguous CG pair slots')
                    b.text=' '.join(str(-x) for x in first);changes.append('restore back-to-back second constituent for zero-total pair: '+a.text+' + '+b.text)
        points=param.find('NPointList')
        if points is not None:
            if r.find('NPointList') is not None:raise RuntimeError('Ambiguous duplicate NPointList: '+str(path))
            param.remove(points);r.insert(list(r).index(param)+1,points);changes.append('move NPointList to v14 root')
        for entry in r.findall('DBFiles/proj_op_xmls/elem'):
            old=(entry.text or '').strip();name=Path(old).name;dest=root/'test_inputs/weights/v4'/name
            if not dest.is_file():
                candidates=[p for p in (root/'test_inputs/weights/v4').glob('*.xml') if p.name.lower()==name.lower()]
                if len(candidates)==1:dest=candidates[0]
                else:
                    source=root/'test_inputs/weights/v3'/name
                    if not source.is_file():raise RuntimeError('Missing original projected weights for '+old)
                    if name not in generated_weights:
                        temp=work/('converted-'+name)
                        with (work/(name+'.log')).open('w') as log:subprocess.run([str(executable),str(source),str(temp)],stdout=log,stderr=subprocess.STDOUT,check=True)
                        generated_weights[name]=(temp,dest)
            new='weights/v4/'+dest.name
            if old!=new:entry.text=new;changes.append('projected weights '+old+' -> '+new)
        options=param.find('cgc_options')
        if args.enable_auto_cg and options is not None and options.findtext('autoIrrepCG')=='false':
            options.find('autoIrrepCG').text='true';changes.append('replace unsupported fixed-CG mode with automatic CGs; phase/rotation retained')
        if args.enable_target_rotation and options is not None and options.findtext('enableCGTargetMomRotation')=='false':
            options.find('enableCGTargetMomRotation').text='true';changes.append('enable required CG rotation to original requested physical momentum')
        if args.fsq_database:
            if args.fsq_database.name not in ('gpdf.sdb','gpdf.more.sdb'):raise RuntimeError('Select a manifest-listed modern FSq database')
            cv=r.find('ColorVec/Param');cv.find('use_FSq').text='true'
            group=r.find('ColorVec/DBFiles/fsq_discoblock_dbs');group.clear();ET.SubElement(group,'elem').text=args.fsq_database.name
            changes.append('select modern FSq backend/database '+args.fsq_database.name+'; current smearing and quantum numbers unchanged')
        for group in r.findall('ColorVec/DBFiles/*'):
            for entry in list(group.findall('elem')):
                if not (entry.text or '').strip():
                    group.remove(entry);changes.append('remove empty database-list placeholder '+group.tag)
        for entry in r.findall('ColorVec/DBFiles/*/elem'):
            old=(entry.text or '').strip()
            if old and '/' in old:entry.text=Path(old).name;changes.append('portable database filename '+old)
        if r.findtext('Param/version')!='14' or r.find('NPointList') is None:raise RuntimeError('Invalid v14 structure: '+str(path))
        if r.findall('.//mom_type'):raise RuntimeError('Unconverted legacy momentum field: '+str(path))
        # Diagnostics are a run-time choice; preserve the tracked value here.
        if changes:
            try:payload=preserve_layout(original,r)
            except ValueError:
                ET.indent(tree,space='  ');payload=('\n'.join(line.rstrip() for line in ET.tostring(r,encoding='unicode').splitlines())+'\n').encode();payload=b'<?xml version="1.0"?>\n'+payload
            pending.append((path,payload,original))
        report.append({'file':path.name,'original_version':version,'new_version':'14','correlators':len(r.findall('NPointList/elem')),'changes':changes,'original_sha256':hashlib.sha256(original).hexdigest()})
    if args.write:
        for name,(source,dest) in generated_weights.items():
            if dest.exists():raise RuntimeError('Refusing to replace projected weights '+str(dest))
            shutil.copy2(source,dest)
        for path,payload,original in pending:
            assert path.read_bytes()==original
            (work/(path.name+'.original')).write_bytes(original);path.write_bytes(payload)
    result={'written':args.write,'converter':str(executable),'projected_name_aliases':aliases,'legacy_operator_definitions':len(ops),'inputs':report,'new_weight_files':list(generated_weights),'changed_files':len(pending),'note':'Only structural/schema conversion is established here. Run validate_inputs.py for graph and real-data evaluation.'}
    (work/'migration.json').write_text(json.dumps(result,indent=2)+'\n');print('Migration report:',work/'migration.json');print('Changed inputs:',len(pending),'legacy operator definitions:',len(ops))


if __name__=='__main__':main()
