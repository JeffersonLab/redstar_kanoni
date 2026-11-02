#!/usr/bin/env python3
"""Generate a separate native-double candidate dataset; never replace active data."""
from pathlib import Path
import argparse,datetime,hashlib,json,math,os,re,shutil,subprocess,time
import xml.etree.ElementTree as E
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--chroma',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--dbutil',type=Path,required=True);p.add_argument('--threads',type=int,default=1);p.add_argument('--reuse-validated',type=Path,help='Copy only checksum-verified completed stages with identical inputs and executable');p.add_argument('--storage-info',type=Path,help='Native SUPERB complex-double header/metadata inspector');a=p.parse_args()
root=a.output.resolve();root.mkdir(parents=True,exist_ok=False);inputs=root/'inputs';shutil.copytree(a.inputs,inputs)
plan=json.loads((inputs/'recipe.json').read_text());env=dict(os.environ,OMP_NUM_THREADS=str(a.threads),OMP_DYNAMIC='FALSE',VECLIB_MAXIMUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
requested_rsd=float(plan['RsdCG'])
if not math.isfinite(requested_rsd) or requested_rsd<=0:raise ValueError('Recipe RsdCG must be finite and positive')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
state={'dataset':plan['dataset'],'status':'running','lattice':[4,4,4,16],'precision_bits':64,'RsdCG':requested_rsd,'threads':a.threads,'executable':str(a.chroma.resolve()),'executable_sha256':sha(a.chroma),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stages':[],'files':[]}
def save():
 (root/'generation.json').write_text(json.dumps(state,indent=2)+'\n')
try:
 prior=None
 if a.reuse_validated:
  prior=json.loads((a.reuse_validated/'generation.json').read_text())
  if prior['executable_sha256']!=state['executable_sha256']:raise RuntimeError('Cannot reuse stages from another executable')
 for spec in plan['stages']:
  residuals=E.parse(inputs/spec['input']).findall('.//RsdCG')
  if any(float(node.text)!=requested_rsd for node in residuals):raise RuntimeError('Recipe/input solver residual mismatch: '+spec['input'])
  if prior:
   old=next((v for v in prior['stages'] if v['input']==spec['input'] and v['status']=='passed' and v['input_sha256']==sha(inputs/spec['input'])),None)
   if old:
    copied=[]
    for name in spec['outputs']:
     item=next(v for v in prior['files'] if v['name']==name);src=a.reuse_validated/name
     if src.is_symlink() or src.stat().st_size!=item['bytes'] or sha(src)!=item['sha256']:raise RuntimeError('Cannot reuse changed output: '+name)
     shutil.copyfile(src,root/name);copied.append(item)
    state['files'].extend(copied);entry=dict(old,reused_from=str(a.reuse_validated.resolve()));state['stages'].append(entry);save();print('REUSE VALIDATED',spec['input'],flush=True);continue

  name=spec['input'];entry={'input':name,'input_sha256':sha(inputs/name),'outputs':spec['outputs'],'status':'running'};state['stages'].append(entry);save();print('START',name,flush=True)
  cmd=[str(a.chroma.resolve()),'-i',str(inputs/name),'-o',name+'.out.xml'];entry['command']=cmd;start=time.monotonic()
  with (root/(name+'.log')).open('w') as f:entry['returncode']=subprocess.run(cmd,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
  entry['seconds']=time.monotonic()-start;save()
  if entry['returncode']:raise RuntimeError(name+' failed')
  E.parse(root/(name+'.out.xml'));log=(root/(name+'.log')).read_text()
  if 'CHROMA: ran successfully' not in log:raise RuntimeError('Missing Chroma success marker: '+name)
  if not re.search(r'<basePrecision>64</basePrecision>',(root/(name+'.out.xml')).read_text()):raise RuntimeError('Stage is not a double-precision build: '+name)
  for output in spec['outputs']:
   f=root/output
   if not f.is_file() or f.stat().st_size==0:raise RuntimeError('Missing output: '+output)
   if f.suffix in ('.sdb','.sbt'):
    if f.suffix=='.sbt':
     if spec.get('storage')!='SUPERB' or a.storage_info is None:raise RuntimeError('Explicit SUPERB inspector required')
     inspect=[str(a.storage_info.resolve()),str(f)]
    else:inspect=[str(a.dbutil.resolve()),str(f),'meta']
    with (root/(output+'.meta.log')).open('w') as stream:subprocess.run(inspect,stdout=stream,stderr=subprocess.STDOUT,check=True)
    metadata=(root/(output+'.meta.log')).read_text();m=re.search(r'<DBMetaData>.*?</DBMetaData>',metadata,re.S)
    if not m:raise RuntimeError('Missing SDB metadata: '+output)
    xml=E.fromstring(m[0]);bits=xml.findtext('ProgramInfo/code_version/basePrecision')
    expected_mass=spec.get('mass_labels',{}).get(output)
    if expected_mass and xml.findtext('mass_label')!=expected_mass:raise RuntimeError('Native tensor mass coverage mismatch: '+output)
    if bits!='64':raise RuntimeError('SDB producer precision mismatch: '+output)
    item={'name':output,'bytes':f.stat().st_size,'sha256':sha(f),'producer_precision_bits':64,'id':xml.findtext('id'),'storage':'SUPERB' if f.suffix=='.sbt' else 'legacy-SDB'}
    state['files'].append(item)
   else:state['files'].append({'name':output,'bytes':f.stat().st_size,'sha256':sha(f)})
  entry['status']='passed';save();print('PASS',name,entry['seconds'],flush=True)
 state['status']='generated_not_promoted';state['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
 (root/'dataset-manifest.json').write_text(json.dumps({'dataset':plan['dataset'],'precision_bits':64,'RsdCG':requested_rsd,'files':state['files'],'generation_report':'generation.json'},indent=2)+'\n')
 print('DATASET GENERATED; numerical validation and fresh baseline establishment still required',flush=True)
except BaseException as error:
 state['status']='failed';state['error']=str(error);save();raise
