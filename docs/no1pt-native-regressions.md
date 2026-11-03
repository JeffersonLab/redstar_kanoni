# Experimental no_1pt: full native-double NPT/CORR regression

Validated on 3 November 2026. **All 30 active experimental no_1pt
comparisons passed**: 925 keys, 4,197 finite complex
values, zero strict per-value failures and zero comparison CG solves. The four
existing CORR deferrals remain intact. **no_1pt remains experimental; devel is
the baseline.** This is a separate full experimental sweep following the
[merged devel sweep](arb-native-regressions.md), not a promotion or a combined
invocation. Together the two new sweeps cover 30 active cases per chain,
including the direct-DISCO nucleon case; the historical 29-case matrix remains
separate evidence.

## Tools, settings and data

The run reused retained experimental format-4 graph tools, native NPT with the
DISCO mass reader, and corrected pre-YLM Chroma with direct-DISCO support.
Their hashes matched the retained artifacts recorded alongside the devel run
before execution and were rechecked after completion. No experimental source
rebuild is claimed. Historical build/link records and executable hashes are
saved in the [machine-readable record](no1pt-native-regressions.json).
Historical source paths in configuration/link logs are not assertions about
those checkouts' current branch heads.

ADAT provenance is incremental: experimental NPT links a Clang archive based on
the installed ADAT `devel`, with graph-codec objects compiled from
`adat/devel-rge-no_1pt` (`corr_graph`, `hadron_corr_util` and `process_corrs`).
Experimental Chroma links the retained experimental ADAT snapshot. The devel
chain and shared native-data tools use ADAT devel. These are recorded artifact
builds, not fresh builds of the current branch tips.

NPT uses Apple Clang/libomp; Chroma uses GCC/libgomp in a separate process.
Neither executable links both OpenMP runtimes. Execution used one worker.
The numerical tool qualification remains corrected pre-YLM CPU snapshots,
not a clean latest-YLM, MPI or GPU build.

All graphs were regenerated with the experimental generator and independently
confirmed as format 4. They were consumed only by matching experimental NPT and
CORR tools. `average_1pt_diagrams=false` was explicit in the graph, NPT and CORR
inputs; it limits one-point averaging rather than discarding one-point pieces.
NPT/CORR vector count, time origin and zero-unsmeared settings matched, including
the intentional two-vector pion_3pt setting. Fake data was disabled.

The primary collection is `runs/native-superb-rsd14-20261101-001/`, with MOD64
color vectors, per-mass native-double tensors, RsdCG=1e-14 and meson momentum
coverage through mom2=4. The direct one-file supplement is
`data/disco-native-direct-20261101-001/`. Dataset, generation-input and payload
hashes, gauge/RNG, lattice, coverage and solver accuracy were validated. The
primary and supplemental data hashes exactly match those used in the full
merged devel sweep. Original data/manifests and historical generation records
were not modified; these are not newly published public-release payloads.

## Paired numerical results

Independent key/value exports verified exact expected key coverage, matching
one-configuration/time shapes and full finite complex readback. A second audit
recomputed every per-value gate and checked input settings, format 4, zero CG
solves and tool/data hashes. The unchanged gate is:

```text
abs(NPT-CORR) <= 1e-9 * max(abs(NPT),abs(CORR))
                + 1e-12 * max(reference_global_max,1e-30)
```

| Case | Keys | Complex values | Maximum absolute difference |
| --- | ---: | ---: | ---: |
| pion | 3 | 48 | 9.04113e-15 |
| 1pt | 3 | 48 | 8.61689e-18 |
| 33 | 1 | 16 | 5.78008e-15 |
| 3pi | 3 | 48 | 7.60541e-14 |
| a0.d3 | 324 | 1296 | 4.62705e-20 |
| a1_rhopi | 1 | 16 | 3.43318e-15 |
| d | 1 | 16 | 3.46945e-16 |
| delta_J1o2m | 1 | 16 | 8.41475e-17 |
| eta8eta8_F8 | 1 | 16 | 1.42025e-15 |
| eta_eta_3pt | 1 | 16 | 0 |
| h8 | 4 | 64 | 2.16364e-14 |
| hard.1_tslice.ini | 529 | 2116 | 2.78053e-19 |
| nuc | 1 | 16 | 2.22045e-16 |
| nuc.p100 | 2 | 14 | 2.1207e-16 |
| nuc_gA | 1 | 7 | 1.47647e-17 |
| nuc_nuc_3pt | 1 | 7 | 3.83213e-17 |
| nuc_nuc_ax_3pt | 4 | 28 | 8.55352e-17 |
| nuc_nuc_proj_3pt | 1 | 7 | 2.75774e-19 |
| nucnuc_small | 2 | 8 | 7.70782e-17 |
| nucpi | 1 | 16 | 3.54718e-17 |
| nucpi_I3o2 | 1 | 16 | 4.9096e-17 |
| nucpi_J1o2m | 1 | 16 | 2.52032e-17 |
| nucpi_nucpi_J1o2m | 2 | 32 | 4.06143e-15 |
| pi | 1 | 16 | 1.26001e-15 |
| pi_pi_3pt | 1 | 6 | 2.93266e-16 |
| pion_3pt | 1 | 7 | 3.01842e-16 |
| pipi_i1 | 1 | 16 | 2.78402e-15 |
| psi | 2 | 32 | 4.01209e-15 |
| rho | 3 | 48 | 1.24409e-14 |
| rho_rho_3pt | 27 | 189 | 6.27109e-16 |

Maximum absolute difference over this experimental suite:
7.6054098295145702e-14. The relative-only dbutil comparison is retained as a
separate diagnostic, not a replacement for the strict gate. No tolerance was
changed and no channels were discarded. Exactly zero-valued channel counts:
eta_eta_3pt (NPT 1, CORR 1). The eta_eta_3pt control has its expected key count,
exactly zero graphs and exactly zero values; it is not a positive channel.

Of the 29 experimental NPT outputs available from the historical
matrix, 29 are byte-identical to the new outputs.
The reopened nuc_nuc_3pt is now included in this full experimental sweep, rather
than only its earlier targeted check. This compares NPT against CORR within the
experimental chain; it does not assert a new full per-value experimental/devel
cross-chain equivalence test. Existing baselines were not overwritten.

## Preserved deferrals and separate NPT checks

[The policy](regression-policy.json) is unchanged: ff_3pt stays deferred in both
NPT and CORR, while fsq_3pt, glue and tetra_F27_S2 stay deferred in CORR. Their
absence is explicit, not a passing implementation claim.

Separate experimental NPT-only checks passed fsq_3pt (two keys/32 values), glue
(one key/16 values) and tetra_F27_S2 (three keys/48 values): six keys and 96 finite
complex values in total, with no exactly zero-valued channels. An independent
audit rechecked keys, shapes, finite readback and hashes. This is NPT coverage,
not CORR support. fsq_3pt retains the authorized legacy gpdf_2_0.00.sdb exception;
it is not regenerated native-double data.

## Evidence and limits

- `runs/no1pt-native-validation-20261103-001/`: exact command JSONs, provenance,
  historical build records, library inspection, launch logs and audit script.
- `runs/no1pt-native-full-20261103-001/results.json`: full paired report;
  `independent-audit.json` records the second complete numerical/hash audit.
- `runs/no1pt-native-npt-only-20261103-001/results.json`: separate NPT-only
  coverage and its independent audit.

The exact commands are embedded in the JSON record. The full command selects
`--chain no_1pt`, omits `--cases`, and passes `--disco-dataset` explicitly. The
current CLI requires devel executable arguments too, but they were not executed
in this experimental-only run. The runner uses a 900-second per-executable
timeout and 8192-MiB RSS cap with child-process inspection. Every attempt gets a
fresh output directory. Generated tensors, graph/correlator binaries and logs
remain Git-ignored; prior successful runs and failures remain separate.

Saved tensors supplied every comparison, so the zero-solve result does not
validate on-demand GenProp generation. This run does not validate experimental
full-lattice one-point averaging (`average_1pt_diagrams=true`), deferred CORR
implementations, displaced-current correlators, clean latest-YLM, MPI/GPU, or
ensemble physics. See [coverage](regressions.md) and [DISCO scope](disconnected-loops.md).
