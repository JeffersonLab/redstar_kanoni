# Standalone Chroma CORR_SUPERB

`run_chroma.csh` runs the saved-field CORR_SUPERB workflow: graph generation,
graph inspection, matching gauge conversion and ordinary Chroma. It does not
run Redstar NPT or regenerate color vectors. Use compatible **devel graph-format-3**
executables; the separate reorg/no_1pt format-4 stack is not interchangeable.

## Run the supplied pion input

From the checkout root:

```sh
export REDSTAR_BIN=/absolute/path/to/redstar/install/bin
export CHROMA_BIN=/absolute/path/to/chroma/install/bin

./run_chroma.csh regressions/corr_superb/chroma.xml \
  --graph-input regressions/direct/pion/graph.xml \
  --threads 1
```

Or use Python directly, without tcsh:

```sh
python3 scripts/run_chroma.py regressions/corr_superb/chroma.xml \
  --graph-input regressions/direct/pion/graph.xml --threads 1
```

The positional input is a **complete Chroma XML**, while `--graph-input` is
**graph-only RedstarNPt v14 XML**. Pass explicit paths relative to the caller's
working directory, or absolute paths. From another working directory:

```sh
KANONI=/Users/admin/Downloads/redstar_kanoni.devel
"$KANONI/run_chroma.csh" "$KANONI/regressions/corr_superb/chroma.xml" \
  --graph-input "$KANONI/regressions/direct/pion/graph.xml" --threads 1
```

The driver chooses the execution working directory itself. There is no need to
`cd` into a run directory or stage XML by hand. This example uses a 4³×16
lattice, ten saved vectors, source zero and 16 time samples; its graph declares
three correlators. Geometry, time-window, source-origin, ensemble and known
case/vector mismatches are rejected before computation. The generated-vector
Nπ input `chroma.generated.xml` belongs to the existing `run_corr_superb.py`
regression workflow; its seven-sample graphs do not match this pion job.

## Select executables and data

`REDSTAR_BIN` must contain `redstar_corr_graph` and `view_corr_graph`;
`CHROMA_BIN` must contain `chroma`. Both must be explicitly selected absolute
directories. `--redstar-bin` and `--chroma-bin` override the environment.
The driver does not search PATH, infer sibling checkouts, or accept the legacy
`CHROMA` executable variable. An installed executable may itself be a symlink.

The matching saved files must be regular files in `data/`:

```text
data/colorvec.mod
data/gauge.mod
```

The driver checks their sizes and SHA-256 against
`test_inputs/mod-manifest.json`, and rejects symlink data homes or payloads.
`--database-dir` overrides `KANONI_DATA_DIR`, which overrides checkout `data/`.
To import the pinned pair from an existing collection:

```sh
python3 scripts/import_mod_data.py --source-dir /absolute/path/to/matched-mod-files
```

`setup-data` distributes the separate SDB release, not the MOD pair. This
on-demand pion example needs no input propagator/elemental SDBs. If a custom
Chroma XML explicitly lists `props`, `genprops`, `mesons` or `baryons`, use
absolute file paths or basenames in the selected data directory. These files
are read directly and hashed, without per-run copies or aliases. Their physics
and basis must match the saved fields; the driver does not establish that
agreement merely from filenames or dimensions.

The prepared Chroma input receives an absolute path to the selected
`colorvec.mod`; its graph is `corr_graph.bin`, derived gauge is `gauge.lime`,
and output is `output.sdb1`, all relative to the fresh execution directory.
The selected original input's gauge settings, solver, flavors, smearing, RNG
and other physics fields are preserved. The supported saved-field template
uses one CORR_SUPERB measurement with `SZINQIO`/`gauge.lime`.

## Gauge converter

By default, each run builds the small converter using
`CHROMA_BIN/chroma-config`. The converter executable, compiler command and
build log are generated outputs retained with the run. The converter reads
`data/gauge.mod`, writes `gauge.lime` and requires exact QIO readback before
Chroma starts. It does not replace the saved gauge with a regenerated field.

To reuse a compatible converter instead, including with a custom Chroma bin
directory that has no `chroma-config`:

```sh
./run_chroma.csh regressions/corr_superb/chroma.xml \
  --graph-input regressions/direct/pion/graph.xml \
  --gauge-importer /absolute/path/to/mod_gauge_to_qio --threads 1
```

The converter runs in its own process. Use compiler/library settings consistent
within each process; never mix Clang/libomp and GCC/libgomp libraries in one.

## Outputs and provenance

Each attempt uses a fresh `runs/chroma-graph-<timestamp>-<unique>/`, or a new
`--output` directory. Existing outputs and input snapshots are never overwritten.
The output directory contains only generated artifacts:

- `corr_graph.bin`, `graph.out.xml`, `graph.log` and `view.log`;
- `gauge.lime`, `gauge-import.log`, and converter build outputs when built there;
- `output.sdb1`, `chroma.out.xml`, `chroma.log` and any measurement reports;
- `run.json`, with commands, actual working directory, tool/input/output hashes,
  expected coverage, limits, status and measured CG-solve count.

Only the chosen original/prepared XMLs and declared projected weights are
snapshotted under ignored `run_inputs/<output-directory-name>/`. No unrelated
XMLs, lists or directory trees are copied. The selected data stays in its real
data home. Keep these input snapshots with successful outputs when archiving.
Choose a unique output-directory name if using `--output`; an existing snapshot
with the same name is preserved and reported rather than overwritten.

The driver requires graph format 3, matching graph coverage, exact gauge
conversion, parseable XML reports, a Chroma completion marker and a nonempty
correlator file. Success is labelled **`executables_passed`**, not a numerical
regression pass. Independent key/shape/finite-value readback and numerical
comparison remain separate checks. `chroma.out.xml` is a report;
`output.sdb1` is the numerical database.

## Resources and validation scope

Defaults are four requested OpenMP workers (or `OMP_NUM_THREADS`), one BLAS
worker, 1,800 seconds per executable, an 8,192 MiB command-process RSS cap and
a 6 GiB contraction planner budget. Change them with `--threads`, `--timeout`,
`--memory-limit-mb` (zero disables the RSS cap) and `--contraction-memory-gb`.
Failed logs, partial outputs and failure metadata are retained.

Invoke the driver once from the shell. It launches one Chroma process; a
multi-rank launcher mode is not implemented. Do not run independent driver
copies under `mpirun` to obtain one distributed job.

See [devel validation and evidence](run-chroma-validation.md) for actual
readback, reference comparisons, preservation checks and qualification limits.
