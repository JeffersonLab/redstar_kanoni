#!/usr/bin/env python3
"""Direct devel-format NPT/CORR_SUPERB comparison using saved MOD fields."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as E

from contraction_workflow import ROOT, digest, read_case, prepare_graph, prepare_npt, graph_summary
from compare_correlators import compare, definition, inspect_export
from redstar_runtime import configured_tools, run_limited


def exported_values(directory):
    return {definition(e.find('Key')): [complex(*map(float,line.split()[1:]))
            for line in (directory/e.findtext('filename')).read_text().splitlines()[1:]]
            for e in E.parse(directory/'index.xml').getroot()}


def provenance(log, mod_weights):
    text=Path(log).read_text()
    m=re.search(r'<DBMetaData>.*?</DBMetaData>',text,re.S)
    if not m:raise RuntimeError('Missing DBMetaData: '+str(log))
    x=E.fromstring(m[0]);w=x.findall('Weights/elem')
    result={k:x.findtext(k) for k in ('id','lattSize','ProgramInfo/run_date','ProgramInfo/code_version/basePrecision')}
    if w:
        values=[list(map(float,n.text.split())) for n in w]
        if len(values)!=len(mod_weights) or any(len(a)!=len(b) for a,b in zip(values,mod_weights)):
            raise RuntimeError('SDB/MOD eigenvalue metadata shape mismatch')
        result['max_abs_eigenvalue_metadata_difference']=max(abs(a-b) for u,v in zip(values,mod_weights) for a,b in zip(u,v))
    result['note']='Producer precision, not a claim that stored complex payloads are single precision. SDB metadata does not pin the MOD file checksum.'
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('case',type=Path)
    p.add_argument('--tools',type=Path,required=True,help='Redstar/ADAT executables TOML')
    p.add_argument('--chroma',type=Path,required=True)
    p.add_argument('--gauge-importer',type=Path,help='Required for historical saved-gauge mode')
    p.add_argument('--storage-info',type=Path,help='Native SUPERB metadata inspector')
    p.add_argument('--dataset-manifest',type=Path,help='Explicit new candidate manifest; uses its WEAK_FIELD input and canonical meson.sdb')
    p.add_argument('--exporter',type=Path,required=True)
    p.add_argument('--database-dir',type=Path,default=ROOT/'data')
    p.add_argument('--output',type=Path)
    p.add_argument('--threads',type=int,default=1)
    p.add_argument('--timeout',type=int,default=1800)
    p.add_argument('--stored-objects-control',action='store_true',help='Read the exact SDB propagators/mesons in CORR_SUPERB to isolate contractions')
    a=p.parse_args(argv)
    if a.threads<1 or a.timeout<1:p.error('threads and timeout must be positive')
    case,meta,graph=read_case(a.case)
    tools=configured_tools(a.tools)
    for key in ('redstar_corr_graph','view_corr_graph','redstar_npt','dbutil'):
        if not tools.get(key,Path('/missing')).is_file():p.error('Missing tool: '+key)
    data=a.database_dir.expanduser().absolute()
    if data.is_symlink() or not data.is_dir():p.error('Expected a real data directory')
    manifest=json.loads((a.dataset_manifest or ROOT/'test_inputs/mod-manifest.json').read_text())
    if not a.dataset_manifest and not a.gauge_importer:p.error('--gauge-importer required for historical saved-gauge mode')
    for item in manifest['files']:
        src=data/item['name']
        if src.is_symlink() or not src.is_file() or src.stat().st_size!=item['bytes'] or digest(src)!=item['sha256']:
            p.error('Missing or changed saved MOD file: '+str(src))
    for path in (a.chroma,a.exporter,*([a.gauge_importer] if a.gauge_importer else [])):
        if not path.is_file() or not os.access(path,os.X_OK):p.error('Missing executable: '+str(path))
    if a.output:
        run=a.output.absolute();run.mkdir(parents=True,exist_ok=False)
    else:
        (ROOT/'runs').mkdir(exist_ok=True);run=Path(tempfile.mkdtemp(prefix='direct-'+case.name+'-',dir=ROOT/'runs'))
    record={'status':'running','case':str(case),'metadata':meta,'mode':'stored_objects_control' if a.stored_objects_control else 'on_demand','MOD_manifest':manifest,'threads':a.threads,'commands':[], 'tools':{name:{'path':str(path),'sha256':digest(path)} for name,path in {**tools,'chroma':a.chroma,**({'gauge_importer':a.gauge_importer} if a.gauge_importer else {}),**({'storage_info':a.storage_info} if a.storage_info else {}),'exporter':a.exporter}.items()}}
    def save(): (run/'run.json').write_text(json.dumps(record,indent=2)+'\n')
    def execute(name,cmd):
        step={'stage':name,'argv':list(map(str,cmd))};record['commands'].append(step);save()
        with (run/(name+'.log')).open('w') as log:
            step['returncode']=run_limited(step['argv'],cwd=run,env=env,stdout=log,timeout=a.timeout)
        save()
        if step['returncode']:raise RuntimeError(name+' failed; see '+str(run/(name+'.log')))
    env=dict(os.environ,OMP_NUM_THREADS=str(a.threads),OMP_DYNAMIC='FALSE',OMP_MAX_ACTIVE_LEVELS='1',VECLIB_MAXIMUM_THREADS='1',OPENBLAS_NUM_THREADS='1',REDSTAR_SB_MEM_GB='6')
    print('Run directory:',run,flush=True);save()
    try:
        raw=(data/'colorvec.mod').read_bytes();mod=E.fromstring(re.search(rb'<MODMetaData>.*?</MODMetaData>',raw,re.S)[0]);weights=[list(map(float,n.text.split())) for n in mod.findall('Weights/elem')]
        record['SDB_provenance']={}
        tensor_props=sorted(v['name'] for v in manifest['files'] if v.get('storage')=='SUPERB' and v.get('id')=='propElemOp')
        tensor_mode=bool(a.dataset_manifest and tensor_props)
        if tensor_mode and not a.storage_info:raise RuntimeError('Native SUPERB inspector required')
        for name in ((tuple(tensor_props)+('meson.sbt',) if tensor_mode else ('prop.sdb','meson.sdb')) if a.dataset_manifest else ('prop.sdb','meson.sdb','meson.deriv.sdb','baryon.sdb')):
            execute(name+'-metadata',([a.storage_info,data/name] if tensor_mode else [tools['dbutil'],data/name,'meta']))
            record['SDB_provenance'][name]=provenance(run/(name+'-metadata.log'),weights)
        prepare_graph(case,graph,run)
        execute('graph',[tools['redstar_corr_graph'],'graph.xml','graph.out.xml']);E.parse(run/'graph.out.xml')
        execute('view',[tools['view_corr_graph'],'corr_graph.bin'])
        record['graph']=graph_summary((run/'view.log').read_text(),meta)
        npt_case=case
        if a.dataset_manifest:
            npt_case=run/'candidate-case';npt_case.mkdir()
            candidate=E.parse(case/'npt.xml')
            for node in candidate.findall('ColorVec/DBFiles/*/elem'):
                if node.text:
                    name=Path(node.text).name
                    if name=='meson.deriv.sdb':node.text='meson.sbt' if tensor_mode else 'meson.sdb'
                    elif tensor_mode and name=='prop.sdb':node.text=tensor_props[0]
            if tensor_mode:
                group=candidate.find('ColorVec/DBFiles/prop_dbs')
                for node in list(group):group.remove(node)
                for name in tensor_props:E.SubElement(group,'elem').text=name
            candidate.write(npt_case/'npt.xml',encoding='utf-8',xml_declaration=True)
        record['verified_data']=prepare_npt(npt_case,run,data,a.dataset_manifest)
        npt=E.parse(run/'npt.xml');npt.find('DBFiles/output_db').text='npt.sdb1';npt.write(run/'npt.xml',encoding='utf-8',xml_declaration=True)
        execute('npt',[tools['redstar_npt'],'npt.xml','npt.out.xml']);E.parse(run/'npt.out.xml')
        text=(run/'npt.log').read_text()
        if len(re.findall(r'^Assemble corr= ',text,re.M))!=meta['correlators'] or 'Closed correlator db' not in text:raise RuntimeError('NPT coverage/closure mismatch')
        tree=E.parse(case/meta.get('chroma_template','chroma.xml'));x=tree.getroot();cfg=x.find('Cfg')
        if a.dataset_manifest:
            producer=E.parse(data/'inputs/colorvec.ini.xml').getroot()
            if producer.findtext('Cfg/cfg_type')!='WEAK_FIELD':raise RuntimeError('Expected explicit WEAK_FIELD producer')
            for tag in ('Cfg','RNG'):
                old=x.find(tag)
                if old is not None:x.remove(old)
                x.append(deepcopy(producer.find(tag)))
            for node in x.findall('.//RsdCG'):node.text='1e-12'
            record['field_source']='WEAK_FIELD and RNG copied from the recorded colorvec producer input'
        else:
            execute('gauge-import',[a.gauge_importer.resolve(),data/'gauge.mod',run/'gauge.lime'])
            if 'squared error=0' not in (run/'gauge-import.log').read_text():raise RuntimeError('Gauge import did not verify exact roundtrip')
            record['derived_gauge_sha256']=digest(run/'gauge.lime')
            cfg.find('cfg_file').text='gauge.lime'
        corr=x.find('Param/InlineMeasurements/elem')
        corr.find('NamedObject/corr_file').text='superb.sdb1'
        corr.find('NamedObject/colorvec_files/elem').text=str((data/'colorvec.mod').resolve())
        if a.stored_objects_control:
            for name in (tensor_props if tensor_mode else ['prop.sdb']):E.SubElement(corr.find('Param/props'),'elem').text=str((data/name).resolve())
            E.SubElement(corr.find('Param/mesons'),'elem').text=str((data/('meson.sbt' if tensor_mode else ('meson.sdb' if a.dataset_manifest else 'meson.deriv.sdb'))).resolve())
        if x.findall('.//Name[.="CREATE_COLORVECS_SUPERB"]'):raise RuntimeError('Matched test must not regenerate eigenvectors')
        tree.write(run/'chroma.xml',encoding='utf-8',xml_declaration=True)
        execute('chroma',[a.chroma.resolve(),'-i','chroma.xml','-o','chroma.out.xml']);E.parse(run/'chroma.out.xml')
        log=(run/'chroma.log').read_text()
        if 'CHROMA: ran successfully' not in log:raise RuntimeError('Missing Chroma success marker')
        record['CG_solves']=log.count('CG_SOLVER_TIME:')
        # Export both full results even when numerical comparison fails.
        comparison_error=None
        try:compare(run/'npt.sdb1',run/'superb.sdb1',tools['dbutil'],a.exporter.resolve(),run/'comparison',1e-9,a.timeout)
        except RuntimeError as error:comparison_error=str(error)
        for label in ('reference','candidate'):
            shapes=inspect_export(run/'comparison'/label,run/'comparison'/(label+'-keys.xml'))
            if len(shapes)!=meta['correlators'] or any(s!=(1,meta['time_samples']) for s in shapes.values()):raise RuntimeError('Incomplete direct readback')
        reference=exported_values(run/'comparison/reference');candidate=exported_values(run/'comparison/candidate')
        if reference.keys()!=candidate.keys():raise RuntimeError('Direct comparison key mismatch')
        scale=max(abs(z) for row in reference.values() for z in row);floor=1e-12*max(scale,1e-30)
        errors=[abs(z-w) for k in reference for z,w in zip(reference[k],candidate[k])]
        norm=sum(abs(z)**2 for row in reference.values() for z in row)**.5
        failed=sum(abs(z-w)>1e-9*max(abs(z),abs(w))+floor for k in reference for z,w in zip(reference[k],candidate[k]))
        record['comparison']={'keys':len(reference),'finite_complex_values':len(errors),'max_abs_error':max(errors),'reference_max_abs':scale,'relative_frobenius_error':sum(e*e for e in errors)**.5/norm,'per_value_failures':failed,'relative_tolerance':1e-9,'absolute_floor':floor,'dbutil_comparison_error':comparison_error}
        record['status']='passed' if failed==0 and comparison_error is None else 'numerical_mismatch';save()
        print(record['status'],json.dumps(record['comparison']),flush=True)
        return int(record['status']!='passed')
    except (OSError,RuntimeError,ValueError,E.ParseError) as error:
        record.update(status='failed',error=str(error));save();print(str(error),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
