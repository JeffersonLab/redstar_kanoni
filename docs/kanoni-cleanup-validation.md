# Kanoni devel runner and data cleanup validation

10 November 2026. The requested historical documentation was committed separately:
`bf113b2` (ADAT branch provenance), `ffa33dc` (historical datalib design/inventory),
and `d6d9028` (historical serial/graph/storage checkpoints). These checks validate
the subsequent cleanup on devel.

## Resulting behavior

- Redstar and Chroma runners require an explicitly selected absolute bin
  directory: `REDSTAR_BIN` / `CHROMA_BIN`, equivalent CLI directory options, or
  absolute `redstar_bin` / `chroma_bin` entries in an explicit tool TOML. CLI
  wins over environment, then TOML. PATH searches, sibling-build fallbacks,
  the old `CHROMA` variable and individual Redstar/Chroma executable overrides
  are removed. Auxiliary tools retain their explicit options.
- The paired-chain runner uses `--baseline-redstar-bin`,
  `--baseline-chroma-bin`, `--feature-redstar-bin`, and `--feature-chroma-bin`.
  Only selected chains need directories; `REDSTAR_BIN` / `CHROMA_BIN` can supply
  them. Choose separate compatible stacks when running both graph formats.
- `run_colorvec` writes only outputs under `runs/<name>/`. The selected original
  XML, prepared XML and only declared projected-weight snapshots are preserved
  under ignored `run_inputs/<same-name>/`. `run.json` records input paths/hashes.
  No unrelated XML, list, data file or input directory is copied into the run.
- The checksum-pinned historical `colorvec.mod` and matching `gauge.mod` already
  live as regular read-only files in `data/`; their bytes are unchanged. Archived
  native-double collections remain separate, with their original provenance.
- Exactly the two requested local SDB files were removed: the long
  `hada_0-511_SVD_disco_cfg_cl21_32_64_b6p3_m0p2390_m0p2050_cfg_1000.ref0001.sdb`
  and `peram.only0.sdb`. Their sizes/hashes were verified before removal.
  `test_inputs/data-policy.json` excludes them from future setup. The immutable
  18-entry release manifest and public release are unchanged. Setup now verifies
  16 active payloads; both initial and repeated setup passed without restoring
  the retired files.
- `.gitignore` ignores `.DS_Store` at every depth. The existing Finder file is
  preserved byte for byte. Existing machine-local TOML files are also preserved;
  migrate any obsolete per-executable overrides before reuse.

## Validation

| Check | Result |
| --- | --- |
| Required standard Python 3.9 unittest command | 71 tests, passed; seven optional TOML tests skipped |
| Python 3.13 full unittest command | 71 tests passed, no skips |
| Fresh output-only run_colorvec pion and pipi_i1 | Passed; each has only generated outputs and no input XML/weights |
| Independent comparison of those exact runner databases | Passed; 4 keys / 64 finite values; both databases byte-identical to accepted references |
| Fresh devel independent pion / pipi_i1 / eta_eta_3pt validation | Two positive cases passed plus exact symmetry-zero control; 5 keys / 80 finite values total |
| Standalone devel Nπ CORR_SUPERB | Passed; 81 keys / 567 finite values; complete 9×9 matrix; no zero channels |
| Native-double cached pion / pion_3pt NPT/CORR smoke | Both passed; 4 keys / 55 finite values; zero CG solves and strict failures |
| Setup, MOD checksums, syntax, CLI help and git diff --check | Passed |

The standalone Nπ job uses its historical generated-vector template with the
format-3 devel graph, one requested OpenMP worker and the established default 6 GiB contraction
budget / 1800-second timeout. The first 2 GiB / 600-second attempt timed out
during propagator computation; its failed evidence is preserved. Its staged
graph and Chroma XML inputs match the passing retry byte for byte.
Its GCC/libgomp Chroma and Clang/libomp Redstar/exporter execute in separate
processes. No process mixes those runtimes. The fresh devel NPT checks request
two OpenMP workers. The recorded native smoke uses the existing reorg format-4
Redstar and fresh MPI/parscalar Chroma binaries at one MPI rank, with one requested
OpenMP worker per process, a 2 GiB planner budget, 1 GiB CPU cache and 8 GiB RSS
limit. Maximum native paired absolute difference: `9.041133121840199e-15`. These runs do not
constitute new source builds or a repeated full native suite. No multi-rank,
GPU, scaling or general on-demand GenProp qualification is added.

The first independent devel attempt was blocked because the sandbox denied
`ps`, which enforces the existing RSS cap. Its failed evidence is retained. A
fresh permission-enabled attempt passed without weakening the limits. All
accepted references, strict numerical gates, physics controls and declared
regression deferrals are preserved.

## Evidence

The [compact machine-readable report](kanoni-cleanup-validation.json) records
source/tool hashes, exact paths, comparisons, retired-file hashes, qualifications
and evidence hashes. Full local evidence remains under
`runs/kanoni-cleanup-20261110-001/`; the independent devel rerun is
`runs/validation-20261110-174414-mdu9ebke/`. Each output-only runner's prepared
inputs remain under its matching `run_inputs/` directory. Keep those selected
input snapshots with successful outputs when archiving a run.
