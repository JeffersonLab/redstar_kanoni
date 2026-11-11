#!/usr/bin/env python3
"""Compile the QDP/QMP/MPI runtime probe using the selected Chroma configuration."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chroma-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.expanduser().absolute()
    if output.exists():
        parser.error('Output exists; choose a fresh path')
    config = args.chroma_config.expanduser().absolute()
    prefix = [str(config)] if os.access(config, os.X_OK) else ['sh', str(config)]
    flags = lambda option: shlex.split(subprocess.check_output(prefix + [option], text=True))
    source = Path(__file__).resolve().parent / 'chroma_mpi_probe.cc'
    command = flags('--cxx') + flags('--cxxflags') + ['-std=c++20', str(source), '-o', str(output)]
    command += flags('--ldflags') + flags('--libs')
    output.parent.mkdir(parents=True, exist_ok=True)
    Path(str(output) + '.build-command.json').write_text(json.dumps(command, indent=2) + '\n')
    subprocess.run(command, check=True)


if __name__ == '__main__':
    main()
