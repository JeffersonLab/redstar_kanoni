# redstar_kanoni

Canonical Redstar demos and a sandbox for new tests.

## Quick start

```sh
./setup-data
./run_colorvec.csh pion.xml
# Equivalent: ./run_colorvec.csh test_inputs/pion.xml
```

`setup-data` reuses the shared, checksum-verified dataset at
`~/QCD/test_data/kanoni/v1`. All branches and copies on this machine can use the
same files. Set `KANONI_DATA_DIR` or pass `--data-dir` to choose another location.

On a machine with the original SDBs already available:

```sh
./setup-data --source-dir ~/Downloads --adopt
```

`--adopt` moves the verified files into shared storage and leaves symlinks at
the original paths. Existing demos and other Kanoni checkouts keep working.
Without `--adopt`, import copies the source files and leaves the source untouched.
Existing files with different checksums are never replaced. Source databases in
the cache are made read-only. A symlink protects against ordinary `rm *.sdb` in a
run directory; it does not protect against programs opening the target for writing
or commands that explicitly traverse links.

## Build selection

Put `redstar_corr_graph` and `redstar_npt` on `PATH`, or set their directory once:

```sh
# sh, bash, zsh
export REDSTAR_BIN=/path/to/redstar/install/bin
# tcsh
setenv REDSTAR_BIN /path/to/redstar/build/src
```

No script editing is needed. With no override, the runner also recognizes the
legacy sibling checkout `../redstar.devel/build/src`.

## Layout and outputs

- `test_inputs/`: tracked XML inputs, operator lists, and weights.
- `test_inputs/data-manifest.json`: dataset sizes and SHA-256 checksums.
- `test_inputs/data`: local, Git-ignored symlink to shared SDB storage.
- `runs/<demo>-<timestamp>-<unique>/`: isolated logs, XML output, and `.sdb1` results.
- Root input names remain compatibility symlinks, so old demo commands still work.
- Root `.sdb` links route through `test_inputs/data`; large data is outside Git.

Each new run copies the small inputs and weights and links the read-only SDBs.
Existing outputs and personal demo files are left in place. Cleanup belongs in
`runs/`; deleting a run does not delete the shared input databases. Personal XML
inputs can also be passed by absolute or relative path. Put their supporting XML
and directory trees in `test_inputs/`, keeping the paths used by the XML intact;
local `.dat` and `.list` files beside the selected input are included automatically.

Redstar and matelem_fitter demos may use the shared dataset through
`KANONI_DATA_DIR` or this checkout's `test_inputs/data` path. Their repositories
are not modified by setup.

## Download distribution

This repository and its SDB release assets are public. Cloning over HTTPS and
running `./setup-data` require no GitHub account, token, GitHub CLI, or login.
Python 3 is required; the demo runner also needs tcsh and a Redstar build.

The versioned [kanoni-data-v1 release](https://github.com/JeffersonLab/redstar_kanoni/releases/tag/kanoni-data-v1)
contains all 18 SDB files, the dataset manifest, and SHA-256 checksums. A fresh
clone downloads any missing data automatically:

```sh
git clone --branch devel https://github.com/JeffersonLab/redstar_kanoni.git
cd redstar_kanoni
./setup-data
./run_colorvec.csh pion.xml
```

Git stores the small inputs and manifest, not the large SDBs or LFS pointers.
The default download URL is pinned in `test_inputs/data-manifest.json`, so copies
and branches reuse the same dataset version. Existing verified shared files are
reused without downloading them again. Setup downloads public release assets
directly over HTTPS. An authenticated GitHub CLI fallback remains available for
private mirrors; it is not needed for the default public dataset.
`--base-url` or `KANONI_DATA_URL` can select
a mirror. `--source-dir` can import existing local data instead of downloading it.

Downloads are checked against the manifest before installation; a missing file,
LFS pointer, or mismatched checksum produces an error, not a silent replacement.
Dataset versions are immutable: publish a new release and manifest/version for
changed inputs instead of replacing existing assets.

## Cleanup

Each new run writes under `runs/`; remove an unwanted run directory to discard
its output without touching the shared inputs. `interior_nodes.*.log` files are
intermediate Redstar diagnostic output and are ignored by Git. Older saved outputs
from the checkout root have been preserved locally under `runs/legacy-*`.

Run the setup/runner regression tests with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```
