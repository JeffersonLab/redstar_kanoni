# Split contraction workflow validation — 1 November 2026

| Check | Observed result |
| --- | --- |
| Python unit/regression tests | 48 passed |
| Fresh split graph + Redstar npt runs | All 34 active cases passed against their existing checksum-pinned references |
| Redstar symmetry-zero control | Preserved as the one explicit zero control |
| Nπ graph-only runs | Full 81- and 729-correlator cases passed; format 3, 4³×16 |
| Shared vanilla Chroma job | Fresh color vectors then CORR_SUPERB, moving-frame Nπ, 729 correlators |
| Chroma readback | 5,103 finite complex samples, no zero channels, complete 27×27 matrix |
| Maximum absolute Chroma/reference difference | 0 |
| Exporter compilation | Installed Clang/libomp and GCC/libgomp ADAT stacks both passed |

See [commands and layout](CONTRACTIONS.md) and
[machine-readable results](contractions-validation.json). Redstar verification
is preserved under `runs/split-redstar-20261101-001`; the pion case has its own
`runs/split-redstar-pion-20261101-001` directory. The shared Chroma job is under
`runs/split-corr-superb-20261101-001`. The pure graph checks are preserved under
`runs/split-graph-npi-{rest,moving}-20261101-001`.

The Redstar sweep requested two workers, except the initial pion check which
used four. The fresh Chroma job used one worker and a 6 GiB contraction budget.
All BLAS limits were one worker. Exact commands, input/reference/tool hashes,
prepared XMLs, graph binaries, final SDBs and independent exports remain with
the run evidence. No existing baseline was overwritten or newly promoted.

The rest-frame CORR_SUPERB case retains its previously accepted compact devel
reference and passed fresh graph generation; its combined Chroma job was not
rerun during this workflow check. The moving case verifies the shared combined
Chroma setup against its independently saved earlier two-job result. These are
single-configuration software checks and do not establish cross-backend physics
agreement. `no_1pt` remains experimental; the separately running original
12³×16 comparison is not being reported as passed here.
