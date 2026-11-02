# Disconnected loops for nuc_nuc_3pt

Devel is the regression baseline. `no_1pt` is experimental and uses its own
matching graph generator and evaluator.

## Generation

The canonical input is
[`disco.probing.ini.xml`](../chroma_inputs/superb-double/disco.probing.ini.xml).
It selects `DISCO_PROBING_3D_DEFLATION_SUPERB`, implemented in
[Chroma's DISCO producer](https://github.com/JeffersonLab/chroma/blob/devel/lib/meas/inline/hadron/inline_disco_prob_3d_defl_superb_w.cc).
This is the gauge-transported implementation, rather than the old plain-shift
`DISCO` task.

The recipe uses the same 4³×16 WEAK_FIELD and RNG seed as the native-double
collection, CLOVER masses U0.05/U0.1, antiperiodic temporal fermion boundaries,
and RsdCG=1e-14. `max_path_length=3` produces straight z paths 0, ±1, ±2, ±3.
There is one zero momentum and all 16 DR gamma components at every time.
`use_ferm_state_links=false` selects the original gauge links for transport;
it does **not** disable gauge transport.

The recipe includes all 16 probing colors (`probing_distance=3`,
`probing_power=2`) with one noise vector. `NULL_PROJECTOR` disables optional
deflation, so generation needs neither color vectors nor a deflation database.
This is a software-validation sample, not a claim about stochastic or ensemble
precision.

The initial producer used continuous first-quadrant phases where it intended
Z4 noise. The correction quantizes the uniform sample into four phases before
forming the complex noise vector. Both Chroma source chains contain the
correction. The initial diagnostic output is retained separately and is not a
regression input.

## Native storage and consumers

The final collection contains **one `disco.sdb`**, with both mass labels, all
16 times, all seven z paths and all 16 gamma components. Its native tensor
order is `itdmf` (gamma, time, displacement, momentum, mass), with an explicit
`mass_labels` dictionary. This is 224 keys and 3,584 complex<double> values.

The current Chroma producer writes a native file per mass/time measurement.
Those 32 files are temporary shards, not the final collection. A shared native
filename in that producer would overwrite earlier measurements. The
[`pack_disco` helper](../scripts/pack_disco.cc) collects the shards into the
single database and checks every packed value against its source exactly.
Complete original metadata is retained losslessly in `source_metadata_hex`;
the executed input and manifest provide readable generation provenance.

To regenerate in a fresh working directory, build the helper with the matching
ADAT compiler/ABI using `scripts/build_disco_packer.py --help`, run the canonical
Chroma input, then run:

```sh
/path/to/pack_disco /path/to/new/disco.sdb disco-U*.sbt
```

The helper refuses an existing output. Keep shards in the generation working
directory; the final data collection contains only the consolidated database,
its manifest and the executed input. Do not point a producer at the immutable
public dataset or overwrite an old reference.

`ADATIO::StorageDisco` reads multi-mass rank-5 tensors, older single-mass rank-4 tensors, and legacy FILEDB DISCO databases.
ColorVec's NPT disconnected operator now uses that dual-format reader. Missing
sparse time blocks and out-of-range times cannot wrap into valid entries;
all 16 gamma values must be present and finite in a native read.

CORR_SUPERB accepts an optional `<discos><elem>...</elem></discos>` file list.
Its disconnected callback supplies the stored 16-gamma block. The evaluator
forms a scalar loop factor using the same DR coefficients, flavor-to-mass map,
creation/annihilation momentum signs and fixed/moving time mapping as NPT,
then combines it with the parent diagram. It does not substitute a GenProp,
recompute stochastic loops, or silently replace missing data with zeros.
No graph wire-format change is involved.

## Reproduce the comparison

Use `scripts/compare_regression_chains.py` with the usual explicit tool paths,
`--dataset /path/to/native-superb-rsd14`,
`--disco-dataset /path/to/disco-native-z3`, and `--cases nuc_nuc_3pt`.
The supplemental directory must contain its validated `dataset-manifest.json`,
`generation-input.xml`, and the single `disco.sdb` payload. The runner checks the gauge/RNG,
solver accuracy, coverage and checksums, then records the actual input/tool
hashes and passes identical loop files to both chains.

Each comparison must retain exact correlator keys and time shapes, complete
finite readback, and the existing per-value gate: relative tolerance 1e-9 plus
1e-12 times max(reference_global_max,1e-30). The relative-only dbutil diagnostic
is retained separately.

## Validation results

The full collection passed block checksums and independent native-reader
readback: **one database, 224 unique keys, 3,584 finite complex values**.
The saved local collection is `data/disco-native-z3-packed-20261101-003/`; its
[checked manifest](../test_inputs/native-disco-z3-manifest.json) is a local
candidate record, not a public dataset release.

`nuc_nuc_3pt` passed NPT versus CORR_SUPERB on both chains: one correlator,
all seven time samples each, zero failed per-value gates and zero CG solves
in the comparison jobs. Maximum absolute differences were:

| Chain | Maximum absolute difference |
|---|---:|
| devel baseline | 4.1777673608052095e-17 |
| experimental no_1pt | 3.8321294114307615e-17 |

Both chains also passed pion, axial-nucleon and rho three-point controls
(six case/chain comparisons, 530 finite values). Reader tests cover sparse
multi-file lookup and missing/out-of-range keys; callback tests cover fixed
and moving times, wraparound, flavor/momentum conventions, missing callbacks,
and incomplete/nonfinite gamma vectors. Both Chroma chains reject a missing
DISCO input explicitly. All 64 Kanoni workflow tests pass.

The nucleon regression uses a local current. Nonzero z paths are generated,
checksum-checked and read back, but are not claimed as separate displaced-current
correlator comparisons. Detailed numerical evidence is saved under
`runs/disco-nuc-checks-20261101-002/`; control evidence is under
`runs/disco-callback-controls-20261101-001/`.

Payloads and numerical reports remain in Git-ignored collection/run directories.
The immutable public kanoni-v1 dataset and older native candidates are unchanged.
The numerical builds are incremental corrected pre-YLM serial CPU snapshots;
these checks do not establish clean latest-YLM, MPI or GPU validation.

The saved single database is approximately 186 KiB (190,216 bytes). Packing copies
existing values exactly and does not repeat the Chroma solves.
