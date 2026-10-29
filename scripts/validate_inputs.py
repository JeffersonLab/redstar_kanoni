#!/usr/bin/env python3
"""Run Kanoni v14 graph/numerical tests with independent database readback."""
import argparse
import copy
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET


def definition(node, tag=None):
    return (tag or node.tag, ' '.join((node.text or '').split()), tuple(definition(x) for x in node))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='*', type=Path)
    parser.add_argument('--redstar-bin',type=Path,default=os.environ.get('REDSTAR_BIN'))
    parser.add_argument('--dbutil',type=Path,default=os.environ.get('DBUTIL'))
    parser.add_argument('--database-dir',type=Path,default=os.environ.get('KANONI_DATA_DIR'))
    parser.add_argument('--threads',type=int,default=4)
    parser.add_argument('--timeout',type=int,default=600,help='seconds allowed per executable')
    parser.add_argument('--exporter',type=Path,help='safe numbered exporter for oversized/colliding names')
    parser.add_argument('--adat-config',type=Path,default=os.environ.get('ADAT_CONFIG'))
    args=parser.parse_args()
    if args.threads<1 or args.timeout<1:parser.error('threads and timeout must be positive')
    root=Path(__file__).resolve().parents[1]
    data=(args.database_dir or root/'test_inputs/data').expanduser().absolute()
    programs={name:(args.redstar_bin/name if args.redstar_bin else Path(shutil.which(name) or '/missing-'+name)).expanduser().absolute() for name in ('redstar_corr_graph','redstar_npt','view_corr_graph','extract_ops_util')}
    dbutil=(args.dbutil or Path(shutil.which('dbutil') or '/missing-dbutil')).expanduser().absolute()
    for p in [*programs.values(),dbutil]:
        if not p.is_file() or not os.access(p,os.X_OK):parser.error('Missing executable '+str(p))
    if not data.is_dir():parser.error('Missing Kanoni data home; run setup-data first')
    files=args.files or [p for p in sorted((root/'test_inputs').glob('*.xml')) if ET.parse(p).getroot().tag=='RedstarNPt']
    files=[p.expanduser().absolute() for p in files]
    if not all(p.is_file() for p in files):parser.error('Every selected input must exist')
    if len({p.stem for p in files})!=len(files):parser.error('Selected inputs need unique output names')
    (root/'runs').mkdir(exist_ok=True)
    expectations=json.loads((root/'test_inputs/validation-expectations.json').read_text())['cases']
    manifest=json.loads((root/'test_inputs/data-manifest.json').read_text())
    expected_data={e['name']:e for e in manifest['files']};verified_data={}
    output=Path(tempfile.mkdtemp(prefix='validation-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-',dir=root/'runs'))
    record={'status':'running','data_home':str(data),'resolved_data_home':str(data.resolve()),'threads':args.threads,'timeout':args.timeout,'cases':[],'current':None,'programs':{k:str(v) for k,v in programs.items()},'dbutil':str(dbutil),'program_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in {**programs,'dbutil':dbutil}.items()},'verified_data':verified_data,'dataset':manifest['dataset']}
    report=output/'results.json'
    def save():
        temp=report.with_suffix('.tmp');temp.write_text(json.dumps(record,indent=2)+'\n');temp.replace(report)
    env={**os.environ,'OMP_NUM_THREADS':str(args.threads),'OMP_DYNAMIC':'FALSE','OMP_MAX_ACTIVE_LEVELS':'1','VECLIB_MAXIMUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
    save();print('Validation directory:',output,flush=True)
    for source in files:
        source=source.expanduser().absolute();case={'file':source.name,'status':'running','commands':[],'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest()};record['cases'].append(case);record['current']={'file':source.name,'phase':'prepare'};save()
        run=output/source.stem;run.mkdir()
        def command(name,argv,cwd=run):
            record['current']={'file':source.name,'phase':name};save();log=run/(name+'.log');start=time.monotonic()
            step={'phase':name,'argv':list(map(str,argv)),'log':str(log),'started_at':datetime.now().astimezone().isoformat()};case['commands'].append(step);save()
            with log.open('w') as stream:
                try:p=subprocess.run(step['argv'],cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=args.timeout)
                except subprocess.TimeoutExpired:
                    step.update(status='timeout',seconds=time.monotonic()-start);save();raise RuntimeError(name+' timed out')
            step.update(returncode=p.returncode,seconds=time.monotonic()-start,status='passed' if p.returncode==0 else 'failed');save()
            if p.returncode:raise RuntimeError(name+' failed: '+'\n'.join(log.read_text(errors='replace').splitlines()[-7:]))
            return log.read_text(errors='replace')
        try:
            tree=ET.parse(source);x=tree.getroot()
            if x.tag!='RedstarNPt' or x.findtext('Param/version')!='14':raise RuntimeError('Expected RedstarNPt v14')
            points=x.findall('NPointList/elem');case['declared_correlators']=len(points)
            if not points or x.findall('.//mom_type'):raise RuntimeError('Empty selection or legacy momentum schema')
            param=x.find('Param');param.find('diagnostic_level').text='0';nt=int(param.findtext('Nt_corr'));case['time_samples']=nt
            db=x.find('DBFiles')
            for name,value in [('corr_graph_bin','corr_graph.bin'),('output_db','output.npt.sdb1')]:
                node=db.find(name)
                if node is None:node=ET.SubElement(db,name)
                node.text=value
            for name in ('corr_graph_xml','eval_graph_xml','noneval_graph_xml','vertex_coeff_xml','export_dag_xml','contraction_info_db','final_eval_graph_db','final_noneval_graph_db'):
                for node in db.findall(name):db.remove(node)
            for node in db.findall('proj_op_xmls/elem'):
                path=Path((node.text or '').strip());candidates=[source.parent/path,root/'test_inputs'/path]
                src=next((p for p in candidates if p.is_file()),None)
                if src is None:raise RuntimeError('Missing projected weights '+str(path))
                if path.is_absolute() or '..' in path.parts:raise RuntimeError('Projected weights must have portable relative paths')
                target=run/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
            for node in x.findall('ColorVec/DBFiles/*/elem'):
                path=data/Path((node.text or '').strip()).name
                if not path.is_file():raise RuntimeError('Missing source database '+str(path))
                if path.name not in verified_data:
                    if path.name not in expected_data:raise RuntimeError('Database absent from pinned manifest: '+path.name)
                    entry=expected_data[path.name];digest=hashlib.sha256()
                    with path.open('rb') as stream:
                        for block in iter(lambda:stream.read(4*1024*1024),b''):digest.update(block)
                    if path.stat().st_size!=entry['bytes'] or digest.hexdigest()!=entry['sha256']:raise RuntimeError('Database differs from pinned manifest: '+path.name)
                    verified_data[path.name]={'bytes':entry['bytes'],'sha256':digest.hexdigest()}
                node.text=str(path)
            case['fake_data_mode']=x.findtext('ColorVec/Param/fake_data_modeP')
            ET.indent(tree,space='  ');tree.write(run/'input.xml',encoding='utf-8',xml_declaration=True)
            command('graph',[programs['redstar_corr_graph'],'input.xml','graph.out.xml'])
            summary=command('view',[programs['view_corr_graph'],'corr_graph.bin'])
            count=int(re.search(r'Number of corrs = (\d+)',summary)[1]);graphs=int(re.search(r'Number of graphs = (\d+)',summary)[1]);case.update(correlators=count,graphs=graphs)
            if count!=len(points):raise RuntimeError('Graph count differs from declared correlator coverage')
            command('numerical',[programs['redstar_npt'],'input.xml','npt.out.xml'])
            log=(run/'numerical.log').read_text(errors='replace');assembled=len(re.findall(r'^Assemble corr= ',log,re.M))
            if assembled!=count or 'Closed correlator db' not in log:raise RuntimeError('Assembly/closure differs from graph coverage')
            command('keys',[dbutil,'output.npt.sdb1','keysxml','keys.xml'])
            keys=ET.parse(run/'keys.xml').getroot()
            if len(keys)!=count:raise RuntimeError('Stored key count differs from graph coverage')
            command('extract',[programs['extract_ops_util'],'operators.list','operators.xml','output.npt.sdb1'])
            extracted=ET.parse(run/'operators.xml').getroot();expected={definition(op,'Val') for k in keys for op in k.findall('NPoint/elem/Irrep/Op')};actual={definition(e.find('Val')) for e in extracted.findall('elem')}
            if not expected or expected!=actual or extracted.findall('.//mom_type'):raise RuntimeError('Extracted operators differ from independent database key definitions')
            readback=run/'readback';readback.mkdir();command('readback',[dbutil,str(run/'output.npt.sdb1'),'get',str(run/'keys.xml')],readback)
            exports=list(readback.glob('*.dat'));case['extracted_operators']=len(actual)
            if len(exports)!=count:
                exporter=args.exporter
                if exporter is None:
                    config=args.adat_config or dbutil.parent/'adat-config'
                    if not config.is_file():raise RuntimeError('dbutil filename export incomplete; supply --adat-config or --exporter')
                    fingerprint=hashlib.sha256((str(config.resolve())+'\n'+(root/'scripts/export_correlators.cc').read_text()).encode()).hexdigest()[:16]
                    exporter=root/'runs/tools'/fingerprint/'export_correlators'
                    if not exporter.is_file():command('build-exporter',['python3',root/'scripts/build_exporter.py','--adat-config',config,'--output',exporter])
                short=run/'readback-numbered'
                command('readback-numbered',[exporter,run/'output.npt.sdb1',short])
                entries=ET.parse(short/'index.xml').getroot().findall('elem')
                indexed={definition(e.find('Key'),'elem') for e in entries}
                if indexed!={definition(k) for k in keys} or len(entries)!=count:raise RuntimeError('Numbered exporter keys differ from independent dbutil key XML')
                exports=[short/e.findtext('filename') for e in entries]
                names=[e.findtext('standard_filename') or '' for e in entries]
                case.update(numbered_readback=True,dbutil_filenames_over_255_bytes=sum(len(n.encode())>255 for n in names),dbutil_duplicate_filenames=len(names)-len(set(names)),indexed_keys_match_dbutil=True)
            if len(exports)!=count:raise RuntimeError('Numerical export misses stored keys')
            zeros=0
            for p in exports:
                lines=p.read_text().splitlines();header=list(map(int,lines[0].split()))
                if header!=[1,nt,1,0,1] or len(lines)!=nt+1:raise RuntimeError('Wrong configuration/time shape: '+p.name)
                amplitude=0.
                for t,line in enumerate(lines[1:]):
                    v=list(map(float,line.split()))
                    if len(v)!=3 or v[0]!=t or not all(math.isfinite(z) for z in v):raise RuntimeError('Nonfinite/malformed numerical value: '+p.name)
                    amplitude=max(amplitude,abs(complex(v[1],v[2])))
                zeros+=amplitude==0.
            case.update(configurations=1,finite_complex_values=count*nt,zero_correlator_keys=zeros,operator_definitions_match_keys=True)
            expected=expectations.get(source.name,{})
            if expected.get('kind')=='symmetry_zero':
                if graphs!=0 or zeros!=count or count!=expected['correlators'] or case['fake_data_mode']=='true':raise RuntimeError('Symmetry-zero control differs from its exact expected coverage')
                case.update(status='passed_symmetry_zero',expectation=expected['reason'])
            else:
                if graphs==0:raise RuntimeError('No contraction graphs; review intended quantum numbers')
                case['status']='passed' if case['fake_data_mode']!='true' else 'passed_fake_data'
        except Exception as error:case.update(status='failed',error=str(error))
        save();print(source.name,case['status'],flush=True)
    record['current']=None
    record['summary']={status:sum(c['status']==status for c in record['cases']) for status in ('passed','passed_fake_data','passed_symmetry_zero','failed')}
    record['status']='attention_required' if record['summary']['failed'] else ('passed' if all(c['status']=='passed' for c in record['cases']) else 'passed_with_limits')
    save();print('Report:',report,flush=True)
    if record['summary']['failed']:raise SystemExit(1)


if __name__=='__main__':main()
