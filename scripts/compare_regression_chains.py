#!/usr/bin/env python3
"""Run matched native-tensor regression comparisons with exact coverage."""
from pathlib import Path
import sys,json,subprocess,shutil,os,time,copy,hashlib,xml.etree.ElementTree as E
import argparse
r=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description="Compare devel and experimental no_1pt NPT/CORR_SUPERB on stored native tensors; retain explicit deferrals and strict per-value gates.")
for flag in ['dataset','output','baseline-graph-bin','feature-graph-bin','baseline-npt','feature-npt','baseline-chroma','feature-chroma','dbutil','exporter']:
 parser.add_argument('--'+flag,type=Path,required=True)
parser.add_argument('--inputs',type=Path,default=r/'regressions/native-superb-v3/inputs')
parser.add_argument('--qualification',required=True,help='Actual source/build qualification recorded verbatim in results')
parser.add_argument('--chain',choices=['both','devel','no_1pt'],default='both')
parser.add_argument('--npt-only',action='store_true',help='Validate NPT key/shape/finite coverage without a CORR comparison; honors separate NPT deferrals')
parser.add_argument('--cases',nargs='+',help='Explicit subset for targeted validation; omitted runs the full inventory')
parser.add_argument('--timeout',type=int,default=900)
parser.add_argument('--max-rss-mb',type=int,default=8192)
parser.add_argument('--tensor-gb',type=float,default=2)
args=parser.parse_args()
for name,value in vars(args).items():
 if isinstance(value,Path):setattr(args,name,value.resolve())
if args.timeout<=0 or args.max_rss_mb<=0 or args.tensor_gb<=0:parser.error('Resource limits must be positive')
sys.path.insert(0,str(r/'scripts'))
from contraction_workflow import read_case,prepare_graph
from compare_correlators import compare,inspect_export
from compare_npt_superb import exported_values
from redstar_runtime import run_limited
base=args.dataset;sphere=base/'meson.sbt'
manifest=json.loads((base/'dataset-manifest.json').read_text())
for item in manifest['files']:
 path=base/item['name']
 if not path.is_file() or path.stat().st_size!=item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
  raise RuntimeError('Dataset checksum/size mismatch: '+str(path))
root=args.output;root.mkdir()
policy=json.loads((r/'docs/regression-policy.json').read_text())
inventory=sorted(p.name for p in (r/'regressions/redstar').iterdir() if (p/'case.json').exists())
if args.cases:
 unknown=set(args.cases)-set(inventory)
 if unknown:parser.error('Unknown cases: '+', '.join(sorted(unknown)))
 inventory=[name for name in inventory if name in args.cases]
# Pion first: validate the experimental chain before the larger cases.
inventory=([name for name in inventory if name=='pion']+[name for name in inventory if name!='pion']);env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',OMP_DYNAMIC='FALSE',REDSTAR_SB_MEM_GB=str(args.tensor_gb))
state={'status':'running','mode':'stored native tensors; full finite readback and strict per-value comparison','scope':'explicit user deferrals retained','requested_cases':inventory,'requested_chain':args.chain,'npt_only':args.npt_only,'experimental_no_1pt':True,'cases':[]}
state['build_qualification']=args.qualification
state['data_provenance']={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [base/'dataset-manifest.json',base/'colorvec.mod',sphere,*sorted(base.glob('prop-*.sbt')),*sorted(base.glob('genprop-*.sbt')),base/'baryon.sbt']}
state['program_sha256']={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [args.baseline_chroma,args.feature_chroma,args.baseline_npt,args.feature_npt,args.dbutil,args.exporter,*[directory/name for directory in [args.baseline_graph_bin,args.feature_graph_bin] for name in ['redstar_corr_graph','view_corr_graph']]]}
def save():
 tmp=root/'results.tmp';tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(root/'results.json')
def execute(d,label,cmd,entry):
 step={'stage':label,'argv':list(map(str,cmd))};entry['commands'].append(step);save()
 with (d/(label+'.log')).open('w') as f:step['returncode']=run_limited(step['argv'],cwd=d,env=env,stdout=f,timeout=args.timeout,memory_limit_mb=args.max_rss_mb)
 save()
 if step['returncode']:raise RuntimeError(label+' failed; see '+str(d/(label+'.log')))
def node(parent,tag,text):
 n=parent.find(tag)
 if n is None:n=E.SubElement(parent,tag)
 n.text=str(text)
def numerical(case,d,chain):
 t=E.parse(args.inputs/(case+'.xml'));x=t.getroot()
 if x.findtext('ColorVec/Param/fake_data_modeP')!='false':raise RuntimeError('Numerical input must explicitly disable fake data')
 if chain=='no_1pt':node(x.find('Param'),'average_1pt_diagrams','false')
 for group in x.findall('ColorVec/DBFiles/*'):
  for n in group.findall('elem'):n.text=str(sphere if group.tag=='smeared_meson_dbs' else base/Path(n.text).name)
 node(x.find('DBFiles'),'corr_graph_bin','corr_graph.bin');node(x.find('DBFiles'),'output_db','output.sdb1');t.write(d/'npt.xml',encoding='utf-8',xml_declaration=True);return t
for name in inventory:
 deferred=policy['deferred_by_user'].get(name,{}).get('npt' if args.npt_only else 'corr_superb',False)
 for chain in (('devel','no_1pt') if args.chain=='both' else (args.chain,)):
  entry={'case':name,'chain':chain,'status':'deferred_by_user' if deferred else 'running','commands':[]};state['cases'].append(entry);save()
  if deferred:continue
  d=root/chain/name;d.mkdir(parents=True)
  try:
   case,meta,graph=read_case(r/'regressions/redstar'/name)
   if chain=='no_1pt':node(graph.getroot().find('Param'),'average_1pt_diagrams','false')
   prepare_graph(case,graph,d)
   bindir=args.baseline_graph_bin if chain=='devel' else args.feature_graph_bin
   execute(d,'graph',[bindir/'redstar_corr_graph','graph.xml','graph.out.xml'],entry);execute(d,'view',[bindir/'view_corr_graph','corr_graph.bin'],entry)
   expected=3 if chain=='devel' else 4
   if 'Version = '+str(expected) not in (d/'view.log').read_text():raise RuntimeError('Wrong graph format for chain')
   nt=numerical(name,d,chain)
   npt=args.baseline_npt if chain=='devel' else args.feature_npt
   execute(d,'npt',[npt,'npt.xml','npt.out.xml'],entry);E.parse(d/'npt.out.xml')
   if args.npt_only:
    keys=d/'npt-keys.xml';export=d/'npt-export'
    execute(d,'keys',[args.dbutil,d/'output.sdb1','keysxml',keys],entry)
    execute(d,'export',[args.exporter,d/'output.sdb1',export],entry)
    shapes=inspect_export(export,keys)
    if len(shapes)!=meta['correlators'] or any(shape!=(1,meta['time_samples']) for shape in shapes.values()):raise RuntimeError('NPT-only coverage mismatch')
    if meta.get('symmetry_zero') and any(z!=0 for row in exported_values(export).values() for z in row):raise RuntimeError('Symmetry-zero control is not zero')
    entry.update(status='passed',npt_only=True,keys=len(shapes),finite_complex_values=sum(c*t for c,t in shapes.values()))
    save();print(chain,name,'NPT-only passed',flush=True);continue
   template=E.parse(r/'regressions/corr_superb/chroma.xml');x=template.getroot();producer=E.parse(base/'inputs/colorvec.ini.xml').getroot()
   for tag in ('Cfg','RNG'):
    old=x.find(tag)
    if old is not None:x.remove(old)
    x.append(copy.deepcopy(producer.find(tag)))
   corr=x.find('Param/InlineMeasurements/elem');p=corr.find('Param');np=nt.getroot().find('Param')
   node(p,'num_vecs',nt.findtext('ColorVec/Param/num_vecs'));node(p,'t_origin',np.findtext('t_origin'));node(p,'Nt_forward',meta['time_samples']);node(p,'zeroUnsmearedGraphsP',np.findtext('zeroUnsmearedGraphsP'))
   node(p,'average_1pt_diagrams',np.findtext('average_1pt_diagrams'))
   fmap=p.find('flavor_to_mass');fprop=p.find('flavor_to_prop');prop_template=copy.deepcopy(fprop.find('elem/Propagator'));fmap.clear();fprop.clear()
   for fm in nt.findall('ColorVec/Param/FlavorToMass/elem'):
    flavor=fm.findtext('flavor');mass=fm.findtext('mass')
    if flavor=='g':continue # gluonic vertices are explicitly deferred by user.
    m=E.SubElement(fmap,'elem');E.SubElement(m,'flavor').text=flavor;E.SubElement(m,'mass').text=mass
    v=E.SubElement(fprop,'elem');E.SubElement(v,'flavor').text=flavor;v.append(copy.deepcopy(prop_template));v.find('Propagator/FermionAction/Mass').text=mass.removeprefix('U')
   for n in p.findall('.//RsdCG'):n.text=str(manifest['RsdCG'])
   for tag,paths in [('props',sorted(base.glob('prop-*.sbt'))),('mesons',[sphere]),('baryons',[base/'baryon.sbt']),('genprops',sorted(base.glob('genprop-*.sbt')))]:
    group=p.find(tag);group.clear()
    for path in paths:E.SubElement(group,'elem').text=str(path)
   corr.find('NamedObject/colorvec_files/elem').text=str(base/'colorvec.mod');corr.find('NamedObject/corr_file').text='superb.sdb1';template.write(d/'chroma.xml',encoding='utf-8',xml_declaration=True)
   chroma=args.baseline_chroma if chain=='devel' else args.feature_chroma
   execute(d,'chroma',[chroma,'-i','chroma.xml','-o','chroma.out.xml'],entry);E.parse(d/'chroma.out.xml')
   dbutil_error=None
   try:
    report=compare(d/'output.sdb1',d/'superb.sdb1',args.dbutil,args.exporter,d/'comparison',1e-9,args.timeout)
   except RuntimeError as error:
    dbutil_error=str(error)
    report=json.loads((d/'comparison/comparison.json').read_text())
    # Numerical acceptance remains the original full per-value gate, including
    # its global scaled floor. The relative-only dbutil result is retained.
    if not report.get('exact_key_coverage') or report.get('keys') is None:raise
   entry['dbutil_relative_only_diagnostic']=dbutil_error
   # Full finite readback and exact key/shape checks accompany dbutil compare.
   expected_keys=meta['correlators']
   if report['keys']!=expected_keys or report['finite_complex_values_per_database']!=expected_keys*meta['time_samples']:raise RuntimeError('Unexpected comparison coverage')
   reference=exported_values(d/'comparison/reference');candidate=exported_values(d/'comparison/candidate')
   if reference.keys()!=candidate.keys():raise RuntimeError('Strict readback key mismatch')
   scale=max((abs(z) for row in reference.values() for z in row),default=0);floor=1e-12*max(scale,1e-30)
   failures=sum(abs(z-w)>1e-9*max(abs(z),abs(w))+floor for k in reference for z,w in zip(reference[k],candidate[k]))
   errors=[abs(z-w) for k in reference for z,w in zip(reference[k],candidate[k])]
   strict={'relative_tolerance':1e-9,'absolute_floor':floor,'per_value_failures':failures,'max_abs_error':max(errors,default=0),'finite_complex_values':len(errors)}
   (d/'strict-comparison.json').write_text(json.dumps(strict,indent=2)+'\n');entry['strict_comparison']=strict
   if failures:raise RuntimeError('Strict per-value comparison failed')
   if meta.get('symmetry_zero') and any(z!=0 or w!=0 for k in reference for z,w in zip(reference[k],candidate[k])):raise RuntimeError('Symmetry-zero control is not exactly zero')
   entry.update(status='passed',keys=report['keys'],finite_complex_values=report['finite_complex_values_per_database'],CG_solves=(d/'chroma.log').read_text().count('CG_SOLVER_TIME:'))
  except BaseException as e:
   if isinstance(e,KeyboardInterrupt):raise
   entry.update(status='failed',error=str(e))
  save();print(chain,name,entry['status'],entry.get('error',''),flush=True)
state['status']='passed' if all(c['status'] in ('passed','deferred_by_user') for c in state['cases']) else 'attention_required';save();print(root,flush=True)

sys.exit(0 if state["status"]=="passed" else 1)
