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

## MPI with QDP parscalar and MPI-backed QMP

Invoke the driver **once**, and let it launch Chroma's ranks:

```sh
export REDSTAR_BIN=/absolute/path/to/devel/redstar/bin
export CHROMA_BIN=/absolute/path/to/devel/mpi-chroma/bin
export MPIEXEC=/absolute/path/to/the/matching/mpiexec

./run_chroma.csh regressions/corr_superb/chroma.xml \
  --graph-input regressions/direct/pion/graph.xml \
  --mpi-ranks 2 --threads 2
```

`--mpiexec` overrides `MPIEXEC`. An absolute launcher path is required; there is
no launcher PATH search. Use the MPI implementation matching the selected
Chroma/QDP/QMP libraries. `CHROMA_BIN/chroma-config`, its matching installed
headers/libraries, QDP **parscalar**, MPI-backed QMP and OpenMP are required.
The same devel graph-format-3 requirement applies to MPI runs.

For Open MPI, binding can be controlled explicitly:

```sh
./run_chroma.csh regressions/corr_superb/chroma.xml \
  --graph-input regressions/direct/pion/graph.xml \
  --mpi-ranks 2 --threads 2 \
  --mpi-arg=--bind-to --mpi-arg=none
```

Repeat `--mpi-arg` for each launcher argument; set the rank count only through
`--mpi-ranks`. `--mpi-ranks 1` exercises the same MPI path for a one-rank
numerical baseline. Omitting it preserves the existing single-process mode.
Do not wrap the driver itself in `mpirun`/`mpiexec`; nested rank launches are
rejected before creating a run.

The driver generates/inspects the graph once. It then compiles a small runtime
probe through the selected `chroma-config` and verifies MPI/QMP world ranks,
QDP lattice distribution and an actual OpenMP team on every rank. A separate
zero-measurement Chroma invocation checks that the **selected binary itself**
reports the requested distributed geometry; for multi-rank launches, a stale
SINGLE binary cannot pass merely because its config script describes an MPI
build. These probes do not
alter the science job's gauge, RNG, XML settings or graph.

Gauge conversion runs with one guarded rank. The final CORR_SUPERB invocation
runs with the requested rank count. Its output XML must again report that
geometry. Every rank receives the same absolute prepared input and real data
paths. Only the selected graph/Chroma/layout XML and referenced weights are
saved under `run_inputs/`; the run directory contains generated probe binaries,
build records, runtime JSON, XML reports, logs, gauge, correlators and resource
records. The scientific outputs retain their usual filenames.

`--threads` is explicitly applied inside every rank, rather than inferred from
the outer launcher environment. `--memory-limit-mb` applies independently to
each actual rank child, not just to `mpiexec`. Each guard records its rank,
child PID, worker setting, RSS samples/peak, exit status and timeout in
`resource-<stage>-rank-<rank>.json`. The rank timeout is `--timeout`; the
launcher receives a 30-second cleanup margin. On interruption the launcher gets
SIGTERM and a five-second grace period so guards can kill their children and
retain failure records. The serial graph/build commands retain their existing
command-process limits. A failed rank cannot be hidden by a primary-rank
correlator file or a launcher exit without the required rank records.

See [MPI validation and evidence](run-chroma-mpi-validation.md) for the actual
one-/two-rank devel comparisons and source/build qualification. The older
[serial validation](run-chroma-validation.md) remains a historical record of
its original SINGLE-QMP run.
