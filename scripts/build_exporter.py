#!/usr/bin/env python3
"""Build the safe correlator exporter with the selected installed ADAT compiler/ABI."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adat-config',default=os.environ.get('ADAT_CONFIG','adat-config'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();config=shutil.which(args.adat_config)
    if not config:parser.error('Cannot find adat-config')
    output=args.output.expanduser().absolute()
    if output.exists():parser.error('Output exists; choose a new path')
    flags=lambda option:shlex.split(subprocess.check_output([config,option],text=True))
    source=Path(__file__).resolve().parent/'export_correlators.cc';output.parent.mkdir(parents=True,exist_ok=True)
    command=flags('--cxx')+flags('--cxxflags')+[str(source),'-o',str(output)]+flags('--ldflags')+['-ldbutil']+flags('--libs')
    print(shlex.join(command),flush=True);subprocess.run(command,check=True)


if __name__=='__main__':main()
