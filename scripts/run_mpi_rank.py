#!/usr/bin/env python3
"""Launch and monitor one actual MPI rank child; all records are run outputs."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def launcher_rank(expected):
    ranks = [int(os.environ[name]) for name in ('OMPI_COMM_WORLD_RANK', 'PMI_RANK', 'PMIX_RANK', 'MV2_COMM_WORLD_RANK') if name in os.environ]
    if not ranks or len(set(ranks)) != 1 or not 0 <= ranks[0] < expected:
        raise ValueError('Missing, conflicting or out-of-range MPI rank environment')
    sizes = [int(os.environ[name]) for name in ('OMPI_COMM_WORLD_SIZE', 'PMI_SIZE', 'MV2_COMM_WORLD_SIZE') if name in os.environ]
    if any(size != expected for size in sizes):
        raise ValueError('Launcher world size differs from --ranks')
    return ranks[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True)
    parser.add_argument('--ranks', type=int, required=True)
    parser.add_argument('--threads', type=int, required=True)
    parser.add_argument('--timeout', type=float, required=True)
    parser.add_argument('--memory-limit-mb', type=int, required=True)
    parser.add_argument('--contraction-memory-gb', type=int, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or min(args.ranks, args.threads, args.timeout, args.contraction_memory_gb) <= 0 or args.memory_limit_mb < 0:
        parser.error('A command and valid positive limits are required')
    if not args.stage.replace('-', '').isalnum():
        parser.error('Invalid stage name')
    try:
        rank = launcher_rank(args.ranks)
    except ValueError as error:
        parser.error(str(error))
    env = dict(os.environ, OMP_NUM_THREADS=str(args.threads), OMP_DYNAMIC='FALSE',
               OMP_MAX_ACTIVE_LEVELS='1', VECLIB_MAXIMUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               REDSTAR_SB_MEM_GB=str(args.contraction_memory_gb))
    path = Path('resource-{}-rank-{}.json'.format(args.stage, rank))
    record = {'rank': rank, 'ranks': args.ranks, 'stage': args.stage, 'command': command,
              'cwd': str(Path.cwd()), 'omp_num_threads': args.threads,
              'memory_limit_mb': args.memory_limit_mb, 'timeout': args.timeout,
              'rss_samples': 0, 'peak_rss_kib': 0, 'status': 'running'}
    process = None
    start = time.monotonic()

    def save():
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, indent=2) + '\n')
        temporary.replace(path)

    def interrupt(signum, frame):
        raise RuntimeError('MPI rank interrupted by signal ' + str(signum))

    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    save()
    try:
        process = subprocess.Popen(command, env=env, start_new_session=True)
        record['child_pid'] = process.pid
        save()
        while process.poll() is None:
            if time.monotonic() - start >= args.timeout:
                raise RuntimeError('MPI rank timed out after {} seconds'.format(args.timeout))
            if args.memory_limit_mb:
                response = subprocess.run(['ps', '-o', 'rss=', '-p', str(process.pid)], capture_output=True, text=True)
                rss = response.stdout.strip()
                if rss:
                    rss = int(rss)
                    record['rss_samples'] += 1
                    record['peak_rss_kib'] = max(record['peak_rss_kib'], rss)
                    if rss > args.memory_limit_mb * 1024:
                        raise RuntimeError('MPI rank exceeded {} MiB RSS'.format(args.memory_limit_mb))
                elif process.poll() is None:
                    raise RuntimeError('Cannot monitor actual rank RSS: ' + response.stderr.strip())
            time.sleep(0.2)
        record.update(returncode=process.returncode, status='passed' if process.returncode == 0 else 'failed')
    except BaseException as error:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        record.update(status='failed', returncode=125, error=str(error))
    record['seconds'] = time.monotonic() - start
    save()
    if record.get('error'):
        print('MPI rank {}: {}'.format(rank, record['error']), file=sys.stderr)
    status = record['returncode']
    return status if status >= 0 else 128 - status


if __name__ == '__main__':
    raise SystemExit(main())
