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

The canonical input now declares the complete `<mass_labels>` dictionary in
each measurement and uses the same `<sdb_file>disco.sdb</sdb_file>` throughout.
The producer creates the native mass-axis database on its first measurement,
then appends each complete mass/time packet directly, including every requested
z path and gamma component. **No temporary shards or packing step are used.**

Run the canonical input in a fresh working directory:

```sh
/path/to/chroma -i /path/to/chroma_inputs/superb-double/disco.probing.ini.xml -o disco.out.xml
```

The first write reserves the filename exclusively. A new process refuses an
existing output; appends are limited to the collection created by that run.
Checks reject duplicate mass/time packets, changed lattice/mass/path/momentum
coverage, changed collection settings, changed actions within a mass label,
and incomplete or nonfinite gamma vectors. Every packet closes the database
and flushes its block checksums before the next measurement.

The collection contract records the declared gauge object/update and gauge
metadata plus mass/time-independent settings. Original input XML remains the
complete specification of all mass/time measurements. The historical packed
collection and its provenance remain available as earlier evidence.
`scripts/pack_disco.cc` is retained only as a migration utility for older shard
outputs; it is not part of the canonical generation workflow.

The direct 4³×16 run is validated. Historical packed data and earlier reports
remain separate; the results below describe direct producer output.

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

The subsequent [full merged-devel native-double suite](arb-native-regressions.md)
includes a passing `nuc_nuc_3pt` comparison using this same direct collection,
as part of a new 30-case devel sweep. The targeted two-chain evidence below
remains separate; experimental no_1pt was not rerun in that full sweep.

The canonical Chroma input produced exactly **one `disco.sdb`**, without shards
or a packing operation. All 32 mass/time measurements and 6,144 CG solves
completed. Independent checks passed for all 224 unique keys, 3,584 finite
complex<double> values and every block checksum.

The direct output agrees with the previously validated collection under the
unchanged strict per-value gate: maximum absolute difference
0, with
0 nonidentical values.
Its local collection is `data/disco-native-direct-20261101-001/`; the
[checked manifest](../test_inputs/native-disco-z3-manifest.json) records the
executed input and payload hashes. This is not a new public payload release.

`nuc_nuc_3pt` passed NPT versus CORR_SUPERB on both chains: one key, all seven
time samples per chain, zero failed numerical gates and zero comparison CG
solves. Maximum absolute differences:

| Chain | Maximum absolute difference |
|---|---:|
| devel baseline | 4.1777673608052095e-17 |
| experimental no_1pt | 3.8321294114307615e-17 |

Pion also passed on both chains (three keys, 48 values per chain), making four
fresh case/chain checks and 110 finite compared values. Missing-DISCO inputs
were rejected explicitly on both chains. Earlier pion/axial-nucleon/rho controls
remain separate passing evidence, not a new full-suite claim.

Direct-writer tests cover earlier-block preservation, separate mass/time keys,
duplicate packets, incompatible settings/actions/path coverage, incomplete data
and refusal to overwrite a pre-existing file. A cached-data I/O test also wrote
all 32 packets through the actual append API and reproduced all values exactly.
All 67 Kanoni workflow tests pass, including direct recipe coverage and native
`.sdb` inspector/mass-dictionary routing.

The nucleon regression uses a local current. Nonzero z paths are generated,
checksum-checked and read back; separate displaced-current correlator
comparisons are not claimed here. Full evidence is saved under
`runs/disco-native-direct-20261101-001/` and
`runs/disco-direct-checks-20261101-001/`.

The direct database is 84,424 bytes. Payloads and numerical
runs stay Git-ignored; immutable kanoni-v1 and previous candidates are preserved.
Numerical builds remain incremental corrected pre-YLM serial CPU snapshots;
these checks do not establish clean latest-YLM, MPI or GPU validation.
