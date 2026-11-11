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
    resolved = {}
    for name, value in tools.items():
        if (name.startswith('redstar_') and name != 'redstar_bin') or name in ('view_corr_graph', 'extract_ops_util', 'chroma'):
            raise ValueError('Select redstar_bin/chroma_bin directories, not individual Redstar/Chroma executables: ' + name)
        location = Path(value).expanduser()
        if not location.is_absolute():
            raise ValueError('Executable configuration paths must be absolute: ' + name)
        resolved[name] = location
    for family, names in [('redstar', ('redstar_corr_graph', 'redstar_npt', 'view_corr_graph', 'extract_ops_util')),
                          ('chroma', ('chroma',))]:
        bindir = resolved.pop(family + '_bin', None)
        if bindir is not None:
            resolved.update({name: bindir / name for name in names})
    return resolved


def required_tools(family, names, directory=None, configured=None):
    """Select one explicit absolute bin directory; never search PATH or siblings."""
    variable = family.upper() + '_BIN'
    directory = directory or os.environ.get(variable)
    if directory is None and configured and names[0] in configured:
        directory = configured[names[0]].parent
    if not directory:
        raise ValueError('Set ' + variable + ' or --' + family + '-bin to an absolute bin directory')
    directory = Path(directory).expanduser()
    if not directory.is_absolute() or not directory.is_dir():
        raise ValueError(variable + ' must select an existing absolute bin directory: ' + str(directory))
    selected = {name: directory / name for name in names}
    for executable in selected.values():
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ValueError('Missing executable in ' + variable + ': ' + str(executable))
    # Preserve the explicitly selected path even when the executable is a symlink.
    return selected


def prepare_outputs(xml):
    db = xml.find('DBFiles')
    for name, value in [('corr_graph_bin', 'corr_graph.bin'), ('output_db', OUTPUT_DATABASE)]:
        node = db.find(name)
        if node is None:
            node = ET.SubElement(db, name)
        node.text = value


def stage_command(programs, phase, input_path='input.xml'):
    executable, report = STAGES[phase]
    return [programs[executable], input_path, report]


def run_limited(argv, *, cwd, env, stdout, timeout, memory_limit_mb=0, terminate_grace_seconds=0):
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
            if terminate_grace_seconds:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    # Give MPI rank guards time to stop their children and
                    # flush records, even if the launcher exits first.
                    time.sleep(terminate_grace_seconds)
                except ProcessLookupError:
                    pass
            if not terminate_grace_seconds or process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait()
            raise
        return process.returncode
