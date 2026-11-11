"""Split graph, Redstar numerical, and vanilla Chroma regression workflows."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from compare_correlators import compare, definition
from redstar_runtime import configured_tools, run_limited

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = 'output.sdb1'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def read_case(path):
    path = path.expanduser().resolve(strict=True)
    meta = json.loads((path/'case.json').read_text())
    if meta.get('schema_version') != 1 or meta['kind'] not in ('redstar', 'corr_superb'):
        raise ValueError('Expected a split regression case.json schema_version 1')
    graph = ET.parse(path/'graph.xml')
    x = graph.getroot()
    if x.tag != 'RedstarNPt' or x.findtext('Param/version') != '14' or x.find('ColorVec') is not None:
        raise ValueError('graph.xml must be graph-only RedstarNPt v14')
    if list(map(int, x.findtext('Param/Layout/lattSize').split())) != [4,4,4,16]:
        raise ValueError('These regression cases require a 4 x 4 x 4 x 16 lattice')
    if len(x.findall('NPointList/elem')) != meta['correlators'] or x.findall('.//mom_type'):
        raise ValueError('Graph selection differs from case coverage or uses legacy keys')
    if int(x.findtext('Param/Nt_corr')) != meta['time_samples']:
        raise ValueError('Graph time coverage differs from case metadata')
    return path, meta, graph


def prepare_graph(case, graph, run):
    """Stage only graph inputs and their explicitly declared projected weights."""
    x = graph.getroot()
    x.find('Param/diagnostic_level').text = '0'
    db = x.find('DBFiles')
    projected = deepcopy(db.find('proj_op_xmls'))
    db.clear()
    if projected is not None:
        db.append(projected)
    else:
        ET.SubElement(db, 'proj_op_xmls')
    ET.SubElement(db, 'corr_graph_bin').text = 'corr_graph.bin'
    for node in db.findall('proj_op_xmls/elem'):
        p = Path(node.text.strip())
        if p.is_absolute() or '..' in p.parts:
            raise ValueError('Projected weights must be portable paths inside the case')
        src = case/p
        if src.is_symlink() or not src.is_file():
            raise ValueError('Missing regular projected weight: '+str(src))
        dest = run/p
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src,dest)
    graph.write(run/'graph.xml', encoding='utf-8', xml_declaration=True)


def graph_summary(text, meta):
    fields = {'version': r'Version = (\d+)', 'correlators': r'Number of corrs = (\d+)',
              'graphs': r'Number of graphs = (\d+)', 'time_samples': r'Nt_corr = (\d+)'}
    result = {}
    for name, pattern in fields.items():
        match = re.search(pattern,text)
        if not match:
            raise RuntimeError('Missing graph summary field: '+name)
        result[name] = int(match[1])
    lattice = re.search(r'Lattice size = ([\d ]+)',text)
    if not lattice or list(map(int,lattice[1].split())) != [4,4,4,16]:
        raise RuntimeError('Generated graph lattice mismatch')
    if result['version'] != 3:
        raise RuntimeError('Established devel regressions require graph format 3; no_1pt is experimental')
    for name in ('correlators','time_samples'):
        if result[name] != meta[name]:
            raise RuntimeError('Generated graph '+name+' differs from case')
    zero = meta.get('symmetry_zero',False)
    if (result['graphs']==0) != zero:
        raise RuntimeError('Unexpected empty/nonempty graph coverage')
    return result


def prepare_npt(case, run, data, data_manifest=None):
    tree = ET.parse(case/'npt.xml')
    x = tree.getroot()
    if x.tag != 'RedstarNPt' or x.find('NPointList') is not None or x.find('ColorVec') is None:
        raise ValueError('npt.xml must be numerical-only, with ColorVec and no NPointList')
    if x.findtext('ColorVec/Param/fake_data_modeP') != 'false':
        raise ValueError('These established numerical cases require real data')
    if data.is_symlink() or not data.is_dir():
        raise ValueError('Use a real dataset directory; run ./setup-data first')
    data = data.resolve()
    manifest = json.loads((data_manifest or ROOT/'test_inputs/data-manifest.json').read_text())
    expected = {item['name']:item for item in manifest['files']}
    verified = {}
    for node in x.findall('ColorVec/DBFiles/*/elem'):
        name = Path((node.text or '').strip()).name
        if not name:
            continue
        src = data/name
        if name not in expected or src.is_symlink() or not src.is_file():
            raise ValueError('Missing regular pinned database: '+str(src))
        if name not in verified:
            item = expected[name]
            if src.stat().st_size != item['bytes'] or digest(src) != item['sha256']:
                raise ValueError('Dataset checksum mismatch: '+name)
            verified[name] = item['sha256']
        node.text = os.path.relpath(src,run)
    x.find('DBFiles/corr_graph_bin').text = 'corr_graph.bin'
    x.find('DBFiles/output_db').text = OUTPUT
    tree.write(run/'npt.xml',encoding='utf-8',xml_declaration=True)
    return verified


def prepare_chroma(case, run, meta, graph):
    """Stage the shared MOD input or an explicitly selected legacy generated-basis input."""
    source = case/meta.get('chroma_template','../chroma.xml')
    tree = ET.parse(source)
    x = tree.getroot()
    if x.tag != 'chroma' or list(map(int,x.findtext('Param/nrow').split())) != [4,4,4,16]:
        raise ValueError('Shared Chroma template must have geometry 4 x 4 x 4 x 16')
    measurements = x.findall('Param/InlineMeasurements/elem')
    names=[m.findtext('Name') for m in measurements]
    if names not in (['CREATE_COLORVECS_SUPERB','CORR_SUPERB'],['CORR_SUPERB']):
        raise ValueError('Expected CORR_SUPERB, optionally preceded by legacy color-vector generation')
    create=measurements[0] if len(measurements)==2 else None
    corr=measurements[-1]
    for m in measurements:
        if int(m.findtext('Param/num_vecs')) != meta['num_vecs'] or int(m.findtext('Param/Nt_forward')) != meta['time_samples']:
            raise ValueError('Shared Chroma template and case vector/time coverage differ')
    origin = meta['t_origin']
    fixed_times = {int(n.text) for n in graph.findall('NPointList/elem/NPoint/elem/t_slice') if int(n.text)>=0}
    if fixed_times != {origin}:
        raise ValueError('Shared Chroma template requires all fixed graph endpoints at the declared origin')
    if (create is not None and int(create.findtext('Param/t_start')) != origin) or int(corr.findtext('Param/t_origin')) != origin:
        raise ValueError('Shared Chroma template and graph source origin differ')
    if any(corr.findall('Param/'+tag+'/elem') for tag in ('props','genprops','mesons','baryons')):
        raise ValueError('Fresh CORR_SUPERB cases require empty elemental/propagator input lists')
    if corr.findtext('NamedObject/corr_graph_file') != 'corr_graph.bin' or corr.findtext('NamedObject/corr_file') != OUTPUT:
        raise ValueError('Shared Chroma template must use corr_graph.bin and '+OUTPUT)
    tree.write(run/'chroma.xml',encoding='utf-8',xml_declaration=True)
    return digest(source)


def validate_values(run, meta):
    directory = run/'comparison/candidate'
    entries = ET.parse(directory/'index.xml').getroot().findall('elem')
    if len(entries) != meta['correlators']:
        raise RuntimeError('Numerical key coverage mismatch')
    zero = 0
    for entry in entries:
        lines = (directory/entry.findtext('filename')).read_text().splitlines()
        if list(map(int,lines[0].split()))[:2] != [1,meta['time_samples']]:
            raise RuntimeError('Numerical configuration/time shape mismatch')
        values = [complex(*map(float,line.split()[1:])) for line in lines[1:]]
        zero += not any(values)
    if meta.get('symmetry_zero',False):
        if zero != meta['correlators']:
            raise RuntimeError('Exact symmetry-zero control became nonzero')
    elif zero:
        raise RuntimeError('Unexpected zero-valued correlator channels')
    basis = meta.get('basis')
    if basis:
        pairs = {tuple(definition(n.find('Irrep/Op')) for n in e.findall('Key/NPoint/elem')) for e in entries}
        sinks={p[0] for p in pairs};sources={p[1] for p in pairs}
        if len(sinks)!=basis or len(sources)!=basis or pairs!={(s,t) for s in sinks for t in sources}:
            raise RuntimeError('Incomplete source/sink operator matrix')
    result = {'keys':len(entries),'finite_complex_values':len(entries)*meta['time_samples'], 'zero_channels':zero}
    if meta['kind']=='corr_superb':
        def load(label):
            directory=run/'comparison'/label
            return {definition(e.find('Key')):[complex(*map(float,line.split()[1:])) for line in (directory/e.findtext('filename')).read_text().splitlines()[1:]] for e in ET.parse(directory/'index.xml').getroot()}
        reference=load('reference');candidate=load('candidate')
        scale=max(abs(z) for row in reference.values() for z in row)
        floor=1e-12*max(scale,1e-30);maximum=0.
        for key in reference:
            for z,w in zip(reference[key],candidate[key]):
                error=abs(z-w);maximum=max(maximum,error)
                if error>1e-9*max(abs(z),abs(w))+floor:
                    raise RuntimeError('CORR_SUPERB per-value numerical disagreement')
        result['per_value_comparison']={'max_abs_error':maximum,'relative_tolerance':1e-9,'absolute_floor':floor}
    return result


def main(mode, argv=None):
    parser = argparse.ArgumentParser(description=__doc__+' Mode: '+mode)
    parser.add_argument('case',type=Path,help='case directory containing case.json and graph.xml')
    parser.add_argument('--output',type=Path,help='fresh output directory; default: unique runs/ directory')
    parser.add_argument('--tools',type=Path,help='optional TOML [executables], all paths absolute')
    parser.add_argument('--redstar-bin',type=Path,default=os.environ.get('REDSTAR_BIN'))
    parser.add_argument('--chroma-bin',type=Path,help='absolute Chroma bin directory (or CHROMA_BIN)')
    parser.add_argument('--gauge-importer',type=Path,help='MOD-to-QIO importer for saved-field CORR_SUPERB cases')
    parser.add_argument('--dbutil',type=Path)
    parser.add_argument('--exporter',type=Path)
    parser.add_argument('--adat-config',type=Path)
    parser.add_argument('--database-dir',type=Path,default=os.environ.get('KANONI_DATA_DIR'))
    parser.add_argument('--threads',type=int,default=4)
    parser.add_argument('--timeout',type=int,default=1800,help='seconds per executable')
    parser.add_argument('--contraction-memory-gb',type=int,default=6)
    args = parser.parse_args(argv)
    if args.threads<1 or args.timeout<1 or args.contraction_memory_gb<1:
        parser.error('threads, timeout and contraction memory must be positive')
    run = None
    record = {'mode':mode,'status':'preparing','commands':[],'tools':{}}
    def save():
        (run/'run.json').write_text(json.dumps(record,indent=2)+'\n')
    try:
        case,meta,graph = read_case(args.case)
        if mode != 'graph' and mode != meta['kind']:
            raise ValueError('Selected case is for '+meta['kind']+', not '+mode)
        tools = configured_tools(args.tools) if args.tools else {}
        from redstar_runtime import required_tools
        names = ('redstar_corr_graph', 'view_corr_graph') + (('redstar_npt',) if mode == 'redstar' else ())
        selected = required_tools('redstar', names, args.redstar_bin, tools)
        if mode == 'corr_superb':
            selected.update(required_tools('chroma', ('chroma',), args.chroma_bin, tools))
        def tool(name, override=None):
            if name in ('redstar_corr_graph', 'view_corr_graph', 'redstar_npt', 'chroma'):
                p = selected[name]
            else:
                p = override or tools.get(name) or Path(shutil.which(name) or '/missing-'+name)
            p = p.expanduser().resolve()
            if not p.is_file() or not os.access(p,os.X_OK):
                raise ValueError('Missing executable '+str(p)+'; use --tools or explicit tool options')
            record['tools'][name]={'path':str(p),'sha256':digest(p)}
            return p
        generator=tool('redstar_corr_graph')
        viewer=tool('view_corr_graph')
        if mode!='graph':
            reference=case/meta['reference']
            if reference.is_symlink():raise ValueError('Reference database must be a regular file, not a symlink')
            reference=reference.resolve(strict=True)
            if digest(reference)!=meta['reference_sha256']:
                raise ValueError('Missing/mismatched trusted reference; restore the pinned baseline, never overwrite it')
            numerical=tool('redstar_npt') if mode=='redstar' else tool('chroma')
            dbutil=tool('dbutil',args.dbutil)
        if args.output:
            target=args.output.expanduser().absolute();target.mkdir(parents=True,exist_ok=False);run=target
        else:
            (ROOT/'runs').mkdir(exist_ok=True)
            run=Path(tempfile.mkdtemp(prefix=mode+'-'+case.name+'-',dir=ROOT/'runs'))
        record.update(status='running',case=str(case),metadata=meta,threads=args.threads,
                      contraction_memory_gb=args.contraction_memory_gb,case_sha256=digest(case/'case.json'),
                      graph_input_sha256=digest(case/'graph.xml'))
        save();print('Run directory:',run,flush=True)
        env=dict(os.environ,OMP_NUM_THREADS=str(args.threads),OMP_DYNAMIC='FALSE',OMP_MAX_ACTIVE_LEVELS='1',VECLIB_MAXIMUM_THREADS='1',OPENBLAS_NUM_THREADS='1',REDSTAR_SB_MEM_GB=str(args.contraction_memory_gb))
        def execute(name, command):
            step={'stage':name,'argv':list(map(str,command))};record['commands'].append(step);save()
            with (run/(name+'.log')).open('w') as log:
                step['returncode']=run_limited(step['argv'],cwd=run,env=env,stdout=log,timeout=args.timeout)
            save()
            if step['returncode']:
                raise RuntimeError(name+' failed; see '+str(run/(name+'.log')))
        prepare_graph(case,graph,run)
        record['prepared_graph_inputs']={str(p.relative_to(run)):digest(p) for p in run.rglob('*.xml')}
        save()
        execute('graph',[generator,'graph.xml','graph.out.xml'])
        ET.parse(run/'graph.out.xml')
        if not (run/'corr_graph.bin').is_file():raise RuntimeError('Missing corr_graph.bin')
        execute('view',[viewer,'corr_graph.bin'])
        record['graph']=graph_summary((run/'view.log').read_text(),meta)
        record['graph_sha256']=digest(run/'corr_graph.bin');save()
        if mode=='graph':
            record['status']='graph_passed';save();return 0
        if mode=='redstar':
            record['verified_data']=prepare_npt(case,run,args.database_dir or ROOT/'data')
            record['npt_input_sha256']=digest(case/'npt.xml')
            execute('npt',[numerical,'npt.xml','npt.out.xml']);ET.parse(run/'npt.out.xml')
            text=(run/'npt.log').read_text()
            if len(re.findall(r'^Assemble corr= ',text,re.M))!=meta['correlators'] or 'Closed correlator db' not in text:
                raise RuntimeError('Incomplete Redstar correlator assembly/closure')
        else:
            record['chroma_input_sha256']=prepare_chroma(case,run,meta,graph)
            tree=ET.parse(run/'chroma.xml')
            if len(tree.findall('Param/InlineMeasurements/elem'))==1:
                data=(args.database_dir or ROOT/'data').absolute()
                manifest=json.loads((ROOT/'test_inputs/mod-manifest.json').read_text())
                for item in manifest['files']:
                    path=data/item['name']
                    if data.is_symlink() or path.is_symlink() or not path.is_file() or digest(path)!=item['sha256']:
                        raise ValueError('Saved MOD checksum mismatch: '+str(path))
                importer=tool('gauge_importer',args.gauge_importer)
                execute('gauge-import',[importer,data/'gauge.mod',run/'gauge.lime'])
                if 'squared error=0' not in (run/'gauge-import.log').read_text():raise RuntimeError('Inexact gauge import')
                tree.find('Cfg/cfg_file').text='gauge.lime'
                tree.find('.//colorvec_files/elem').text=str((data/'colorvec.mod').resolve())
                tree.write(run/'chroma.xml',encoding='utf-8',xml_declaration=True)
                record['MOD_manifest']=manifest
            execute('chroma',[numerical,'-i','chroma.xml','-o','chroma.out.xml']);ET.parse(run/'chroma.out.xml')
            if 'CHROMA: ran successfully' not in (run/'chroma.log').read_text():
                raise RuntimeError('Missing Chroma completion marker')
        if not (run/OUTPUT).is_file():raise RuntimeError('Missing final correlator database')
        exporter=args.exporter or tools.get('exporter')
        if exporter is None:
            config=args.adat_config or tools.get('adat_config') or dbutil.parent/'adat-config'
            execute('build-exporter',[sys.executable,ROOT/'scripts/build_exporter.py','--adat-config',config,'--output',run/'export-correlators'])
            exporter=run/'export-correlators'
        exporter=tool('exporter',exporter)
        compare(reference,run/OUTPUT,dbutil,exporter,run/'comparison',meta.get('relative_tolerance',1e-12),args.timeout)
        record['readback']=validate_values(run,meta)
        record.update(status='passed',output_sha256=digest(run/OUTPUT));save()
        print('PASS:',meta['correlators'],'correlators, independent readback and pinned-reference comparison',flush=True)
        return 0
    except (OSError,ValueError,RuntimeError,ET.ParseError,subprocess.SubprocessError,KeyError) as error:
        if run is not None and run.is_dir():
            record.update(status='failed',error=str(error));save()
        print(str(error),file=sys.stderr)
        return 1
