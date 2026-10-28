#!/usr/bin/env python3
"""Install a verified, shared Kanoni dataset without overwriting different data."""
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


def link(path, target):
    if path.is_symlink():
        if path.resolve() == target.resolve():
            return
        raise RuntimeError('Refusing to replace existing link: ' + str(path))
    if path.exists():
        raise RuntimeError('Refusing to replace existing path: ' + str(path))
    path.symlink_to(target)


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
    parser.add_argument('--source-dir', type=Path, help='directory containing the original SDBs')
    parser.add_argument('--data-dir', type=Path, help='shared dataset directory (or KANONI_DATA_DIR)')
    parser.add_argument('--base-url', help='HTTPS release-asset directory (or KANONI_DATA_URL)')
    parser.add_argument('--adopt', action='store_true', help='move source files into shared storage and leave compatibility links')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'test_inputs/data-manifest.json').read_text())
    cache = (args.data_dir or Path(os.environ.get('KANONI_DATA_DIR', str(Path.home() / 'QCD/test_data/kanoni/v1')))).expanduser().absolute()
    source = (args.source_dir or Path.home() / 'Downloads').expanduser().absolute()
    base = args.base_url or os.environ.get('KANONI_DATA_URL') or manifest.get('base_url')
    if base and not base.startswith('https://'):
        raise RuntimeError('Downloads require an HTTPS base URL')
    # Validate every available file before changing anything.
    for entry in manifest['files']:
        name = entry['name']
        if Path(name).name != name or not name.endswith('.sdb'):
            raise RuntimeError('Invalid manifest filename: ' + name)
        dst, src = cache / name, source / name
        if dst.exists() or dst.is_symlink():
            if dst.is_symlink() or not verified(dst, entry):
                raise RuntimeError('Shared data differs from manifest: ' + str(dst))
        elif src.exists():
            if not verified(src, entry):
                raise RuntimeError('Source data differs from manifest: ' + str(src))
        elif not base:
            raise RuntimeError('Missing ' + name + '; supply --source-dir or --base-url.')
        if args.adopt and src.exists() and not verified(src, entry):
            raise RuntimeError('Refusing to adopt different source data: ' + str(src))
    data_link = root / 'test_inputs/data'
    if data_link.exists() or data_link.is_symlink():
        if not data_link.is_symlink() or data_link.resolve() != cache.resolve():
            raise RuntimeError('Existing test_inputs/data points elsewhere; leave it intact or choose its dataset with --data-dir')
    cache.mkdir(parents=True, exist_ok=True)
    for entry in manifest['files']:
        dst, src = cache / entry['name'], source / entry['name']
        if not dst.exists():
            if src.exists() and args.adopt:
                # Resolve legacy links: move the actual file, then restore its old name.
                original = src.resolve()
                shutil.move(str(original), str(dst))
                original.symlink_to(dst)
            else:
                fd, filename = tempfile.mkstemp(prefix='.' + entry['name'], dir=str(cache))
                os.close(fd)
                temp = Path(filename)
                try:
                    if src.exists():
                        shutil.copyfile(str(src), str(temp))
                    else:
                        download(base.rstrip('/') + '/' + entry['name'], temp)
                    if not verified(temp, entry):
                        raise RuntimeError('Checksum mismatch: ' + entry['name'])
                    temp.replace(dst)
                finally:
                    if temp.exists():
                        temp.unlink()
        if args.adopt and src != dst and src.exists() and not src.is_symlink():
            # A verified duplicate from an earlier import can become a link too.
            src.unlink()
            src.symlink_to(dst)
        if args.adopt and not src.exists() and not src.is_symlink():
            src.symlink_to(dst)
        dst.chmod(0o444)
    link(data_link, cache)
    print('Verified {} SDB files in {}'.format(len(manifest['files']), cache))
    print('Ready: ' + str(data_link))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        sys.exit('setup-data: ' + str(error))
