# Merged devel: full native-double NPT/CORR regression

Validated on 3 November 2026 with Redstar devel merge `b194fdf`.
**All 30 active devel comparisons passed**, with 925 keys,
4,197 finite complex values, zero strict per-value failures
and zero comparison CG solves. The four existing CORR deferrals remain intact.
This is a new full devel sweep including native-DISCO `nuc_nuc_3pt`; experimental
no_1pt was not rerun. The historical 29-case/two-chain matrix remains separate.

The subsequent [separate experimental full sweep](no1pt-native-regressions.md)
also passed all 30 active cases using the same data. no_1pt remains experimental.

## Build and data qualification

The exact merged Redstar source was freshly built in
`runs/arb-native-build-20261103-001/`, using serial Apple Clang 21, C++20,
Accelerate and undefined-behavior instrumentation. All 867 archived tracked files
were verified against the merged Git revision. `make` and `make check` passed;
`make check` builds check programs but declares no Automake `TESTS` suite.
This build uses the retained native ColorVec/ADAT/Hadron stack and corrected
pre-YLM Chroma v15 direct-DISCO snapshot. Those dependencies were reused, not
cleanly rebuilt. The [machine-readable record](arb-native-regressions.json)
pins executable/library hashes, configuration, dataset hashes and commands.
Current source branch heads are not a claim about how reused binaries were built.

The RsdCG=1e-14 candidate is
`runs/native-superb-rsd14-20261101-001/`: native-double MOD color vectors,
per-mass propagators and GenProps, and the meson momentum sphere through mom2=4.
The direct one-file DISCO supplement is
`data/disco-native-direct-20261101-001/`. Input and payload hashes, lattice,
solver accuracy, gauge and RNG were checked before use. Original dataset
manifests and archived inputs were preserved, including their historical status
labels. This is not a new public data release. See [DISCO](disconnected-loops.md)
and [dataset recipes](../chroma_inputs/README.md).

The suite uses fresh format-3 graphs and matching merged NPT, one CPU worker,
fake data disabled, and saved tensors. NPT vector count, time origin, averaging
and zero-unsmeared settings match CORR; pion_3pt retains its two-vector setting.
The full run does not use the earlier legacy-only OpenMP build described in the
[initial ARB validation](arb-merge-validation.md).

## Paired results

Independent exports checked exact key coverage, equal configuration/time shapes,
expected case coverage and complete finite complex readback. A second audit
rechecked all values, hashes, input settings, format-3 graphs and zero CG solves.
Every complex value passed the unchanged gate:

```text
abs(NPT-CORR) <= 1e-9 * max(abs(NPT),abs(CORR))
                + 1e-12 * max(reference_global_max,1e-30)
```

| Case | Keys | Complex values | Maximum absolute difference |
| --- | ---: | ---: | ---: |
| pion | 3 | 48 | 9.04113e-15 |
| 1pt | 3 | 48 | 1.02256e-18 |
| 33 | 1 | 16 | 1.14184e-15 |
| 3pi | 3 | 48 | 1.21934e-13 |
| a0.d3 | 324 | 1296 | 5.79247e-20 |
| a1_rhopi | 1 | 16 | 3.37339e-15 |
| d | 1 | 16 | 3.04364e-16 |
| delta_J1o2m | 1 | 16 | 1.11509e-16 |
| eta8eta8_F8 | 1 | 16 | 1.42025e-15 |
| eta_eta_3pt | 1 | 16 | 0 |
| h8 | 4 | 64 | 4.45635e-14 |
| hard.1_tslice.ini | 529 | 2116 | 2.78053e-19 |
| nuc | 1 | 16 | 2.22045e-16 |
| nuc.p100 | 2 | 14 | 2.1207e-16 |
| nuc_gA | 1 | 7 | 1.47706e-17 |
| nuc_nuc_3pt | 1 | 7 | 4.17777e-17 |
| nuc_nuc_ax_3pt | 4 | 28 | 8.55352e-17 |
| nuc_nuc_proj_3pt | 1 | 7 | 2.57141e-19 |
| nucnuc_small | 2 | 8 | 1.11022e-16 |
| nucpi | 1 | 16 | 3.54746e-17 |
| nucpi_I3o2 | 1 | 16 | 2.64545e-17 |
| nucpi_J1o2m | 1 | 16 | 2.5101e-17 |
| nucpi_nucpi_J1o2m | 2 | 32 | 4.51828e-15 |
| pi | 1 | 16 | 1.26001e-15 |
| pi_pi_3pt | 1 | 6 | 2.93266e-16 |
| pion_3pt | 1 | 7 | 3.01842e-16 |
| pipi_i1 | 1 | 16 | 2.67334e-15 |
| psi | 2 | 32 | 4.01209e-15 |
| rho | 3 | 48 | 1.24409e-14 |
| rho_rho_3pt | 27 | 189 | 6.08401e-16 |

Maximum absolute difference over the suite: 1.2193405344946423e-13.
The relative-only dbutil comparison remains a separately recorded diagnostic;
it does not replace the strict per-value gate. No tolerances were changed.
Exactly zero-valued channel counts: eta_eta_3pt (NPT 1, CORR 1).
The eta_eta_3pt control is required to be exactly zero with its expected key count;
it is not a positive channel. No failing or zero channels were discarded.

For the 29 historical devel NPT outputs available in the previous
matrix, 29 are byte-identical to this
merged build's outputs. nuc_nuc_3pt is covered by the new full sweep rather than
the old matrix's historical deferral. Saved baselines were not overwritten.

## Deferrals and separate NPT coverage

[The policy](regression-policy.json) is unchanged. ff_3pt remains deferred in
both NPT and CORR. Glue, tetra_F27_S2 and fsq_3pt remain CORR deferrals.
Separate NPT-only checks passed for all three: six keys and 96 finite complex
values. These checks establish key/shape/finite NPT coverage, not CORR support.
fsq_3pt uses the explicitly retained legacy gpdf_2_0.00.sdb; it is not claimed
as regenerated native-double data. No on-demand GenProp, displaced-current,
MPI, GPU, clean latest-YLM or ensemble-physics validation is implied.

## Retained evidence and repetition

- `runs/arb-native-build-20261103-001/`: configuration, source verification,
  build logs, exact command JSONs, native binaries and audit script.
- `runs/arb-native-full-20261103-001/results.json`: full paired runner report;
  `independent-audit.json` records the second numerical/hash audit.
- `runs/arb-native-npt-only-20261103-001/results.json`: separate NPT-only report
  and independent audit.

The exact invocations are also embedded in the compact JSON record. The paired
command uses `--chain devel`, omits `--cases` to cover the complete inventory,
and passes `--disco-dataset` explicitly. Feature executable paths are required
by the current CLI but were not executed in this devel-only run. The existing
runner requires child-process inspection for its RSS limit. Use a fresh output
directory for every repetition, retain the default 900-second executable timeout
and 8192-MiB RSS cap unless deliberately recording a different resource policy,
and select the same pinned dataset/tools. Generated payloads and logs remain
Git-ignored. Earlier build and regression evidence is retained separately.
