# Numerical baseline inventory

- `tools.toml`: local executable paths; edit this file when switching builds.
- `tools.example.toml`: portable starting point for a development build.
- `tests.toml`: active passing tests plus explicit exclusions and their reasons.
- `<xml-stem>/output.sdb1`: read-only local baseline (ignored by Git).
- `<xml-stem>/baseline.json`: baseline hash, validation counts and provenance.

Run `python3 scripts/run_regressions.py` from the checkout root, using Python
3.11+ or Python 3.9/3.10 with `tomli`. A single explicit XML path or `--list`
selects a subset. `--tools` selects another executable-path TOML independently.
List XML names resolve inside `test_inputs`; paths in tools TOML resolve from
that TOML file's directory. Input names retain intermediate dots.

Combined XMLs are development fixtures: corr_graph uses NPointList; npt uses
ColorVec. Use separate purpose-specific XMLs in production. The runner's graph
and numerical stages share command/output conventions with run_colorvec.csh.

Baselines are generated only by explicit `--establish`, never by comparison.
Preserve their original run directories. A clone contains metadata and test
names, not the ignored SDB payloads; restore trusted baseline bytes with the
recorded hashes before comparing. Do not substitute an unreviewed new run for
a missing reference or call self-comparison an independent historical check.

## Establishment, October 31, 2026

All 39 `RedstarNPt` XMLs were attempted with four threads, 120 seconds per
executable and an 8192 MiB per-process RSS cap, using the matching Apple
Clang/libomp Redstar/ADAT stack recorded in `toolchain-provenance.json`.

| Outcome | Count |
| --- | ---: |
| Real-data baselines | 33 |
| Retained fake-data snapshots; inactive after failed reproduction | 2 |
| Exact symmetry-zero control (`eta_eta_3pt`) | 1 |
| Failed; no baseline and no test-list entry | 3 |

`a1.000_T1pM.xml` hit the 8192 MiB memory cap (8463360 KiB observed RSS).
`da_3pt.xml` and `kpi_3pt.xml` could not find the required forward/backward GenProp4
keys in the immutable dataset. Their exact missing key definitions and all
per-case coverage, finite-value and shape results are recorded in
[establishment.json](establishment.json). No positive case contained a zero-valued
correlator key; the symmetry-zero control had exactly its one required zero key.
All 36 saved SDB snapshots were checked to be regular read-only files matching their
TOML SHA-256 pins. The complete initial suite is preserved at
`runs/validation-20261031-151322-ma_m7fjx/`; its nonzero exit status records the
three failures rather than masking them with the passing-list result.

Eight other XMLs (GenerateXML/OpsList schemas) are not RedstarNPt numerical inputs
and were not executed by this sweep. Establishment uses independent readback and
self-comparison to validate the saved database, not an independent prior physics
reference. Subsequent fresh runs against the saved baselines test reproducibility.

## Reproducibility check

The second, fresh 36-case run found that `pion_DA.xml` and `pion_pdf_3pt.xml`
failed numerical comparison (relative Frobenius errors 1.49047 and 1.34612).
Both omit `fake_data_seed`; their numerical logs explicitly report a seed based
on the current time. ColorVec defaults the missing seed to -1 and uses a clock
seed in that mode. Their exact keys, shapes and finite values passed, but the
numbers are not reproducible. Their original snapshots and failed comparisons
are preserved; `baseline.json` marks them inactive. Their XMLs were not changed.

The active TOML list therefore contains **34** cases: 33 real-data cases and the
one exact zero control. All five exclusions (these two plus the three original
failures) appear explicitly under `[[excluded]]` in the same TOML file. Normal
runs use only `[[tests]]`; passing a single XML or `--all` still attempts excluded
inputs and reports failures. New establishment refuses to promote time-seeded
fake data. Explicit exclusions survive future list updates, and successful
promotion of a formerly excluded case removes its exclusion.

All **34 active cases passed** the fresh numerical comparison at `1e-12`; the
maximum reported relative error for active cases was zero. The complete repeat
attempt (`runs/validation-20261031-152328-5ava3owl/`) correctly returned nonzero
for the two fake-data mismatches. [verification.json](verification.json) retains
that full-attempt result separately from the 34-case active-list result, so the
failures remain visible. The single-XML command was also tested successfully
with `test_inputs/nuc.p100.xml`. All 40 Python regression/unit tests passed with
the TOML-capable Python runtime.

## Separate graph and numerical inputs

The [4³×16 split contraction workflows](CONTRACTIONS.md) provide three entry
points: graph only, graph then Redstar npt, and graph then vanilla Chroma
CORR_SUPERB. Cases live separately under `regressions/redstar/` and
`regressions/corr_superb/`, preserving the existing combined-input inventory.
