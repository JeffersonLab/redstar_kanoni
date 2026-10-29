#!/usr/bin/env python3
"""Install verified regular Kanoni SDB files in data/ without creating symlinks."""
import argparse
import hashlib
import http.client
import time
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess
import urllib.error
import urllib.parse
import tempfile
import urllib.request


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verified(path, entry):
    return path.is_file() and path.stat().st_size == entry['bytes'] and digest(path) == entry['sha256']


def retire_legacy_aliases(root, entries):
    aliases = []
    for entry in entries:
        path = root / entry['name']
        if path.is_symlink():
            if path.exists() and not verified(path, entry):
                raise RuntimeError('Legacy SDB alias refers to different data; preserved: ' + str(path))
            aliases.append(path)
    directory = root / 'test_inputs/data'
    if directory.is_symlink():
        if directory.exists() and not all(verified(directory / e['name'], e) for e in entries):
            raise RuntimeError('Legacy data alias refers to different data; preserved: ' + str(directory))
        aliases.append(directory)
    for path in aliases:
        path.unlink()


def download_once(url, destination):
    try:
        with urllib.request.urlopen(url, timeout=120) as response, destination.open('wb') as out:
            shutil.copyfileobj(response, out)
        return
    except urllib.error.HTTPError as error:
        parsed = urllib.parse.urlsplit(url)
        parts = parsed.path.strip('/').split('/')
        if error.code not in (403, 404) or parsed.hostname != 'github.com' or len(parts) != 6 or parts[2:4] != ['releases', 'download']:
            raise
    gh = shutil.which('gh')
    if not gh:
        raise RuntimeError('Private GitHub release downloads require GitHub CLI: install gh, run gh auth login, then retry setup-data; or use --source-dir.')
    result = subprocess.run([gh, 'release', 'download', urllib.parse.unquote(parts[4]),
        '--repo', '/'.join(parts[:2]), '--pattern', urllib.parse.unquote(parts[5]),
        '--output', str(destination), '--clobber'], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Authenticated release download failed; run gh auth login and check repository access. ' + result.stderr.strip())


def download(url, destination):
    # Large release assets can be interrupted in transit. Retrying starts only
    # this temporary file again; previously verified databases are left intact.
    for attempt in range(3):
        try:
            download_once(url, destination)
            return
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead, http.client.RemoteDisconnected) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code not in (408, 429, 500, 502, 503, 504):
                raise
            if attempt == 2:
                raise
            print('Download interrupted; retrying {} ({}/3)'.format(destination.name, attempt + 2), flush=True)
            time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, help='copy existing verified SDBs instead of downloading')
    parser.add_argument('--data-dir', type=Path, help='real destination directory (default: KANONI_DATA_DIR or checkout data/)')
    parser.add_argument('--base-url', help='HTTPS release-asset directory (or KANONI_DATA_URL)')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'test_inputs/data-manifest.json').read_text())
    data = (args.data_dir or Path(os.environ.get('KANONI_DATA_DIR', str(root / 'data')))).expanduser().absolute()
    source = args.source_dir.expanduser().absolute() if args.source_dir else None
    base = args.base_url or os.environ.get('KANONI_DATA_URL') or manifest.get('base_url')
    if base and not base.startswith('https://'):
        raise RuntimeError('Downloads require an HTTPS base URL')
    if data.is_symlink() or (data.exists() and not data.is_dir()):
        raise RuntimeError('Data directory must be a real directory, not a symlink: ' + str(data))
    # Validate all available inputs before installing anything. Imports are copies;
    # never move source files or manufacture compatibility links.
    for entry in manifest['files']:
        name = entry['name']
        if Path(name).name != name or not name.endswith('.sdb'):
            raise RuntimeError('Invalid manifest filename: ' + name)
        dst = data / name
        src = source / name if source else None
        if dst.exists() or dst.is_symlink():
            if dst.is_symlink() or not verified(dst, entry):
                raise RuntimeError('Destination differs from manifest or is a symlink: ' + str(dst))
        elif src is not None and src.exists():
            if not verified(src, entry):
                raise RuntimeError('Source data differs from manifest: ' + str(src))
        elif not base:
            raise RuntimeError('Missing ' + name + '; supply --source-dir or --base-url.')
    data.mkdir(parents=True, exist_ok=True)
    for entry in manifest['files']:
        dst = data / entry['name']
        src = source / entry['name'] if source else None
        if not dst.exists():
            fd, filename = tempfile.mkstemp(prefix='.' + entry['name'], dir=str(data))
            os.close(fd)
            temp = Path(filename)
            try:
                if src is not None and src.exists():
                    shutil.copyfile(str(src), str(temp))
                else:
                    download(base.rstrip('/') + '/' + entry['name'], temp)
                if not verified(temp, entry):
                    raise RuntimeError('Checksum mismatch: ' + entry['name'])
                temp.replace(dst)
            finally:
                if temp.exists():
                    temp.unlink()
        dst.chmod(0o444)
    retire_legacy_aliases(root, manifest['files'])
    print('Verified {} regular SDB files in {}'.format(len(manifest['files']), data))
    print('Ready: ' + str(data))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        sys.exit('setup-data: ' + str(error))
