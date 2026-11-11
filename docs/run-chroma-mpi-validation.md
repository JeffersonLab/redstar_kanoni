# run_chroma MPI validation: 11 November 2026

The devel saved-field pion workflow passed with **one and two local MPI ranks**,
using QDP parscalar, MPI-backed QMP and **two measured OpenMP workers per rank**.
Independent readback found exactly **3 keys, 48 finite complex values and 1×16
shapes**, with no zero-valued channel. One versus two ranks had **zero strict
failures**; maximum absolute difference was **1.954399679134266e-14**.

This is a targeted standalone Chroma check. It does not extend the historical
full native-double suite to MPI or validate NPT, multiple hosts or GPUs.
This is one-configuration software validation, not ensemble statistics.
The machine-readable [report](run-chroma-mpi-validation.json) records hashes,
source pins, launcher commands, geometries, runtime probes and rank resources.
See [usage](run-chroma.md#mpi-with-qdp-parscalar-and-mpi-backed-qmp).

## Executed stack and build qualification

Kanoni parent: `3b12e09e2ebf83c73387eb2af464279c5d44eb95` on `devel`.
Graph generator/viewer: existing merged Redstar devel install under
`runs/arb-merge-build-20261103-001/install/bin`, producing **format 3**.

Chroma was freshly compiled from its devel commit
`e1ac530e0bd50dbeac75a1e94d62a981308fe251` in a new empty build directory.
It requires the legacy contraction backend absent from ordinary ADAT devel:

- backend: `origin/eloy/redstar-datalib@be218b0c506acd0062959f19258a5c8c37ffd58e`,
  archived locally without changing or merging any branch;
- compatibility: exact `lib/io/disco_superb.h` from canonical ADAT devel
  `7b1d36f574bce5d77f1c5d0ed985d06d97f5be1f`, applied in the isolated source
  providing the current Chroma DISCO writer API;
- callback compatibility: backport of `6022296b3ad2a5cc6e5bc8ffeb5cf640adfeac31`
  in `lib/algs/superb_contractions.h`, adapted to the format-3 `graph`/`stich`
  representation and its fixed-one-point time handling;
- header SHA-256: `029fd94b042f5c948d0d82bf37f8fea272b5065d9d89361ef4fc08757ca38443`;
- patch and complete source/build provenance are retained under
  `run_inputs/mpi-devel-build-20261111-001/` and
  `runs/mpi-devel-build-20261111-001/`.

This is **not an unchanged ADAT devel-tip or a wholly rebuilt dependency stack**.
The final build continued from the initially empty build after both source
compatibility changes, using ordinary make dependency rebuilding and install.
No old object/binary overlays were used. The existing MPI dependency installs
from `runs/no1pt-clean-20261103-002/install/` were reused; QMP/QDP/SuperbBLAS
are independent of the graph format. Their original source pins are:

| Component | Source commit | Checked profile |
| --- | --- | --- |
| QMP | `3010fef5b5784b3e6eeec9fff38cb9954a28ad42` | MPI communications |
| QDP++ | `c1e9b5209f89d232af064a60004f8ac7c9a5c734` | parscalar, double, Nd=4, OpenMP |
| SuperbBLAS | `6714302c08d82e22dd5a7bb018ff40e3926bd3a2` | CPU, MPI enabled |

Compiler: Apple clang version 21.0.0 (clang-2100.1.1.101). Launcher: mpiexec (Open MPI) 5.0.7.
Chroma/probe/converter use Clang/libomp and the matching MPI libraries.
The independent exporter runs separately. Linkage evidence is retained locally.
The DISCO compatibility API is compiled, not numerically exercised by this pion
case. No experimental format-4 graph or evaluator was substituted.

## Real commands and results

The driver was invoked from `/private/tmp`, with absolute input paths and these
explicit selections (expand `KANONI` to the checkout path):

```sh
KANONI=/Users/admin/Downloads/redstar_kanoni.devel
export REDSTAR_BIN="$KANONI/runs/arb-merge-build-20261103-001/install/bin"
export CHROMA_BIN="$KANONI/runs/mpi-devel-build-20261111-001/install/chroma-v3-compatible/bin"
export MPIEXEC=/opt/homebrew/bin/mpiexec
export OMPI_CC=/usr/bin/clang
export OMPI_CXX=/usr/bin/clang++

cd /private/tmp
"$KANONI/run_chroma.csh" "$KANONI/regressions/corr_superb/chroma.xml" \
  --graph-input "$KANONI/regressions/direct/pion/graph.xml" \
  --mpi-ranks 2 --threads 2 --mpi-arg=--bind-to --mpi-arg=none \
  --output "$KANONI/runs/chroma-mpi-devel-2rank-20261111-001"
```

The one-rank baseline used `--mpi-ranks 1` and a separate `1rank` output path.
These retained output names now exist; choose new names to repeat the checks.
Both runs used the default 8,192 MiB **per actual rank** RSS cap, 6 GiB planner
budget and 1,800-second rank timeout. The MOD pair was checksum-verified, read
in place and never copied or aliased into the run directories. Gauge conversion
ran with one rank and confirmed squared QIO roundtrip error zero.

| Check | One rank | Two ranks |
| --- | --- | --- |
| Driver result | `executables_passed` | `executables_passed` |
| CG solve markers | 680 | 680 |
| MPI/QMP world | 1 | 2 |
| Measured OpenMP workers/rank | 2 | 2 |
| Local sites/rank | 1024 | 512 |
| Global QDP sum of ones | 1024 | 1024 |
| Keys / finite complex values | 3 / 48 | 3 / 48 |

The runtime probe verifies actual MPI/QMP identity and a distributed QDP sum.
A zero-measurement invocation checks the selected Chroma binary's own topology
before the science job; the final XML is checked again. Every rank guard
recorded successful completion and positive RSS observations of the actual
Chroma process. Two-rank peak RSS values were
68928 KiB (rank 0), 64688 KiB (rank 1).

Acceptance used the unchanged per-value gate:
`1e-9 * max(abs(reference), abs(candidate)) + 1e-12 * max(reference_global_max, 1e-30)`.
Exact key coverage, 1×16 shapes and complete finite readback accompany the
comparison. The relative-only dbutil diagnostic remains separately recorded.

The new one-rank MPI result also passed against the archived serial Chroma
result: zero strict failures, maximum absolute difference
`3.5623136682461841e-15`. That reference's historical NPT comparison
remains **numerical_mismatch** because it used a separate legacy dataset.
This reproducibility check does not promote that result to a matched NPT pass.

## Tests, layout and retained evidence

- Python 3.13: 89 tests passed; Python 3.9: 89 tests, seven optional TOML skips.
  The final seven targeted MPI tests also passed after failure-record handling
  was refined. Tests cover stage/rank dispatch, failed secondary ranks, stale
  SINGLE binaries, explicit launchers, nested launches, rank timeouts and
  launcher-timeout cleanup of the actual rank child.
- The real two-rank Open MPI interruption check also passed: both actual rank
  children were stopped and both guards retained their failure records.
- Sources/prepared XML and weights remain under `run_inputs/`; runtime
  directories contain generated outputs only. No data symlinks, source XML or
  unrelated templates were introduced there.
- Historical serial evidence, its NPT mismatch, release manifest and regression
  policy hashes were rechecked unchanged. Existing deferrals remain intact.
- Evidence root: `runs/run-chroma-mpi-validation-20261111-001/`; real outputs:
  `runs/chroma-mpi-devel-1rank-20261111-001/` and
  `runs/chroma-mpi-devel-2rank-20261111-001/`.
- All initial failures are retained: an unavailable old installed config/lib
  profile; ordinary ADAT devel missing backend headers; the legacy backend
  missing the current DISCO storage and evaluator callback APIs; and a unit-test-discovered redundant macOS
  kill of an exited guard. The final build/checks supersede those attempts.
  `v5-build.json` is the successful build-attempt record; the graph format is **3**.

No source branch outside Kanoni was modified. Existing devel/Kanoni historical
records and datasets were preserved; this change adds the MPI runner and its
qualified evidence on Kanoni devel.
