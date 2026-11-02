#!/usr/bin/env python3
"""Build the native DISCO packer with the selected installed ADAT compiler/ABI."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adat-config',default=os.environ.get('ADAT_CONFIG','adat-config'))
    parser.add_argument('--adat-source',type=Path,help='Optional matching ADAT source tree containing the new DISCO header')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();config=shutil.which(args.adat_config)
    if not config:parser.error('Cannot find adat-config')
    output=args.output.expanduser().absolute()
    if output.exists():parser.error('Output exists; choose a new path')
    flags=lambda option:shlex.split(subprocess.check_output([config,option],text=True))
    source=Path(__file__).resolve().parent/'pack_disco.cc';output.parent.mkdir(parents=True,exist_ok=True)
    headers=[]
    if args.adat_source:
        include=args.adat_source.resolve()/'lib'
        if not (include/'io/disco_superb.h').is_file():parser.error('ADAT source lacks io/disco_superb.h')
        headers=['-I'+str(include)]
    command=flags('--cxx')+headers+flags('--cxxflags')+[str(source),'-o',str(output)]+flags('--ldflags')+flags('--libs')
    print(shlex.join(command),flush=True);subprocess.run(command,check=True)


if __name__=='__main__':main()
