from pathlib import Path
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest

import test_run_chroma as serial_tests

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'scripts'))
from redstar_runtime import run_limited


class ChromaMPITests(unittest.TestCase):
    executable = serial_tests.ChromaRunnerTests.executable
    run_job = serial_tests.ChromaRunnerTests.run_job

    def setUp(self):
        serial_tests.ChromaRunnerTests.setUp(self)
        for key in ('OMPI_COMM_WORLD_RANK', 'OMPI_COMM_WORLD_SIZE', 'PMI_RANK', 'PMI_SIZE', 'PMIX_RANK'):
            self.env.pop(key, None)
        probe = '''import json,os,sys
rank=int(os.environ['OMPI_COMM_WORLD_RANK']);size=int(os.environ['OMPI_COMM_WORLD_SIZE'])
assert int(os.environ['OMP_NUM_THREADS'])==int(sys.argv[2])
row={'rank':rank,'mpi_ranks':size,'qmp_nodes':size,'qmp_rank':rank,'global_sum':1024,'local_volume':1024//size,'openmp_threads':int(sys.argv[2]),'mpi_thread_level':3}
with open('mpi-runtime-rank-'+str(rank)+'.json','w') as f:json.dump(row,f)
'''
        compiler = self.home / 'fake compiler'
        self.executable(compiler, 'from pathlib import Path\nimport sys\np=Path(sys.argv[sys.argv.index("-o")+1])\np.write_text('+repr('#!'+sys.executable+'\n'+probe)+')\np.chmod(0o755)\n')
        config = self.chroma_bin / 'chroma-config'
        self.executable(config, 'import sys\nif sys.argv[1]=="--parallel-arch":print("parscalar")\nelif sys.argv[1]=="--cxx":print('+repr(shlex.join([sys.executable,str(compiler)]))+')\nelse:print("")\n')
        self.launcher = self.home / 'mpiexec'
        self.executable(self.launcher, '''import os,subprocess,sys
index=sys.argv.index('-n');size=int(sys.argv[index+1]);command=sys.argv[index+2:]
children=[]
for rank in range(size):
 env=dict(os.environ,OMPI_COMM_WORLD_RANK=str(rank),OMPI_COMM_WORLD_SIZE=str(size))
 children.append(subprocess.Popen(command,env=env))
codes=[child.wait() for child in children]
sys.exit(next((code for code in codes if code),0))
''')
        self.executable(self.chroma_bin / 'chroma', '''import json,os,pathlib,sys,xml.etree.ElementTree as E
source=pathlib.Path(sys.argv[sys.argv.index('-i')+1]);x=E.parse(source)
rank=int(os.environ.get('OMPI_COMM_WORLD_RANK','0'));size=int(os.environ.get('OMPI_COMM_WORLD_SIZE','1'))
assert os.environ['OMP_NUM_THREADS']=='2'
assert source.parent.parent.name=='run_inputs'
real=bool(x.findall('Param/InlineMeasurements/elem'))
if real and rank==1 and os.environ.get('FAIL_RANK'):sys.exit(7)
if rank==0:
 if real:
  assert pathlib.Path(x.findtext('Cfg/cfg_file')).read_bytes()==b'QIO gauge'
  pathlib.Path(x.findtext('.//corr_file')).write_bytes(b'correlators')
 reported=1 if os.environ.get('SINGLE_BINARY') else size
 report=E.Element('chroma');g=E.SubElement(E.SubElement(report,'ProgramInfo'),'Setgeom')
 E.SubElement(g,'logical_size').text=str(reported)+' 1 1 1'
 E.SubElement(g,'subgrid_size').text=str(4//reported)+' 4 4 16'
 E.ElementTree(report).write(sys.argv[sys.argv.index('-o')+1])
 print('CHROMA: ran successfully')
''')

    def mpi_job(self, *extra, env=None):
        return self.run_job('--mpi-ranks','2','--mpiexec',str(self.launcher),'--threads','2',
                            '--timeout','10',*extra,env=env)

    def test_one_driver_launches_each_mpi_stage_with_guarded_ranks(self):
        result = self.mpi_job('--mpi-arg=--bind-to','--mpi-arg=none')
        self.assertEqual(result.returncode,0,result.stderr)
        run = self.home/'result'
        record = json.loads((run/'run.json').read_text())
        self.assertEqual(record['status'],'executables_passed')
        self.assertEqual(record['mpi']['chroma_geometry']['ranks'],2)
        self.assertEqual(len(record['mpi']['runtime_probe']),2)
        self.assertEqual(len(record['mpi']['rank_resources']['gauge-import']),1)
        self.assertEqual([row['rank'] for row in record['mpi']['rank_resources']['chroma']],[0,1])
        for row in record['mpi']['rank_resources']['chroma']:
            self.assertEqual(row['omp_num_threads'],2)
            self.assertEqual(row['status'],'passed')
        self.assertFalse((run/'mpi-layout.xml').exists())
        self.assertTrue((self.repo/'run_inputs/result/mpi-layout.xml').is_file())
        graph = [step for step in record['commands'] if step['stage']=='graph']
        self.assertEqual(len(graph),1)
        self.assertEqual(graph[0]['argv'][0],str(self.redstar/'redstar_corr_graph'))

    def test_stale_single_binary_fails_layout_probe_before_real_job(self):
        result = self.mpi_job(env=dict(self.env,SINGLE_BINARY='1'))
        self.assertNotEqual(result.returncode,0)
        record = json.loads((self.home/'result/run.json').read_text())
        self.assertIn('requested MPI rank count',record['error'])
        self.assertFalse((self.home/'result/gauge.lime').exists())
        self.assertFalse((self.home/'result/chroma.log').exists())

    def test_actual_rank_failure_is_not_hidden_by_primary_output(self):
        result = self.mpi_job(env=dict(self.env,FAIL_RANK='1'))
        self.assertNotEqual(result.returncode,0)
        record = json.loads((self.home/'result/run.json').read_text())
        self.assertEqual(record['status'],'failed')
        rows=record['mpi']['rank_resources']['chroma']
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[1]['returncode'],7)
        self.assertTrue((self.home/'result/output.sdb1').is_file())

    def test_explicit_matching_launcher_is_required(self):
        env=dict(self.env);env.pop('MPIEXEC',None)
        result=self.run_job('--mpi-ranks','2',env=env)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('MPIEXEC',result.stderr)
        self.assertFalse((self.home/'result').exists())

    def test_scalar_configuration_and_nested_driver_are_rejected(self):
        config=self.chroma_bin/'chroma-config'
        self.executable(config,"print('scalar')")
        result=self.mpi_job()
        self.assertNotEqual(result.returncode,0)
        self.assertIn('parscalar',result.stderr)
        env=dict(self.env,OMPI_COMM_WORLD_RANK='0',OMPI_COMM_WORLD_SIZE='2')
        result=self.run_job(env=env)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('outside mpiexec',result.stderr)
        self.assertFalse((self.home/'result').exists())


class RankGuardTests(unittest.TestCase):
    def test_launcher_timeout_allows_rank_guard_to_stop_its_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, OMPI_COMM_WORLD_RANK='0', OMPI_COMM_WORLD_SIZE='1')
            env.pop('PMIX_RANK', None)
            env.pop('PMI_RANK', None)
            command = [sys.executable, str(BASE / 'scripts/run_mpi_rank.py'),
                       '--stage', 'interrupted', '--ranks', '1', '--threads', '2',
                       '--timeout', '30', '--memory-limit-mb', '0',
                       '--contraction-memory-gb', '6', '--', sys.executable,
                       '-c', 'import time;time.sleep(30)']
            with open(os.devnull, 'w') as log:
                with self.assertRaisesRegex(RuntimeError, 'timed out'):
                    run_limited(command, cwd=tmp, env=env, stdout=log,
                                timeout=1, terminate_grace_seconds=1)
            record = json.loads((Path(tmp) / 'resource-interrupted-rank-0.json').read_text())
            self.assertEqual(record['status'], 'failed')
            self.assertIn('interrupted by signal', record['error'])
            with self.assertRaises(ProcessLookupError):
                os.kill(record['child_pid'], 0)

    def test_rank_timeout_kills_actual_child_and_keeps_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ,OMPI_COMM_WORLD_RANK='0',OMPI_COMM_WORLD_SIZE='1')
            env.pop('PMIX_RANK',None);env.pop('PMI_RANK',None)
            result=subprocess.run([sys.executable,str(BASE/'scripts/run_mpi_rank.py'),
                '--stage','timeout','--ranks','1','--threads','2','--timeout','0.1',
                '--memory-limit-mb','0','--contraction-memory-gb','6','--',
                sys.executable,'-c','import time;time.sleep(30)'],cwd=tmp,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,125)
            record=json.loads((Path(tmp)/'resource-timeout-rank-0.json').read_text())
            self.assertEqual(record['status'],'failed')
            self.assertIn('timed out',record['error'])
            with self.assertRaises(ProcessLookupError):os.kill(record['child_pid'],0)
