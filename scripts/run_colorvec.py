#!/usr/bin/env python3
"""Run a Kanoni demo in a fresh output directory."""
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    if len(sys.argv) != 2:
        sys.exit('Usage: run_colorvec.csh <redstar XML input file>')
    supplied = Path(sys.argv[1]).expanduser()
    candidates = [supplied, root / supplied, root / 'test_inputs' / supplied]
    source = next((p.resolve() for p in candidates if p.is_file()), None)
    if source is None:
        sys.exit('Redstar input file does not exist: ' + str(supplied))
    names = ('redstar_corr_graph', 'redstar_npt')
    bindir = os.environ.get('REDSTAR_BIN')
    if bindir:
        programs = [str(Path(bindir).expanduser() / name) for name in names]
    else:
        programs = [shutil.which(name) for name in names]
        if not all(programs):
            sibling = root.parent / 'redstar.devel/build/src'
            programs = [str(sibling / name) for name in names]
    if not all(p and Path(p).is_file() and os.access(p, os.X_OK) for p in programs):
        sys.exit('Cannot find redstar_corr_graph and redstar_npt. Add their directory to PATH or set REDSTAR_BIN to its build/src or install/bin directory.')
    # Resolve before changing the subprocess working directory.
    programs = [str(Path(p).resolve()) for p in programs]
    if not (root / 'test_inputs/data').is_dir():
        subprocess.run([str(root / 'setup-data')], check=True)
    runs = root / 'runs'
    runs.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=source.stem + '-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-', dir=str(runs)))
    # Copy small inputs so programs cannot overwrite the checked-out originals.
    for item in (root / 'test_inputs').iterdir():
        if item.name == 'data' or item.name == 'data-manifest.json':
            continue
        target = run / item.name
        if item.is_dir():
            shutil.copytree(str(item), str(target))
        elif item.is_file():
            shutil.copyfile(str(item), str(target))
    shutil.copyfile(str(source), str(run / source.name))
    # Include local support inputs for personal demos without importing old outputs.
    for item in source.parent.iterdir():
        target = run / item.name
        if not target.exists() and item.is_file() and item.suffix in ('.list', '.dat'):
            shutil.copyfile(str(item), str(target))
    for database in (root / 'test_inputs/data').glob('*.sdb'):
        (run / database.name).symlink_to(database.resolve())
    print('Run directory: ' + str(run), flush=True)
    for program, suffix in zip(programs, ('corr.out', 'out')):
        log = run / (source.stem + '.' + suffix)
        with log.open('wb') as stream:
            result = subprocess.run([program, source.name, 'out.xml'], cwd=str(run), stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            sys.exit('{} failed ({}); see {}'.format(Path(program).name, result.returncode, log))
    print('Completed: ' + str(run))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit('run_colorvec: ' + str(error))
