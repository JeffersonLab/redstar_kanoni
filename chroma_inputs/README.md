# Native-double 4³×16 dataset recipes

`original/` preserves the supplied Chroma/Harom XML and its checksums. `superb-double/` is the native SUPERB recipe; `double/` retains the legacy-SDB output alternative. The validated candidate uses the original WEAK_FIELD/RNG, ten MOD64 color vectors and **RsdCG=1e-14** for propagator and GenProp solves. No gauge.mod is required. colorvec.lime is the native QIO bridge for glue elementals.

The combined PROP_AND_MATELEM_DISTILLATION_SUPERB task generates perambulators directly; the vanilla combined-task alternative is retained. Native storage uses **one file per mass**, prop-U0.05.sbt, prop-U0.1.sbt and prop-U0.2.sbt; sharing one native output filename between masses overwrites earlier data. GenProp5 has separate U0.05/U0.1 files and the required wrapped source/sink coverage. Meson and baryon coverage includes all 16 times. Meson input has mom2_min=0, mom2_max=4 and an empty mom_list, producing every momentum in the sphere (33 momenta, 121 paths, 6,388,800 finite values).

## Validation and provenance

All regenerated native tensors passed payload-type, block-checksum and full finite readback. The final RsdCG=1e-14 matrix passed 29 active cases on each chain, with five explicit CORR deferrals per chain. Separate NPT-only glue/tetra/fsq checks also passed on both chains. See [coverage](../docs/regressions.md), [three-point corrections](../docs/three-point-comparison.md), and [timings](../docs/regression-timings.md). NPT and CORR use the same stored tensors; all comparison Chroma jobs performed zero CG solves.

The checked numerical executables were incremental corrected pre-YLM snapshots (baseline Chroma ad9795af plus corrected ADAT), not clean latest-YLM builds. MPI/GPU and the full on-demand GenProp path are not validated by the cached-tensor matrix. Synthetic MOD tests cover exact 32-bit/64-bit/legacy-32 readback and classic mixed-precision rejection. Native tetra/glue payloads matched legacy payloads exactly; their CORR implementations remain deferred.

`test_inputs/native-superb-f64-manifest.json` pins the validated local candidate's filenames, sizes and SHA-256 values. Payloads and run directories are ignored by Git; this is not a declaration of a new public dataset release. The original kanoni-v1 manifest and installed old data remain unchanged. Fresh runs and baseline establishment must use separate destinations and actual supplied payloads, not aliases or implicit replacement of old references.

## Explicit legacy exception and retained failures

The user authorized retaining **gpdf_2_0.00.sdb** because its generator is unavailable. It remains pinned to kanoni-v1 and is not claimed as freshly generated native-double data. ff_3pt and its missing gpdf.more.sdb are deferred; that file is not added to the candidate. nuc_nuc_3pt has since passed its separate fresh-DISCO comparison on both chains; the previous matrix retains its historical deferral. See [DISCO details](../docs/disconnected-loops.md).

All old candidates and failed evidence remain separate, including early MOD ingestion/ABI failures, native-format/legacy-inspector mismatch, shared-filename overwrite, incomplete momentum coverage, and corrected three-point failures. Do not relabel historical failed reports or overwrite their inputs/outputs.

## Reproduce comparisons

Use the native recipes to generate a separate dataset and verify every tensor with the supplied storage/readback helpers. `scripts/compare_regression_chains.py --help` documents explicit executable and dataset paths; `--cases pion` selects a quick paired check. Include `--disco-dataset /path/to/validated-disco-collection` and omit case selection for the complete active inventory and use `--npt-only --cases glue tetra_F27_S2 fsq_3pt` for the separate NPT lanes. Supply the actual build qualification with `--qualification`; no personal executable path is embedded in the runner.

## Disconnected-loop recipe

`disco.probing.ini.xml` writes all masses, all 16 times and straight z paths
0, ±1, ±2, ±3 **directly into one `disco.sdb`**. Every measurement declares the
same `mass_labels` dictionary and the same output filename. No shard files or
packing step are part of this workflow. Run in a fresh directory: existing
files, duplicate mass/time entries and incompatible settings are rejected.

The native rank-5 `itdmf` tensor has an explicit mass dictionary. Readers also
accept older rank-4 native files and legacy FILEDB databases. `recipe.json`
includes the direct DISCO stage; the generator chooses native inspection from
`storage: SUPERB` even though its suffix is `.sdb`, and checks the mass dictionary.
The old packer is retained only for migrating historical shard outputs.

The direct collection `data/disco-native-direct-20261101-001/` passed full
readback and paired nuc_nuc_3pt/pion checks on both chains. Earlier packed data
and failed diagnostics remain separate. See
[direct DISCO generation and results](../docs/disconnected-loops.md).
