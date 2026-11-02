"""Shared development-run conventions for graph and numerical executables."""
from pathlib import Path
import os
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

OUTPUT_DATABASE = 'output.sdb1'
STAGES = {'graph': ('redstar_corr_graph', 'graph.out.xml'),
          'numerical': ('redstar_npt', 'npt.out.xml')}


def load_toml(path):
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            raise RuntimeError('TOML configuration needs Python 3.11+ or the tomli package')
    with Path(path).open('rb') as stream:
        return tomllib.load(stream)


def configured_tools(path):
    config = Path(path).expanduser().absolute()
    tools = load_toml(config)['executables']
    resolved = {name: (config.parent / Path(value).expanduser()).absolute()
                for name, value in tools.items()}
    bindir = resolved.pop('redstar_bin', None)
    if bindir is not None:
        for name in ('redstar_corr_graph', 'redstar_npt', 'view_corr_graph', 'extract_ops_util'):
            resolved.setdefault(name, bindir/name)
    return resolved


def prepare_outputs(xml):
    db = xml.find('DBFiles')
    for name, value in [('corr_graph_bin', 'corr_graph.bin'), ('output_db', OUTPUT_DATABASE)]:
        node = db.find(name)
        if node is None:
            node = ET.SubElement(db, name)
        node.text = value


def stage_command(programs, phase):
    executable, report = STAGES[phase]
    return [programs[executable], 'input.xml', report]


def run_limited(argv, *, cwd, env, stdout, timeout, memory_limit_mb=0):
    """Bound real-tool attempts; terminate the process group on failure/timeout."""
    start = time.monotonic()
    with subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout,
                          stderr=subprocess.STDOUT, start_new_session=True) as process:
        try:
            while process.poll() is None:
                if time.monotonic() - start >= timeout:
                    raise RuntimeError('timed out after {} seconds'.format(timeout))
                if memory_limit_mb:
                    rss = subprocess.run(['ps', '-o', 'rss=', '-p', str(process.pid)],
                                         capture_output=True, text=True, check=False).stdout.strip()
                    if rss and int(rss) > memory_limit_mb * 1024:
                        raise RuntimeError('memory limit exceeded ({} MiB; observed {} KiB RSS)'.format(memory_limit_mb, rss))
                time.sleep(0.2)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise
        return process.returncode
