# Summary of redstar/chroma code devel

Updated 3 November 2026 from repository documentation, saved validation records and current local runs.

Canonical home: redstar_kanoni `devel`, `docs/development-summary.md`. Devel is the regression baseline; no_1pt remains experimental.

The main achievement is a documented, reproducible route from continuum operators through contraction graphs and numerical correlator databases to matrix-element fits. The regression baseline is the **devel chain**, with the fitting repositories on their established main/master branches. The experimental `no_1pt` work and the proposed all-YLM vertex migration are separate from that baseline.

## ARB merged into Redstar devel

On 3 November 2026, the clean local `redstar.devel` checkout fast-forwarded to
validated merge `b194fdf`. It combines ARB memory auditing and the three-hadron
momentum-class independence fix with devel's data workflows and baryon metadata.
A fresh Redstar build using existing Apple Clang/libomp dependencies passed
targeted checks and eight legacy-SDB regressions: 39 keys and 354 finite complex
values, with every database byte-identical to its saved devel baseline.
The exact-zero control is included separately. This is local integration,
not a push or a repeated full native-double matrix; Linux memory measurements,
jemalloc dumps and MPI/GPU remain untested. See the [build and validation
record](arb-merge-validation.md) for source/tool hashes, operator-basis changes
and retained evidence. no_1pt remains experimental.

## Requested next work: publication and production integration

Recorded 1 November 2026 at the user's request. These are planned tasks, not
completed migrations; the current baseline and experimental qualifications below
remain in force until the implementation and validation are complete.

- [ ] Prepare a paper and a coordinated public code release before merging the
  branch families. Establish the ADAT/datalib publication and dependency layout
  explicitly; pushing a branch to an access-controlled repository is not a public
  release.
- [ ] Bring the `no_1pt` work in Redstar, ColorVec and ADAT into the supported
  development baseline so it no longer needs the experimental designation.
  Coordinate the matching Chroma consumer, graph-format compatibility and
  regression evidence as part of that promotion.
- [ ] Integrate the `devel-rge-ylm` work into `devel` where it has not already
  been merged; check each repository's actual merge state first.
- [ ] Change the graph vertex representation to reuse the `deriv` tag for the
  specification of the derivative-part Y_lm present in that vertex. Elementals
  retain the full specification described by the `devel-rge-ylm` work.
- [ ] Obtain the user's remaining design details before implementing the vertex
  encoding. Define the precise tag contents, reader/writer changes, compatibility
  and migration procedure, and validate matched graph generators and consumers
  without weakening the numerical gate.

## 1. Experimental `no_1pt`: changed one-point behavior and graph compatibility

**Experimental; not the regression baseline.** On the `devel-rge-no_1pt` feature branches, `average_1pt_diagrams=false` disables full-lattice one-point averaging. Disconnected one-point pieces are still computed: fixed-source pieces once, and varying pieces within the parent correlator's requested time window. This avoids requiring annihilation data outside that window. Setting the flag true in Redstar expands one-point evaluation over the lattice and averages products for diagrams composed entirely of one-point pieces. Mixed diagrams retain their requested-time products.

This is a **breaking change to `corr_graph.bin`**: the experimental container is version 4, uses plain connected graph keys without the `Stich` wrapper, and rejects version 3. Old binaries must be regenerated with the matching generator. ADAT now owns the shared graph codec; consumers must be rebuilt together. Redstar input XML remains version 14.

The experimental Redstar tests cover sparse annihilation coverage, wraparound, multiple source times, and combined one-, two-, and three-particle bases. Canonicalizing one-point vertex labels also fixes sharing across source times. These feature tests do not replace the established devel regressions.

The matching experimental CORR_SUPERB interface requires an explicit averaging flag: false is accepted; true is currently rejected as unsupported. The corrected Nπ compact test now passes all 810 correlators and strict numerical comparison with the corrected devel chain. This validates the false setting for this case; true remains unsupported, and the original 12³ follow-up is tracked in the [run report](https://github.com/JeffersonLab/redstar/blob/devel/docs/roper/chroma/ORIGINAL12_RUN.md). See the [Nπ correction](https://github.com/JeffersonLab/redstar/blob/devel/docs/roper/chroma/NPI_FIX.md).

References: [Redstar one-point behavior](https://github.com/JeffersonLab/redstar/blob/devel-rge-no_1pt/docs/onept-time-windows.md), [multiparticle feature tests](https://github.com/JeffersonLab/redstar/blob/devel-rge-no_1pt/docs/multiparticle-onept-times.md), [shared ADAT format-4 codec](https://github.com/JeffersonLab/adat/blob/eloy/devel-rge-no_1pt/docs/corr-graph-v4.md), [experimental CORR_SUPERB flag](https://github.com/JeffersonLab/chroma/blob/devel-rge-no_1pt/docs/corr-superb-onept.md).

## Regression coverage: completed numerical comparison

All 29 active native-double regression cases pass against CORR_SUPERB on both
devel and experimental no_1pt: 58 case/chain comparisons and 8,380 finite values.
Five CORR cases per chain were deferred in that historical matrix. The user has
now completed the reopened nuc_nuc_3pt check with native DISCO data: both chains pass all seven values. This targeted addition brings recorded coverage to 30 active cases per chain; it is separate from the historical full sweep. The other four deferrals remain. See [DISCO validation](disconnected-loops.md) and [coverage](regressions.md).
The original 12³×16 Nπ comparison also passed all 81+729 keys and 5,670 values,
with maximum experimental/devel difference 1.11e-16. No tolerances were weakened.
The validated changes are committed; [regression coverage](regressions.md) records their scope and build qualification.

## Direct one-file DISCO generation

DISCO now writes all declared masses, times and z displacements directly to one
native database, with checked appends rather than temporary shards or a packing
step. The full weak-field run passed readback and agreed with the previous values
under the unchanged numerical gate; fresh nuc_nuc_3pt and pion comparisons pass on devel and experimental
no_1pt. [Direct DISCO details](disconnected-loops.md) record the guarded writer,
inputs, tests and build qualification. Historical packed data remain separate.

## New native-double 4³×16 dataset and storage work

The candidate uses the original WEAK_FIELD/RNG, ten native-double color vectors
and RsdCG=1e-14. The user selected SUPERB tensor storage throughout the elemental
pipeline; colorvec.mod remains the explicitly requested double MOD source.
Native propagators and GenProp5 use **one tensor file per mass**. Filename suffixes
are explicit .sbt; legacy dbutil does not inspect these tensor files. Native
inspection checks complex<double> payloads and native checksum/full finite
readback is required. No gauge.mod is needed.

The former hard-coded single-precision MOD readers now dispatch from metadata and
retain double buffers for 64-bit files. Synthetic exact-readback checks cover
32-bit, 64-bit and legacy 32-bit MODs. Classic and SUPERB propagator/generalized
propagator reader paths were updated. This is separate from changing graph format.

Tetraquark storage now has explicit vector/time/momentum/color axes. All 32 keys
and 320,000 complex values matched the legacy output exactly. The full
`tetra_F27_S2` NPT regression passed with three correlators / 48 finite values and
byte-identical output databases. The corresponding CORR_SUPERB callback remains
separate work.

Glue storage now has vector/time/displacement/momentum axes. Its full derivative
storage check covered 1,093 displacement choices, seven momenta, 122,416 keys and
1,224,160 finite values, all exactly matching legacy output. Native block checksums
also pass. The rebuilt ColorVec reader is wired in; the glue correlator check and
complete suite status are recorded separately.

The complete tighter-accuracy candidate passed native checksum/full finite
readback and the matched regression matrix. Direct stored-input pion checks
pass on both chains, and the separate on-demand pion two-point check passed.
Reversed-GenProp and diagonal-time fixes also make the meson three-point cases
pass, including all 189 rho_rho values. The old SDB dataset and references remain
separate. Failed attempts, including storage/inspector mismatch, per-mass
filename overwrite and the earlier three-point failures, are retained.
`gpdf_2_0.00.sdb` is an explicit user-authorized legacy exception because its
production input is unavailable; it is not claimed as freshly generated 64-bit data.

Chroma tests use an incremental rebuild of the recorded **pre-YLM** devel snapshot
(ad9795af with corrected backend), not a clean build of the latest YLM checkout.
Branch names alone do not remove that validation qualification.

See the [input recipes and dataset rebuild notes](../chroma_inputs/README.md),
[glue schema](https://github.com/JeffersonLab/chroma/blob/devel/docs/glue-superb.md)
and [tetraquark schema](https://github.com/JeffersonLab/chroma/blob/devel/docs/tetraquark-superb.md).
The schema guides describe the validated native formats; glue/tetraquark CORR_SUPERB implementation remains deferred.

## 2. Planned YLM integration: a separate forthcoming breaking change

The next planned step is to merge the YLM development into the working branch and convert **all graph vertices to YLM format**. CORR_SUPERB must be updated to consume that representation. This is expected to introduce **another incompatible `corr_graph.bin` change**; its final format/version and migration procedure remain to be defined.

Substantial groundwork already exists: coupled meson and baryon derivative elementals, explicit coupled-component descriptors, storage metadata, and reconstruction checks. Chroma's local `origin/devel` already contains the merge titled “Merge validated YLM additions into devel.” That producer-side work does not mean the all-vertex Redstar/CORR_SUPERB migration is complete. The meson guide explicitly identifies remaining reader integration work.

References: [Redstar YLM branch](https://github.com/JeffersonLab/redstar/tree/devel-rge-ylm), [ColorVec YLM branch](https://github.com/JeffersonLab/colorvec/tree/devel-rge-ylm), [Chroma meson YLM guide](https://github.com/JeffersonLab/chroma/blob/devel/tests/meson_ylm/README.md), [baryon YLM guide](https://github.com/JeffersonLab/chroma/blob/devel/tests/baryon_ylm/README.md), [YLM storage checks](https://github.com/JeffersonLab/chroma/blob/devel/tests/ylm_storage/README.md).

## 3. Documentation now covers the working pipeline

Redstar has a linked documentation index and executable-specific guides covering operator discovery, continuum-to-lattice subduction, one-/two-/three-hadron bases, spectrum selection, two-/three-point correlator selection, graph construction and inspection, numerical evaluation, and database diagnostics. Worked examples include a1, a0–omega, rho–rho, and the Roper/Nπ investigation. Additional guides cover phasing, projected-weight conversion, stored-operator extraction, and reproducible builds.

The fitter documentation now includes database-reader conventions, portable input files, replica generation, staged execution, expected kinematic coverage, dependency provenance, clean-build instructions, and a reconstruction/troubleshooting handoff. These documents distinguish generator spectrum rows from fitter spec-list rows and record explicit phasings and momentum conventions.

Start here: [Redstar documentation index](https://github.com/JeffersonLab/redstar/blob/devel/docs/README.md), [matelem_fitter overview](https://github.com/JeffersonLab/matelem_fitter/blob/main/README.md), [fitter example](https://github.com/JeffersonLab/matelem_fitter/blob/main/example/README.md), [reconstruction guide](https://github.com/JeffersonLab/matelem_fitter/blob/main/example/RECONSTRUCTION.md).

## 4. Continuum operators to final SDB correlators

### a1: completed Redstar numerical workflow

The a1 example starts with continuum operators, combines one-hadron, rho–pion, and three-pion operators, selects compatible lattice irreps, builds full source/sink matrices, constructs graphs, and evaluates them against real numerical databases.

| Irrep | Basis size | Final correlators | Unevaluatable graphs | Final database size |
| --- | ---: | ---: | ---: | ---: |
| `000_T1pM` | 6 | 36 | 0 | 18,916 bytes |
| `001_A2M` | 13 | 169 | 0 | 69,508 bytes |

Both runs completed on 27 October. Each saved output is `output.npt.sdb1`. Subsequent file-test diagnostics are documented, including NaN single-configuration uncertainties and a negative-diagonal warning for the rest-frame derivative operator. Successful numerical assembly does not establish ensemble statistics or physical fit quality.

References: [complete a1 workflow and results](https://github.com/JeffersonLab/redstar/blob/devel/docs/a1_workflow.md), [saved a1 inputs and outputs](https://github.com/JeffersonLab/redstar/tree/devel/docs/a1), [database diagnostic guide](https://github.com/JeffersonLab/redstar/blob/devel/docs/filetest_db.md).

### Nπ/Roper with CORR_SUPERB: corrected compact numerical workflow

The Roper example constructs one-particle and Nπ bases in `000_G1g` and `001_E1`, with intended full matrices of 81 and 729 correlators. The laptop trial generates ten color vectors and asks CORR_SUPERB to compute propagators on demand, starting with empty propagator/elemental database lists.

The recorded 30 October run generated the vectors and completed 20 CG solves, then failed in the SUPERB sparse baryon contraction backend: “Unsupported to an output tensor with dimensions both from the domain and the image on the sparse matrix.” **Neither final correlator SDB was produced by that historical run.** The follow-up fixes the sparse baryon coefficient layout, partial propagator batches on the feature branch, and a shared gather/scatter inconsistency in baryon slot permutations. The corrected **4³ × 16 compact contraction** retains the entire original L=12-selected basis and passes all 81 + 729 correlators, seven finite samples per key, independent database-key checks, and strict experimental-versus-devel numerical comparison. The small final **devel** SDBs are saved as regression references. The original 12³ × 16 numerical follow-up is tracked separately in the [run report](https://github.com/JeffersonLab/redstar/blob/devel/docs/roper/chroma/ORIGINAL12_RUN.md).

Saved evidence includes logs, a debugger stack, reconstruction instructions, and small generated eigenvector and baryon diagnostic SDBs with checksums. Those historical diagnostic databases are separate from the new [compact devel correlator references](https://github.com/JeffersonLab/redstar/blob/devel/docs/roper/chroma/compact-reference/README.md). See [correction, scope and reproduction](https://github.com/JeffersonLab/redstar/blob/devel/docs/roper/chroma/NPI_FIX.md).

References: [Roper operator workflow](https://github.com/JeffersonLab/redstar/blob/devel/docs/roper/README.md), [CORR_SUPERB trial and failure](https://github.com/JeffersonLab/redstar/blob/devel/docs/roper/chroma/README.md), [reconstruction](https://github.com/JeffersonLab/redstar/blob/devel/docs/roper/RECONSTRUCT.md), [retained data manifest](https://github.com/JeffersonLab/redstar/blob/devel/docs/roper/chroma/data-manifest.json).

## 5. rho–rho through matelem_fitter: all four form-factor coefficients exercised

The regression evidence covers the full workflow in two reproducible packages: Redstar performs operator selection, graph generation and numerical contraction; the fitter example starts from a small saved derived correlator database, generates replicas, and runs temporal and spatial fits. They share workflow provenance, but their correlator selections differ; the 83-key compact Redstar database is not the 135-key fitter fixture.

| Stage | Recorded coverage |
| --- | --- |
| Compact Redstar rho–rho | 31 temporal + 52 spatial correlators; 166 graphs; seven finite complex samples per key; zero unevaluatable graphs |
| Operator extraction | Five operator definitions checked against independently exported database keys |
| Fitter input fixture | 135 keys: 31 temporal + 104 spatial, including improvement-term channels |
| Replica generation | 1,000 synthetic samples per channel by default |
| Fits | 83 selected rows across seven kinematic classes |
| Final outputs | 28 finite complex output ensembles, each with 1,000 bins |
| Kinematic ranks | Moving/rest spatial systems rank 4, temporal systems rank 2, zero-transfer systems rank 1 |

The rank-4 spatial systems exercise **all four coefficients in the fitter's form-factor basis**. These are software regressions using synthetic replicas of one weak-field configuration and illustrative energies; some fits have poor chi-square. They are not physical form-factor measurements.

Important fixes supporting the regression include Redstar momentum matching through `referenceMom`, fitting_lib PAIC normalization to prevent underflow/NaNs, correct OpenMP worker counts including one-thread execution, and GNU static-library link ordering. Published fixes remove the need for local patches. Clean Linux/GCC/chromaform/OpenBLAS and macOS/Clang/libomp/Accelerate reproductions are documented.

References: [Redstar rho–rho runner](https://github.com/JeffersonLab/redstar/blob/devel/src/generate_all_3pt_spectrum/rho_rho/README.md), [saved contraction summaries](https://github.com/JeffersonLab/redstar/blob/devel/src/generate_all_3pt_spectrum/rho_rho/test_results/README.md), [full fitter example](https://github.com/JeffersonLab/matelem_fitter/blob/main/example/README.md), [expected coverage](https://github.com/JeffersonLab/matelem_fitter/blob/main/example/expected.json), [source/data provenance](https://github.com/JeffersonLab/matelem_fitter/blob/main/example/provenance.json).

### What is actually saved

- **Versioned fitter fixture:** [`rho.single.sdb`](https://github.com/JeffersonLab/matelem_fitter/blob/main/example/inputs/rho.single.sdb), approximately 43 KB, with a recorded checksum. It makes fit reproduction independent of the large raw contraction inputs.
- **Local Redstar contraction archive:** the rho–rho `test_results/runs/` directories retain graph binaries, correlator databases, inputs, logs, and numerical exports. The complete archive occupies about 35.6 MB. The runs are Git-ignored; their compact summaries and checksum manifest are versioned. A GitHub reader gets the records, not the complete local archive.
- **Generated fitter artifacts:** `replicas.sdb` is about 14 MB; fit directories contain intermediate results and final `G*.jack` files. These are generated per run and are not versioned.
- **Replication utility:** ADAT devel now includes [`dbreplicate`](https://github.com/JeffersonLab/adat/blob/devel/main/dbutil/dbreplicate.cc), with tests. The fitter package also supplies a buildable copy and helper. It adds controlled Gaussian noise to complex correlators while retaining the input-key structure.

The small fitter SDB is already preserved. If downloadable compact Redstar contraction SDBs are desired, promoting selected files out of the ignored local archive remains a separate packaging task.

## 6. Other substantial changes worth including

| Area | Additional work |
| --- | --- |
| Reproducible data | Public checksum-pinned Kanoni data setup, a consistent `KANONI_DATA_DIR` home, concrete/relative input paths, and removal of reliance on historical SDB symlinks. See [data guide](https://github.com/JeffersonLab/redstar/blob/devel/docs/data.md). |
| Database interoperability | SUNClass `StorageCorrFunc` reader support, modern and supported legacy formats, multiple input files, and independent key/value comparisons with ADAT `dbutil`. See [fitter reader documentation](https://github.com/JeffersonLab/matelem_fitter/blob/main/README.md#reader-integration-test). |
| Portable builds | One-command clean build/test helpers, pinned sources, actual OpenMP-team checks, and source-distribution inclusion. See [Redstar builds](https://github.com/JeffersonLab/redstar/blob/devel/docs/build.md) and [fitter builds](https://github.com/JeffersonLab/matelem_fitter/blob/main/example/README.md#build-a-fresh-linux-or-macos-stack). |
| ADAT devel | Database replication and tests, read-only MOD metadata/key inspection, and time-slice wrapping utilities/fixes. See [ADAT history](https://github.com/JeffersonLab/adat/commits/devel/). |
| Hadron devel | Apple build cleanup, more accurate memory accounting, and fixes/refinements to segmented batched contractions. See [Hadron history](https://github.com/JeffersonLab/hadron/commits/devel/). |
| ColorVec devel | Multi-GPU node construction, explicit perambulator phasing, database-read changes, and elemental-cache controls. These are supporting branch changes, not all newly introduced in this documentation effort. See [ColorVec history](https://github.com/JeffersonLab/colorvec/commits/devel/). |
| Tensor | The inspected checkout is `master`, not `devel`; its tip includes C++20 compilation support, with OpenBLAS/toolchain support in its history. See [Tensor](https://github.com/JeffersonLab/tensor/tree/master). |
| Other examples | The compact [a0–omega regression](https://github.com/JeffersonLab/redstar/blob/devel/src/generate_all_3pt_spectrum/a0_omega/README.md) checks 16 correlators and 12 extracted operators. Projected-weight conversion and stored-operator extraction also have worked, tested guides. |
| Web documentation | Chroma's `gh-pages` history includes refreshed dependency, build, tutorial, and QDP resource links. See [Chroma website source](https://github.com/JeffersonLab/chroma/blob/gh-pages/index.html). |

## 7. Baseline branches and document location

Use **ADAT, Hadron, ColorVec, Redstar and Chroma `devel`** for the established regression chain; Tensor uses its available `master`. Use `matelem_fitter/main`, `threept_fitting_lib/main`, `fitting_lib/master`, and `plot_lib/main`. Pinned source records identify the precise validated revisions; branch names alone are not an exact reproduction recipe.

This synopsis now lives in **redstar_kanoni/devel/docs/development-summary.md**.
Redstar's former location is a forwarding link. Current regression evidence and
limitations live beside this document; older workflow results above remain
historical evidence with their original data and toolchain qualifications.

[View this summary on GitHub](https://github.com/JeffersonLab/redstar_kanoni/blob/devel/docs/development-summary.md)
once the local documentation changes are published.

## Redstar primer

The [Redstar primer](redstar-primer.md) introduces continuum operator selection,
subduction/coupling, NPointList construction, corr_graph, NPT and CORR_SUPERB.
It includes a checked continuum-pion/NPT example and links the matched native
tensor workflows. Devel remains the baseline; no_1pt stays experimental.

### Latest regression scope

The user deferred ff_3pt, and deferred glue/tetraquark implementation in
CORR_SUPERB. Keep their historical evidence; do not call those deferred comparisons
passed. Glue and tetraquark NPT storage comparisons passed independently.
The direct native-double pion comparison passed all three keys / 48 finite values:
maximum absolute difference 4.0466634007868925e-13, relative Frobenius error
6.529263491790643e-14, zero strict per-value failures. The first complete native
candidate passed checksums and full finite readback of 26,252,960 tensor values;
the broader sweep then exposed missing momentum partners, so it was not promoted.
The meson recipe now uses an empty mom_list and mom2 range 0..4, as requested.
The wider regression sweep and matching experimental checks precede code commits.
