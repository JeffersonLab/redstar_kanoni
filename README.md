# redstar_kanoni

Canonical Redstar demos and a sandbox for new tests.

## Quick start

```sh
./setup-data
./run_colorvec.csh test_inputs/pion.xml
```

`setup-data` installs the 18 checksum-verified SDBs as real files in this
checkout's `data/` directory (about 1 GB). The directory and payloads are ignored
by Git; no SDB or data-directory symlinks are needed. Repeating setup reuses
verified files and downloads only missing ones.

To import an existing dataset instead of downloading it:

```sh
./setup-data --source-dir /path/to/existing-sdbs
```

Imports copy the verified bytes without moving the source SDB files. Dataset files
are made read-only. `--data-dir` or `KANONI_DATA_DIR` selects another real data
directory; explicit options take precedence. Symlink destination directories and
symlink SDB files are rejected. The old `--adopt` mode has been removed.

When upgrading an older checkout, unset an obsolete `KANONI_DATA_DIR` setting or
point it at the new `data/` directory. For a one-time local import you can use:

```sh
./setup-data --source-dir /path/to/old-dataset --data-dir data
```

After installation, setup removes verified top-level SDB compatibility links and
the old `test_inputs/data` directory link. Links to different data are preserved
and reported for review. The actual source files are not removed.

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
- `data/`: the actual read-only SDB files, downloaded or imported locally; Git-ignored.
- `runs/<demo>-<timestamp>-<unique>/`: isolated logs, XML output, and `.sdb1` results.
- XML demos live directly in `test_inputs/`; the top-level XML aliases have been removed.

Each new run copies the small inputs and weights and writes a prepared `input.xml`
with relative paths to the actual SDB files. A normal run under `runs/<name>/`
uses paths such as `../../data/prop.sdb`; no per-run SDB links or copies are made.
Tracked numerical templates use `../data/<file>.sdb`, relative to `test_inputs/`.
The runners rebase those paths for their fresh working directories, since Redstar
resolves XML paths from the process working directory.
It saves `graph.log`, `npt.log`, separate XML reports and `run.json`. Default
OpenMP settings request four workers and disable dynamic teams; `--threads`
overrides this. The installed Redstar build must itself have OpenMP enabled.
Large diagnostic dumps are disabled unless `--keep-diagnostics` is supplied.

Existing outputs and personal demo files are left in place. Cleanup belongs in
`runs/`; deleting a run does not delete the actual files in `data/`. Personal XML
inputs can also be passed by absolute or relative path. Put their supporting XML
and directory trees in `test_inputs/`, keeping the paths used by the XML intact;
local `.dat` and `.list` files beside the selected input are included automatically.
Input paths resolve from the current directory, with no basename lookup or XML
compatibility aliases. From the checkout root use `test_inputs/pipi_i1.xml`, for
example:

```sh
./run_colorvec.csh test_inputs/pipi_i1.xml
```

When invoking the runner from another directory, pass the full input path, such
as `/path/to/redstar_kanoni/test_inputs/pipi_i1.xml`.

After setup, use this checkout as the stable database home for Redstar generators:

```sh
export KANONI_DATA_DIR="$PWD/data"
```

The Kanoni runner uses that variable too:

```sh
python3 scripts/run_colorvec.py test_inputs/pion.xml --threads 4
# Explicit paths win over the environment:
python3 scripts/run_colorvec.py test_inputs/pion.xml --database-dir /path/to/verified-sdbs
```

Redstar input generators accept that variable; `--database-dir` overrides it.
Kanoni runners generate relative database paths even for an alternate real data
directory. External Redstar helpers expand their selected data home when preparing
inputs. Historical run records keep their original paths; replay an old numerical
input through the current runner into a fresh directory to use the new layout.
The fitter's bundled 135-key `rho.single.sdb` is a derived correlator fixture and
remains self-contained; these raw SDBs are used for contraction regeneration.

## Download distribution

This repository and its SDB release assets are public. Cloning over HTTPS and
running `./setup-data` require no GitHub account, token, GitHub CLI, or login.
Python 3.9 or newer is required; the shell launchers also need tcsh.
The Python runner can be invoked directly without tcsh.

The versioned [kanoni-data-v1 release](https://github.com/JeffersonLab/redstar_kanoni/releases/tag/kanoni-data-v1)
contains all 18 SDB files, the dataset manifest, and SHA-256 checksums. A fresh
clone downloads any missing data automatically:

```sh
git clone --branch devel https://github.com/JeffersonLab/redstar_kanoni.git
cd redstar_kanoni
./setup-data
./run_colorvec.csh test_inputs/pion.xml
```

Git stores the small inputs and manifest, not the large SDBs or LFS pointers.
The default download URL is pinned in `test_inputs/data-manifest.json`, so copies
and branches reuse the same dataset version. Existing verified files in `data/` are
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
its output without touching the dataset in `data/`. `interior_nodes.*.log` files are
intermediate Redstar diagnostic output and are ignored by Git. Older saved outputs
from the checkout root have been preserved locally under `runs/legacy-*`.

Run the setup and runner regression tests with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

## Current input schemas and validation

The 39 `RedstarNPt` inputs in `test_inputs` use relative `../data/` database paths,
v14 and SUNClass keys,
root-level NPoint lists and explicit CG controls. Projected weights used at
runtime live under `weights/v4`; historical v3 weights are retained. The six
`GenerateXML` inputs and two `OpsList` maps have separate schemas and do not
receive a Redstar v14 tag.

See [VALIDATION.md](VALIDATION.md) and
[test_inputs/validation-reference.json](test_inputs/validation-reference.json)
for the original observed coverage and exact limitations. The later data-layout
migration and fresh relative-path checks are recorded in
[test_inputs/data-layout-validation.json](test_inputs/data-layout-validation.json). Two genprop cases require
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

See AGENTS.md for source/dataset conventions and reference-work hygiene.
