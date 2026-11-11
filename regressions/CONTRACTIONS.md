# Split contraction regressions: 4 × 4 × 4 × 16

The three entry points share one graph-generation implementation:

1. `scripts/run_corr_graph.py`: graph XML → `redstar_corr_graph` → `corr_graph.bin`; inspect the result with the matching `view_corr_graph`.
2. `scripts/run_redstar_npt.py`: the same graph stage, then a separate npt XML → `redstar_npt` → `output.sdb1` → independent numerical readback and comparison.
3. `scripts/run_corr_superb.py`: the same graph stage, then one ordinary Chroma invocation with its selected Chroma template → `output.sdb1` → independent numerical readback and comparison.

Each invocation creates a fresh run directory. Graph-only runs need neither the
raw SDB dataset nor a saved numerical reference. The two numerical workflows
require their trusted, checksum-pinned references; they never establish or
replace a reference as a side effect of testing.

## Layout

```text
regressions/
  redstar/
    <case>/case.json       # counts, shapes, pinned reference, provenance
    <case>/graph.xml       # v14 graph controls + NPointList + projected weights
    <case>/npt.xml         # numerical controls + ColorVec/database settings
    <case>/weights/...     # only the projected weights used by this case
  corr_superb/
    chroma.xml            # saved MOD fields, 16-sample direct pion template
    chroma.generated.xml  # generated-vector 4³×16 Nπ job, seven samples
    npi_000_G1g/           # graph.xml + case.json; full 9×9 matrix
    npi_001_E1/            # graph.xml + case.json; full 27×27 matrix
```

The `redstar/` directory contains split copies of the **34 active validated
cases** in the existing inventory: 33 positive real-data cases and one exact
isospin-zero control. Their operator selections, phasings, time controls, masses,
and numerical settings are preserved. The five existing exclusions are not
silently promoted into this suite. The legacy combined inputs, baseline files,
`tests.toml`, and older runners remain available.

The CORR_SUPERB cases preserve the full original Nπ bases selected with L=12,
but their **contraction geometry is 4³×16**. Both have ten vectors, source zero,
and seven sink samples. Their references are the accepted corrected **devel**
compact outputs, not experimental outputs or the running 12³ test.

## Select executables

Copy [contraction-tools.example.toml](contraction-tools.example.toml) to an
ignored `contraction-tools.local.toml` and set the executable paths. You can use
separate local files for Redstar and CORR_SUPERB stacks. TOML paths must be absolute. Python 3.11+ supports TOML directly;
Python 3.9/3.10 needs `tomli` only when `--tools` is used.

`--redstar-bin` (or `REDSTAR_BIN`) selects an absolute directory containing the
matching graph generator and viewer; it also selects `redstar_npt` for the
Redstar workflow. `--chroma-bin` (or `CHROMA_BIN`) selects an absolute directory
containing `chroma`. Explicit directory options override environment variables,
which override the tool file. All TOML executable paths must be absolute;
Redstar and Chroma must be selected through their bin-directory entries.
There is no executable PATH search or sibling-build fallback for either stack.
Use compatible installed libraries within each executable. The runners invoke
tools as separate processes.

```sh
python3 scripts/run_corr_graph.py regressions/redstar/pion \
  --tools regressions/contraction-tools.local.toml

python3 scripts/run_redstar_npt.py regressions/redstar/pion \
  --tools regressions/contraction-tools.local.toml

python3 scripts/run_corr_superb.py regressions/corr_superb/npi_001_E1 \
  --tools regressions/contraction-tools.local.toml --threads 1
```

Add `--output runs/my-new-run` to select a fresh destination. Existing outputs
are rejected without altering them. Default limits are four OpenMP workers,
one BLAS worker, 1,800 seconds per executable, and a 6 GiB SUPERB contraction
budget. `--threads`, `--timeout`, and `--contraction-memory-gb` override these.
Only the Chroma contraction backend uses the latter budget.

## What belongs in the Chroma input?

No NPoint list, projected operator definitions, or npt ColorVec configuration
is copied into Chroma. Operator and contraction information arrives through
`corr_graph.bin`.

A runnable Chroma job still needs the gauge setup and color vectors in addition
to the propagator/solver configuration. The Nπ cases select `chroma.generated.xml`, which runs
`CREATE_COLORVECS_SUPERB` followed by `CORR_SUPERB` in the same vanilla Chroma job.
It uses the existing weak field, RNG 11/11/11/0, isotropic clover mass 0.05,
coefficient 1, temporal antiperiodicity, stout settings and CG 1e-8/1000.
There are no pre-existing propagator, generalized-propagator, meson or baryon
SDB inputs. Eigenvectors are generated afresh in each run.

The fixed names are `eigs.sdb`, `corr_graph.bin`, and `output.sdb1`. Only the case
selection changes between the two Nπ tests. A graph with a different lattice,
source origin, vector count or time extent requires an explicitly different
Chroma setup; the runner rejects an inconsistent case/template combination.
These established regression inputs require graph **format 3**. `no_1pt`
remains experimental and is not the source of saved regression references.

For the separate saved-field pion job, use [run_chroma](../docs/run-chroma.md)
with `chroma.xml` and `regressions/direct/pion/graph.xml`. It generates a graph
and runs Chroma without NPT or a pinned-reference comparison, verifies the
saved MOD pair, and keeps its original/prepared inputs outside the output
directory. Its 16-sample graph is separate from the seven-sample Nπ cases.

## Data, references and checks

Run `./setup-data` for Redstar's immutable raw dataset; `--database-dir` or
`KANONI_DATA_DIR` selects another real, checksum-verified data directory. npt
input database names are rebased to that directory, without SDB symlinks or
per-run payload copies.

The existing Redstar reference SDBs remain at `regressions/<case>/output.sdb1`.
The two small CORR_SUPERB reference SDBs are regular read-only files under
`data/regressions/corr_superb/`; their hashes and provenance are pinned in each
`case.json`. All SDB payloads are Git-ignored. A clone contains inputs and hash
pins, not these saved references: restore trusted baseline bytes at the declared
locations before numerical comparisons. `setup-data` installs the raw release
payloads; it does not download these additional regression outputs. Missing or
mismatched references cause an error before numerical evaluation.

Every numerical run requires exact independent key coverage, the expected
one-configuration/time shape, finite values, and successful comparison with its
pinned reference. The Redstar exact-zero case stays a separately declared
control; positive cases must not contain zero channels. Nπ checks additionally
require the complete 9×9 or 27×27 source/sink matrix and the existing per-value
`1e-9` relative tolerance plus `1e-12` times the reference maximum as an absolute
floor. No failing channel is removed. The numbered exporter avoids long or
colliding database filenames and builds with the selected `adat-config` when
`--exporter` is not provided.

`run.json` retains input/reference hashes, executed commands and tool hashes,
coverage and readback results. Logs, native XML reports, `corr_graph.bin`,
`output.sdb1`, and independent exports stay together in the fresh run directory.
A successful graph-only run is labelled `graph_passed`, never a numerical pass.
These are single-configuration software checks, not physical ensemble results.

The Redstar and CORR_SUPERB suites have independent trusted numerical baselines.
A common geometry does not establish cross-backend numerical agreement; that
requires matching gauge, propagator, and elemental data. The shared Chroma
template currently covers the supplied light-flavor two-point Nπ cases. New
flavors, current insertions, or different source/time coverage may require an
explicit additional solver/measurement configuration.

See [observed validation results](CONTRACTIONS_VALIDATION.md) for the fresh
split-input checks and the precise shared-Chroma coverage.
