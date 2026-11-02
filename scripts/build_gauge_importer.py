#!/usr/bin/env python3
"""Build the read-only MOD gauge importer with a configured Chroma/QDP stack."""
import argparse,json,os,shlex,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--chroma-config',type=Path,required=True)
p.add_argument('--source-dir',type=Path,help='Chroma source checkout for an uninstalled build')
p.add_argument('--library-dir',type=Path,help='Chroma archive directory for an uninstalled build')
p.add_argument('--adat-config',type=Path,help='matching ADAT installation if its libraries are required')
p.add_argument('--extra-libs',default='',help='extra linker flags omitted by an older chroma-config')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();out=a.output.absolute()
if out.exists():p.error('Output exists; choose a fresh filename')
config=a.chroma_config.resolve();prefix=[str(config)] if os.access(config,os.X_OK) else ['sh',str(config)]
def flags(option):return shlex.split(subprocess.check_output(prefix+[option],text=True))
command=flags('--cxx')
if a.source_dir:command+=['-I'+str(a.source_dir.resolve()/'lib')]
command+=flags('--cxxflags')+['-std=c++20',str(Path(__file__).resolve().parent/'mod_gauge_to_qio.cc'),'-o',str(out)]
if a.library_dir:command+=['-L'+str(a.library_dir.resolve())]
command+=flags('--ldflags')
if a.adat_config:
 ac=str(a.adat_config.resolve());command+=shlex.split(subprocess.check_output([ac,'--ldflags'],text=True))
command+=flags('--libs')
if a.adat_config:command+=shlex.split(subprocess.check_output([ac,'--libs'],text=True))
command+=shlex.split(a.extra_libs)
out.parent.mkdir(parents=True,exist_ok=True)
Path(str(out)+'.build-command.json').write_text(json.dumps(command,indent=2)+'\n')
print(shlex.join(command),flush=True);subprocess.run(command,check=True)
