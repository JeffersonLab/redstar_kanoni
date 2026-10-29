# Derivative vertex audit

This fixture isolates one-, two- and three-derivative coefficients by using the
`a0` Dirac structure (the four-dimensional spin identity). It checks graph
construction and vertex algebra. It does not evaluate a numerical correlator and
needs no Kanoni SDBs.

## Reproduce from this checkout

Use Python 3.9 or newer and one compatible Redstar installation. The audit uses
only the Python standard library; NumPy is not required. Build Redstar with
OpenMP using its [clean-build guide](https://github.com/JeffersonLab/redstar/blob/devel/docs/build.md).

From the Kanoni checkout root:

```sh
export REDSTAR_BIN=/path/to/redstar/install/bin
python3 test_vertices/run.py --threads 4
```

The runner creates a unique `runs/derivative-audit-*` directory. It regenerates
all operator definitions and correlator selections, compares them against the
tracked fixtures, builds a complete v14 graph input, runs `redstar_corr_graph`
and `dump_corr_graph`, then audits the exported coefficients. No ignored file
from an earlier run is needed. All inputs and references in this checkout remain
unchanged. `run.json` records executable/input hashes, requested threads, commands,
return codes, timings and observed coverage; per-phase logs remain beside it.

`--redstar-bin` overrides `REDSTAR_BIN`; otherwise all four tools must be on PATH
and belong to one installation. `--timeout` sets a per-executable time limit
(default 180 seconds). An explicit `--output` directory must not already exist.
The runner requests four OpenMP workers by default and disables dynamic teams;
the underlying installation must itself have working OpenMP support. Its build
should pass Redstar's independent observed-team checks.

## Files and coverage

| File or stage | Purpose and expected count |
| --- | --- |
| `single.cont.list` | 11 continuum derivative-only operators. The first column is ignored by the one-hadron generator. |
| `single.ops.list`, `single.ops.xml` | 139 unique list/map entries generated over momentum squared 0 through 4. |
| `gen.2pt.ini.xml` | Two-point selection at momenta 000, 001, 011, 111, row 1. The 29 entries at 002 are intentionally not selected. |
| `red.xml` | 482 unique `NPointList` entries, using 110 selected operator definitions. This is not a complete `RedstarNPt` input. |
| Graph binary/export | 482 correlators, 482 graphs and 220 unique vertices. |
| `../derivative_vertex_audit.json` | Historical successful reference: 110 creation/annihilation pairs, 1,724 derivative-path terms and 6,896 spin coefficients. |
| `../selected_derivative_vertices.xml` | Four coefficient snapshots: creation/annihilation for a rest-frame two-derivative scalar and a moving three-derivative J=3 operator. |

`OpsList`, `GenerateXML` and `NPointList` are separate schemas and do not receive
a v14 tag. The runner embeds the generated `NPointList` into a v14 graph input
with lattice 4×4×4×16, Nt=16, anti-periodic boundary conditions, explicit automatic
CG settings and the original flavor conversion. There are no projected weights
or numerical database inputs in this fixture.

The fresh macOS Apple Clang/libomp run on 2026-10-28 reproduced every operator and
correlator definition, all coverage counts and all four selected snapshots.
The largest derivative-basis residual was 2.226e-14, the adjoint residual was
zero, and analytic-basis orthogonality differed from identity by at most 8.882e-16.
The historical JSON remains unchanged; floating-point reduction order can change
its last few digits. Acceptance uses the original 1e-10 tolerance, exact key/path
coverage and per-vertex normalization checks. Twenty setup/runner/audit regression
tests passed, including rejection of corrupted coefficients and reduced coverage.
A second fresh run from outside the checkout, using one requested worker and a
spaced output path, passed too. All 220 vertex coefficient maps (1,724 path terms)
were identical between the one- and four-worker runs.

## What is checked

The independent analytic calculation builds circular derivatives in Cartesian
components, couples SU(2) spins (including J13 for three derivatives), and reverses
the nested derivative order to match stored paths. The conventions follow
Redstar `lib/operators/twoquark_deriv_ops.cc`.

For every vertex it checks explicit zero phasing, the intended scalar spin/color/
flavor structure, finite coefficients, four identical diagonal spin entries,
unique derivative paths, membership in the specified coupled-spin subspace, and
unit normalization. For every creation/annihilation pair it checks path reversal,
complex conjugation and the sign (-1)^n. The complete vertex identities and path
counts must match the historical reference. The four selected snapshots also have
their individual coefficients checked.

Subspace membership and normalization alone do not establish every little-group
subduction phase or row convention: another normalized vector in the same spin
subspace can pass those tests. The four snapshots provide limited coefficient
regression coverage. This audit does not prove full subduction covariance,
numerical database evaluation, Hermiticity of measured correlators, or physical
matrix elements.

## Audit an existing graph export

Choose a new output filename; the script refuses to overwrite an existing file:

```sh
python3 audit_derivative_vertices.py /path/to/corr_graph.inspect.xml \
  --output /path/to/new-audit.json
```

The new report records the chosen tolerance. The defaults compare against the
checked-in full JSON and four selected vertices.
The graph must cover this complete derivative fixture; a smaller map fails the
coverage check. `graph.out.xml` is a run report and cannot replace the graph export.
Malformed paths, nonfinite values and duplicate entries are errors. Zeroed
coefficients cannot pass merely because they lie in every linear subspace.
Failures return nonzero, including when Python is run with optimization enabled;
validation does not rely on `assert` statements. Numerical failures are retained
in the new report when parsing/structural checks allow one to be written.

Run the fast regression tests from the checkout root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```
