# Three-point NPT / CORR_SUPERB comparison investigation

The baseline remains **devel**; **no_1pt is experimental**. No numerical tolerance was relaxed. Historical failed runs and the original dataset are retained.

## Confirmed causes

1. **Reversed GenProp lookup in Chroma.** NPT falls back to the reversed source/sink tensor, reverses displacement and momentum, and applies gamma-five hermiticity and its gamma/momentum phase. CORR_SUPERB lacked this stored-tensor fallback. The baseline callback also clipped to an oriented time interval before lookup, dropping valid reversed-line contributions. Both Chroma chains now use the shorter unoriented interval and perform the reversed lookup. Changes are local and await complete validation.
2. **Comparison harness eigenvector count.** `pion_3pt` requests two vectors in NPT, but the matrix harness supplied ten to CORR_SUPERB. The harness now copies the numerical input's `ColorVec/Param/num_vecs`; physics inputs remain unchanged.

## Isolated checks on the unchanged RsdCG=1e-12 data

| Case | devel | experimental no_1pt | Maximum absolute difference |
|---|---|---|---|
| pi_pi_3pt | passed | passed | 2.663806906600181e-13 |
| pion_3pt, matching two-vector truncation | passed | passed | 2.629355070669928e-13 |
| rho_rho_3pt | strict comparison still fails | strict comparison still fails | 8.42491780344247e-9 / 1.7978965390235732e-5 |

The large rho_rho mismatch was substantially reduced, but its remaining discrepancy is unresolved. Diagnostic decomposition into insertion-containing and fully smeared diagrams preserves all 27 output keys and is not a substitute regression.

Evidence is in `runs/threepoint-reverse-devel-20261101-001`, `runs/threepoint-reverse-devel-20261101-002`, `runs/threepoint-reverse-no_1pt-20261101-002`, and `runs/rho-threepoint-split-probe-20261101-001`. The earlier stored-versus-recomputed and on-demand probes also failed; these remain evidence requiring follow-up, not passing checks.

## Tighter-accuracy candidate

The user approved **RsdCG=1e-14** for propagators and GenProp solves and deferred `nuc_nuc_3pt` disconnected-loop work. The separate candidate `runs/native-superb-rsd14-20261101-001` has generated all three propagator masses and both GenProp masses and passed full tensor readback. It reuses independently validated gauge/eigenvectors and elementals, with the meson sphere set to mom2_min=0, mom2_max=4 and an empty mom_list. The old candidate is unchanged. Paired focused comparisons are tracked in `runs/rsd14-focused-comparisons-20261101-001/results.json`.

The numerical executable is an incremental corrected pre-YLM Chroma snapshot, not a clean build of the latest YLM checkout. No code is committed or published on the strength of incomplete or failed checks.

## RsdCG=1e-14 focused results

Both chains pass pi_pi_3pt (max 2.9326576526939265e-16), matching-rank pion_3pt (3.0184188481996443e-16), and eta8eta8_F8 (1.4202500883305642e-15). The full rho_rho_3pt case still fails all 189 strict per-value checks: devel max 8.424917742158808e-9; experimental max 1.1006625952225617e-5. Tighter solves therefore do not resolve the rho residual.

The first decomposition did not produce a nontrivial fully smeared control: all 84,882 diagrams contain the insertion, and the fully smeared subset has zero diagrams. Its zero outputs are not a positive regression result. Rewriting the equivalent insertion graph leaves NPT values unchanged to 5.56e-17 but changes CORR_SUPERB values by up to 1.7934133330524974e-5. This points to an ordering-dependent CORR_SUPERB issue; the precise cause is not yet established. Fresh one-diagram and one-correlator diagnostics are tracked under runs/rho-threepoint-selected-probe-20261101-001.

## Diagonal GenProp correction validated

The remaining rho discrepancy was localized to a product containing an insertion with equal GenProp source and sink times. These diagonal tensors retain every insertion time; treating them as a zero-length interval discarded valid values. Both callbacks now exempt equal endpoints from interval clipping. Full rho_rho_3pt comparisons on the RsdCG=1e-14 dataset pass all 189 values on both chains: devel maximum difference 6.084010900123129e-16; experimental no_1pt 6.271086192402129e-16. Earlier failures remain saved. The full matched sweep with these v11 executables is tracked in runs/native-comparison-matrix-20261101-004/results.json; commits await that sweep and remaining source checks.

## Final full sweep

Matrix 004 passed all 58 active case/chain pairs (29 cases on each chain), with 10 explicit case/chain deferrals. Independent audit verified expected key/time coverage, 8,380 finite compared values, zero strict failures, executable hashes, and zero CG solves. Timing details are in [regression-timings.md](regression-timings.md). Final source review and commit preparation follow; no claim of publication is made here.
