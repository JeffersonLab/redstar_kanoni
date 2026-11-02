#!/usr/bin/env python3
"""Copy the checksum-pinned MOD dataset into a real Kanoni data directory."""
import argparse,hashlib,json,shutil
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-dir',type=Path,required=True)
p.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[1]/'data')
a=p.parse_args();root=Path(__file__).resolve().parents[1]
if a.data_dir.is_symlink():p.error('Data directory must not be a symlink')
manifest=json.loads((root/'test_inputs/mod-manifest.json').read_text())
# Validate every source and destination before writing any payload.
files=[]
for entry in manifest['files']:
 source=a.source_dir/entry['name'];dest=a.data_dir/entry['name']
 for path in [source]+([dest] if dest.exists() or dest.is_symlink() else []):
  if path.is_symlink() or not path.is_file() or path.stat().st_size!=entry['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:p.error('Missing/mismatched regular MOD file: '+str(path))
 files.append((source,dest))
a.data_dir.mkdir(parents=True,exist_ok=True)
for source,dest in files:
 if not dest.exists():shutil.copyfile(source,dest)
 dest.chmod(0o444)
 print('Verified:',dest)
