# Regression status and coverage

## Full experimental no_1pt sweep: 3 November 2026

A separate full experimental sweep passed **all 30 active native-double
NPT/CORR cases**: 925 keys, 4,197 finite complex values, zero strict per-value
failures and zero comparison CG solves. Maximum absolute difference:
7.60540982951457e-14. All 29 experimental NPT outputs available in the historical
matrix are byte-identical. Only the declared eta control has an exactly
zero-valued channel. Format-4 graphs and explicit `average_1pt_diagrams=false`
were checked independently, along with matching NPT/CORR settings and hashes.

The data and direct-DISCO supplement exactly match the merged devel sweep below.
The four CORR deferrals are unchanged; separate experimental NPT-only fsq/glue/
tetra checks passed six keys and 96 values. The numerical tools are retained
corrected pre-YLM CPU snapshots, not a new clean source build. no_1pt remains
experimental, with devel as the baseline. The two separate new full sweeps now
cover 30 active cases per chain (60 comparisons, 8,394 finite compared values).
This does not claim a new full per-value experimental/devel cross-chain test.
See [experimental results and provenance](no1pt-native-regressions.md).

## Full merged devel sweep: 3 November 2026

Redstar merge `b194fdf` passed **all 30 active native-double NPT/CORR cases**,
including `nuc_nuc_3pt` with the explicit validated direct-DISCO supplement:
925 keys, 4,197 finite complex values, zero strict per-value failures and zero
comparison CG solves. The maximum absolute difference was
1.2193405344946423e-13. All 29 NPT outputs available in the historical matrix
are byte-identical to the merged build. Only the declared eta control contains
an exactly zero-valued channel.

The four CORR deferrals are unchanged: ff_3pt, fsq_3pt, glue and tetra_F27_S2.
Separate NPT-only fsq/glue/tetra checks passed six keys and 96 values; they do
not establish CORR support. ff_3pt remains deferred in NPT too. This is a fresh
merged Redstar build with retained native-reader dependencies and corrected
pre-YLM Chroma, using the existing RsdCG=1e-14 data. It is not a clean latest-YLM,
MPI or GPU validation. no_1pt was not part of that run; its subsequent full
sweep is recorded above. See the [full report and
provenance](arb-native-regressions.md).

## Historical matrix and targeted checks

The [3 November ARB merge check](arb-merge-validation.md) separately validates
Redstar merge `b194fdf`: eight legacy-SDB baseline comparisons passed with
byte-identical databases (39 keys, 354 finite complex values), plus targeted
memory-audit and three-hadron checks. It does not repeat or supersede the
native-double matrix below.

Updated 1 November 2026. The full native-double matrix passed **29 active cases on each chain** (58 case/chain comparisons, 8,380 finite compared values). Five historical cases per chain were deferred in that matrix; nuc_nuc_3pt has since passed its separate fresh-DISCO check, leaving four explicit CORR deferrals. This does not claim those implementations pass.

The dataset uses the original WEAK_FIELD/RNG, ten MOD64 vectors, RsdCG=1e-14, native SUPERB tensors with separate files per mass, and the full meson momentum sphere through mom2=4. Old datasets, reference SDBs and failed attempts are retained separately. Devel is the regression baseline (graph format 3); no_1pt remains experimental (format 4). Numerical executables are incremental corrected pre-YLM builds, not clean latest-YLM builds.

| Case | devel CORR vs NPT | experimental no_1pt CORR vs NPT |
|---|---|---|
| `1pt` | Passed | Passed |
| `33` | Passed | Passed |
| `3pi` | Passed | Passed |
| `a0.d3` | Passed | Passed |
| `a1_rhopi` | Passed | Passed |
| `d` | Passed | Passed |
| `delta_J1o2m` | Passed | Passed |
| `eta8eta8_F8` | Passed | Passed |
| `eta_eta_3pt` | Passed | Passed |
| `ff_3pt` | Explicitly deferred | Explicitly deferred |
| `fsq_3pt` | Explicitly deferred | Explicitly deferred |
| `glue` | Explicitly deferred | Explicitly deferred |
| `h8` | Passed | Passed |
| `hard.1_tslice.ini` | Passed | Passed |
| `nuc` | Passed | Passed |
| `nuc.p100` | Passed | Passed |
| `nuc_gA` | Passed | Passed |
| `nuc_nuc_3pt` | Passed (fresh DISCO; targeted check) | Passed (fresh DISCO; targeted check) |
| `nuc_nuc_ax_3pt` | Passed | Passed |
| `nuc_nuc_proj_3pt` | Passed | Passed |
| `nucnuc_small` | Passed | Passed |
| `nucpi` | Passed | Passed |
| `nucpi_I3o2` | Passed | Passed |
| `nucpi_J1o2m` | Passed | Passed |
| `nucpi_nucpi_J1o2m` | Passed | Passed |
| `pi` | Passed | Passed |
| `pi_pi_3pt` | Passed | Passed |
| `pion` | Passed | Passed |
| `pion_3pt` | Passed | Passed |
| `pipi_i1` | Passed | Passed |
| `psi` | Passed | Passed |
| `rho` | Passed | Passed |
| `rho_rho_3pt` | Passed | Passed |
| `tetra_F27_S2` | Explicitly deferred | Explicitly deferred |

## Explicit deferrals and separate NPT coverage

- ff_3pt: entire regression deferred; missing legacy gpdf.more.sdb generator. Historical reference retained; file not added to new dataset.
- nuc_nuc_3pt was deferred in the historical matrix. It is now covered by a separate passing native-DISCO comparison on both chains; see [DISCO validation](disconnected-loops.md).
- glue and tetra_F27_S2: CORR implementation deferred. Native storage equivalence and NPT consumer tests passed separately. The final portable runner supports NPT-only checks against the RsdCG=1e-14 candidate.
- fsq_3pt: gluonic-insertion CORR implementation deferred. NPT retains the explicitly authorized legacy gpdf_2_0.00.sdb; this file is not claimed as regenerated native-double data.

The machine-readable scope is [regression-policy.json](regression-policy.json). Separate NPT-only checks are reported in runs/native-npt-only-rsd14-20261101-001/results.json; their exact status must be read independently of the CORR matrix.

## What the passing matrix checks

Each case generates the chain's matching graph format, runs NPT and CORR_SUPERB, compares exact output keys and configuration/time shapes, independently exports all values and checks finiteness, then applies the unchanged strict gate:

`abs(NPT-CORR) <= 1e-9 * max(abs(NPT),abs(CORR)) + 1e-12 * max(reference_global_max,1e-30)`.

The separate dbutil relative-only result is retained as a diagnostic; it is not a substitute for the full per-value gate, particularly for cancellation channels. The eta_eta_3pt symmetry control must remain exactly zero with its expected key count. No channels were dropped to obtain a pass.

The saved full matrix is runs/native-comparison-matrix-20261101-004/results.json. Independent audit verified expected fixture coverage, all binary hashes, and zero strict failures. All 58 Chroma jobs used saved propagator/GenProp tensors and performed zero CG solves. [Measured timings](regression-timings.md) distinguish evaluator cost from generation and validation overhead.

## Storage and direct-comparison evidence

Tetra storage matched 32 keys/320,000 finite values exactly; the paired tetra_F27_S2 legacy/native NPT outputs were byte-identical (three keys/48 values). Glue matched 122,416 keys/1,224,160 finite values exactly, including native checksums and full readback; its paired legacy/native NPT check passed. These storage checks do not implement glue/tetra CORR callbacks.

The three-point failures exposed reversed-GenProp lookup, equal-endpoint diagonal support, and a pion_3pt comparison-harness vector-count error. Corrections now pass the complete matrix; see [three-point investigation](three-point-comparison.md) for retained failed evidence and validation details.

The original 12³×16 Nπ run also passed both chains with ten vectors and seven samples, 81+729 keys and 5,670 finite values. Its strict experimental/devel maximum difference is 1.110668157082426e-16. The small corrected devel references and checksums remain separate from experimental output.

## Reproducing the checks

`scripts/compare_regression_chains.py --help` lists explicit executable, dataset and output paths. It verifies the dataset manifest, records executable hashes and the supplied build qualification, preserves user deferrals, copies each NPT case's vector count to Chroma, and runs stored-tensor comparisons. Use `--cases` for a targeted check and `--npt-only` for separate NPT coverage; omitted case selection runs the full inventory. A fresh real-tool pion smoke test passed both chains in runs/portable-chain-smoke-20261101-001.

Generated tensors, logs, binaries and run directories stay outside Git. Historical exclusions remain in ../regressions/tests.toml. Source and workflow commits record this validation; generated payloads remain separate from source publication. The [Redstar primer](redstar-primer.md) introduces the complete validated workflow.

## Validated source commits

- ADAT native readers: [devel](https://github.com/JeffersonLab/adat/commit/41ad4df8806484bf745944f48f9c76a1b9251db5), [experimental no_1pt](https://github.com/JeffersonLab/adat/commit/96aec2b1ec681e0e15d1e8c98b1d525154e2f11d).
- ColorVec native consumers: [devel](https://github.com/JeffersonLab/colorvec/commit/8ee8bd31c11f053c77e80275aeb6505d6db38c46).
- Chroma native MOD readers and storage producers: [devel](https://github.com/JeffersonLab/chroma/commit/8da1a2b7682f7b7bf3e370ddea2ce1deef521d35), [experimental readers](https://github.com/JeffersonLab/chroma/commit/acf5dc0680084bac9e6abe38008e01ec35df7400).
- Redstar experimental one-point output extent: [no_1pt](https://github.com/JeffersonLab/redstar/commit/45898bd24ab7585d4507df66415326d18b424ec3).

The native-data payloads are not a new public data release. no_1pt stays experimental; the corrected pre-YLM numerical build qualification above still applies.

## Reopened disconnected-loop case

The user reopened `nuc_nuc_3pt` after the historical 29-case matrix; the new targeted comparison now passes on both chains. The recipe
`chroma_inputs/superb-double/disco.probing.ini.xml` uses gauge-transported
straight z paths through ±3 on the same WEAK_FIELD, RsdCG=1e-14 and native
DiscoBlocks storage. Generation/readback and matched comparisons are separate
gates. Supply a validated supplemental collection explicitly with
`--disco-dataset`; the runner hashes it and passes the same files to NPT and
CORR_SUPERB. The new report independently checks all seven values per chain, missing-data rejection and zero comparison CG solves. Together with the historical matrix, this covers 30 active cases per chain; it is not a newly repeated full 30-case sweep. Devel is the baseline and no_1pt is experimental. See [DISCO details](disconnected-loops.md).

## Direct DISCO generation acceptance

The canonical DISCO stage now appends every mass/time packet directly to one
`disco.sdb`, with no temporary shards or packing step. The full generated output
passed all 224 keys/3,584 values and agreed with the previous baseline. A fresh
paired nuc_nuc_3pt/pion check passed on both chains (four checks, 110 values, zero
comparison CG solves). See [direct DISCO results](disconnected-loops.md). This
validates the direct writer without claiming a repeated full 30-case sweep.
