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
./setup-data --source-dir /path/to/existing-sdbs
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

Build Redstar with OpenMP using its
[clean-build guide](https://github.com/JeffersonLab/redstar/blob/devel/docs/build.md)
and one-command script. Linux uses GCC/libgomp and chromaform/OpenBLAS; macOS uses
Apple Clang/libomp and Accelerate. Use matching Redstar and ADAT installations.

No script editing is needed. With no override, the runner also recognizes the
legacy sibling checkout `../redstar.devel/build/src`.

## Layout and outputs

- `test_inputs/`: tracked XML inputs, operator lists, and weights.
- `test_inputs/data-manifest.json`: dataset sizes and SHA-256 checksums.
- `test_inputs/data`: local, Git-ignored symlink to shared SDB storage.
- `runs/<demo>-<timestamp>-<unique>/`: isolated logs, XML output, and `.sdb1` results.
- Root input names remain compatibility symlinks, so old demo commands still work.
- Root `.sdb` links route through `test_inputs/data`; large data is outside Git.

Each new run copies the small inputs and weights, links read-only SDBs through
the selected home, and writes a prepared `input.xml` with concrete database paths.
It saves `graph.log`, `npt.log`, separate XML reports and `run.json`. Default
OpenMP settings request four workers and disable dynamic teams; `--threads`
overrides this. The installed Redstar build must itself have OpenMP enabled.
Large diagnostic dumps are disabled unless `--keep-diagnostics` is supplied.

`run_redstar.csh` now invokes this same precomputed-SDB workflow. The historical
HAROM database-production launcher is archived in [legacy](legacy/README.md).
Existing outputs and personal demo files are left in place. Cleanup belongs in
`runs/`; deleting a run does not delete the shared input databases. Personal XML
inputs can also be passed by absolute or relative path. Put their supporting XML
and directory trees in `test_inputs/`, keeping the paths used by the XML intact;
local `.dat` and `.list` files beside the selected input are included automatically.

After setup, use this checkout as the stable database home for Redstar generators:

```sh
export KANONI_DATA_DIR="$PWD/test_inputs/data"
```

The Kanoni runner uses that variable too:

```sh
python3 scripts/run_colorvec.py pion.xml --threads 4
# Explicit paths win over the environment:
python3 scripts/run_colorvec.py pion.xml --database-dir /path/to/verified-sdbs
```

Current Redstar input generators accept that variable; `--database-dir` overrides
it. They write concrete paths into generated XML. The top-level Downloads SDB
aliases are no longer required. Historical run records keep their original paths.
The fitter's bundled 135-key `rho.single.sdb` is a derived correlator fixture and
remains self-contained; these raw SDBs are used for contraction regeneration.

## Download distribution

This repository and its SDB release assets are public. Cloning over HTTPS and
running `./setup-data` require no GitHub account, token, GitHub CLI, or login.
Python 3.9 or newer is required; the compatibility launchers also need tcsh.
The Python runner can be invoked directly without tcsh.

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
Transient network interruptions are retried up to three times per asset. If a
transfer still fails, rerun `./setup-data`; verified files are reused.
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

## Current input schemas and validation

The 39 `RedstarNPt` inputs in `test_inputs` now use v14, SUNClass keys,
root-level NPoint lists and explicit CG controls. Projected weights used at
runtime live under `weights/v4`; historical v3 weights are retained. The six
`GenerateXML` inputs and two `OpsList` maps have separate schemas and do not
receive a Redstar v14 tag.

See [VALIDATION.md](VALIDATION.md) and
[test_inputs/validation-reference.json](test_inputs/validation-reference.json)
for observed coverage and the exact limitations. Two genprop cases require
additional data; the eta case is an exact symmetry-zero control. The full
121-correlator a1 graph attempt was stopped after reaching about 37 GB memory
footprint on the 32 GiB test Mac and remains unvalidated. The two inputs
that originally selected fake data retain that mode and are labelled separately.
A full-suite command returns nonzero if any requested case fails.

`scripts/migrate_inputs.py` defaults to a dry run. `--write` saves originals and
reports under a fresh `runs/input-migration-*`. It uses the installed converter
for typed SUN-to-SUNClass operators and projected-name factory aliases. Optional
compatibility changes are explicit:

```sh
# Unsupported fixed-CG mode requires current automatic CGs:
python3 scripts/migrate_inputs.py --write --enable-auto-cg
# These are deliberate, recorded repairs, applied only to named inputs:
python3 scripts/migrate_inputs.py --write --repair-rest-pairs test_inputs/a1.000_T1pM.xml
python3 scripts/migrate_inputs.py --write --enable-target-rotation test_inputs/kpi_3pt.xml
python3 scripts/migrate_inputs.py --write --fsq-database gpdf.more.sdb test_inputs/ff_3pt.xml
```

These conversions are already applied; structural conversion alone does not
establish numerical correctness. For independent validation use one matching
installation:

```sh
export REDSTAR_BIN=/path/to/redstar/bin
export DBUTIL=/path/to/adat/bin/dbutil
python3 scripts/validate_inputs.py --threads 4 --timeout 600
```

Specific input filenames can follow the options to rerun only selected cases.
Each validation suite creates a fresh directory under runs and writes results.json
after every case. It checks graph/assembly/key counts, all numerical readback
values, one-configuration/time dimensions, extracted operator definitions and
manifest-pinned raw database checksums. ADAT `dbutil` cannot export some long
multi-hadron filenames on this filesystem. In that case the validator builds
`scripts/export_correlators.cc` with the matching `adat-config`, exports numbered
files and checks every full key against independent `dbutil keysxml` output.
Set `ADAT_CONFIG`, pass `--adat-config`, or supply a matching `--exporter` if ADAT's
config tool is not beside dbutil. Keep compilers and OpenMP runtimes consistent.
Diagnostic verbosity and large graph/DAG dumps are disabled in the staged copy;
tracked input physics settings remain intact. Fake-data runs and zero channels
are reported explicitly. A failed or incomplete case is not a passing regression.

See AGENTS.md for source/dataset conventions and staged reference-work hygiene.
The pre-existing derivative-vertex audit and test_vertices inventories are
separate reference work; they are preserved independently of these migrations.
