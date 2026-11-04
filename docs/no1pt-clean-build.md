# Experimental no_1pt: clean source build and native-double validation

3 November 2026. no_1pt remains experimental; devel is the regression baseline.
This record replaces the retained-binary qualification for this new run only.
The [earlier experimental sweep](no1pt-native-regressions.md) remains historical
validation of its recorded incremental binaries.

## Does Chroma use ADAT?

This Chroma build does. `CORR_SUPERB` uses ADAT's contraction graph, hadron key,
XML/binary I/O and tensor storage interfaces. Chroma was configured with
`--with-redstar-datalib=<fresh-prefix>/adat-mpi`; its application links the fresh
`libadat.a`. Redstar NPT and the database exporter use a separately compiled CPU
ADAT library from the **same source commit**. Chroma's MPI profile and NPT's CPU
profile run in separate processes.

“Snapshot” in the previous report meant retained compiled artifacts, including
an NPT ADAT archive assembled using selected experimental graph-codec objects.
Those numerical checks did not establish that matching source branches built
cleanly. This attempt uses fresh source checkouts, empty build/install directories
and newly compiled project libraries throughout. No old project object, archive
or header was copied into the new stack.

## Source compatibility and build

The isolated workspace is `runs/no1pt-clean-20261103-002/`. Its `sources.json`
records all ten repositories and exact submodules. The main pins are:

| Component | Branch | Source commit |
| --- | --- | --- |
| ADAT base | local devel-rge-no_1pt, published eloy/devel-rge-no_1pt | `161c8edcd7059b95539f1f4a6a6d7c73770363da` |
| ADAT built | isolated codex/no1pt-clean-compat | `817f7e200aa29fa4474c7ac4eeda0658af08869d` |
| Redstar | devel-rge-no_1pt | `45898bd24ab7585d4507df66415326d18b424ec3` |
| Chroma | devel-rge-no_1pt | `1628765976513d8b71ba210ecf116c420a589b09` |
| ColorVec | shared devel | `bab4ff2f050f3b91cf10d2fc394c74aa42faa7c0` |
| Hadron | devel | `34477b440f0099a6b7633d0df97f6ea4e949f35a` |

The local ADAT branch tracks `origin/eloy/devel-rge-no_1pt`. The different,
unprefixed `origin/devel-rge-no_1pt` at `161bc77d` lacks the native storage
additions needed by this suite. The branch mapping is explicit in the source
record; these names are not interchangeable.

The published tips did **not** build together unchanged. Redstar required the
`conjOpName` helper and public installation of `dbtype.h`. Three existing ADAT
devel commits were backported into the isolated source branch:

- `4daaf97dd3bfb3c30c3cb75c1c7ea572c3f6d70d`: conjugate operator-name helper.
- `fd9fefc2f447c3284136a8283072091641384691`: correct Ds/Es conjugation prefixes.
- `4f94cf558ae1410c791c7efb54f9ea7ca9d90124`: install public `dbtype.h`.

The resulting source diff adds 41 lines in three files. The header-install
conflict was resolved by preserving the branch's SuperbBLAS flag conditional.
The [saved source patch](patches/no1pt-adat-compat.patch) is reproducible against
the recorded base; `adat-source-backports.patch/json` in the run directory records
the exact patch, tree and SHA-256.
ADAT and affected consumers were rebuilt from empty directories after the
changes. Original repository checkouts and their existing work were preserved.
These are source fixes, not an incremental binary overlay.

All C++ components use Apple Clang, libc++ and libomp. Tensor Fortran uses
GFortran 14; numerical BLAS uses Accelerate. Chroma's intended MPI backend uses
Homebrew OpenMPI 5.0.7 with Clang wrappers. Fresh MPI builds of QMP, QDP++,
SuperbBLAS and ADAT are separate from NPT's fresh CPU dependencies. Global
`USE_MPI=1` and `SUPERBBLAS_USE_MPI` compiler definitions ensure MPI interfaces
are visible before every shared-header inclusion. Chroma runtime sources are
unchanged; the older standalone Chroma patch was not used.

SuperbBLAS's generated C++ source was split into ten translation units using
complete lines because the upstream GNU split invocation is unavailable here.
The concatenated bodies were checked against the complete generated source;
every object was then compiled locally. No generated body was altered.

Build failures and diagnostics remain archived: the first workspace failed on
the missing helper; subsequent attempts exposed the missing installed header,
initially uninitialized Chroma submodules, the unsupported standalone MPI-header
path, and MPI include-order requirements. The final top-level Chroma build also
needed explicit ADAT link flags for auxiliary tests: their Makefile omits ADAT,
although the application links it correctly. `make LIBS=...` supplied only fresh
ADAT dependencies and the complete build then passed. This changes link
configuration, not runtime source or objects. Exact commands and logs are in
`build_clean.py`, `build_chroma_mpi.py`, `auxiliary-link-command.json`,
`build.json`, `mpi-build.json` and `logs/`; retained failed attempts are not
reported as successful builds.

## Verification and scope

The four ADAT native tests and Redstar's `check_graph_times` test passed.
An installed-header conjugation probe checked K/D/E/Ds/Es name involution.
Installed runtime probes passed for OpenMP teams of one and four and one-rank
MPI initialization/all-reduce. `otool` confirmed libomp without libgomp or
libstdc++; exported configuration flags exclude old project installations.
`source-integrity.json` confirms runtime sources match their recorded commits
across all ten checkouts. Generated bootstrap-file changes are recorded separately.
The exporter was compiled against the newly installed CPU ADAT archive.

The numerical checks use one MPI rank and cached native-double tensors. They
perform zero CG solves and do not validate multi-rank MPI, GPU, the full
on-demand GenProp path, an all-YLM source migration or ensemble physics.
The data are unchanged RsdCG=1e-14 tensors from
`runs/native-superb-rsd14-20261101-001/`, with the explicit validated direct-DISCO
supplement `data/disco-native-direct-20261101-001/`. This does not publish a new
public dataset release.

## Numerical results

**All 30 active paired NPT/CORR cases passed:** 925 keys and 4,197 finite
complex values, zero strict failures and zero CG solves. A pion smoke test
passed before the full run. Fresh format-4 graphs were independently checked;
XML schema version 14 is separate. Graph, NPT and CORR inputs explicitly use
`average_1pt_diagrams=false`, matching time origin, vector counts and physics
flags, including pion_3pt's two vectors. Fake data is disabled.

Independent readback verified exact keys, one-configuration/time shapes and all
finite complex values, then recomputed the unchanged gate:

```text
abs(NPT-CORR) <= 1e-9 * max(abs(NPT),abs(CORR))
                + 1e-12 * max(reference_global_max,1e-30)
```

The relative-only dbutil diagnostic remains separate from acceptance. No failing
channels were removed and no tolerance was relaxed.

| Case | Keys | Complex values | Maximum absolute difference |
| --- | ---: | ---: | ---: |
| pion | 3 | 48 | 9.04113e-15 |
| 1pt | 3 | 48 | 8.61689e-18 |
| 33 | 1 | 16 | 7.2365e-16 |
| 3pi | 3 | 48 | 1.21958e-13 |
| a0.d3 | 324 | 1296 | 4.64794e-20 |
| a1_rhopi | 1 | 16 | 3.43311e-15 |
| d | 1 | 16 | 3.66384e-16 |
| delta_J1o2m | 1 | 16 | 1.11509e-16 |
| eta8eta8_F8 | 1 | 16 | 1.42025e-15 |
| eta_eta_3pt | 1 | 16 | 0 |
| h8 | 4 | 64 | 6.49262e-15 |
| hard.1_tslice.ini | 529 | 2116 | 2.58162e-19 |
| nuc | 1 | 16 | 2.22045e-16 |
| nuc.p100 | 2 | 14 | 2.1207e-16 |
| nuc_gA | 1 | 7 | 1.4267e-17 |
| nuc_nuc_3pt | 1 | 7 | 4.17777e-17 |
| nuc_nuc_ax_3pt | 4 | 28 | 8.72593e-17 |
| nuc_nuc_proj_3pt | 1 | 7 | 2.61967e-19 |
| nucnuc_small | 2 | 8 | 7.98397e-17 |
| nucpi | 1 | 16 | 3.53916e-17 |
| nucpi_I3o2 | 1 | 16 | 3.33229e-17 |
| nucpi_J1o2m | 1 | 16 | 2.50869e-17 |
| nucpi_nucpi_J1o2m | 2 | 32 | 2.77556e-15 |
| pi | 1 | 16 | 1.26001e-15 |
| pi_pi_3pt | 1 | 6 | 2.93266e-16 |
| pion_3pt | 1 | 7 | 3.01842e-16 |
| pipi_i1 | 1 | 16 | 3.02013e-15 |
| psi | 2 | 32 | 4.01209e-15 |
| rho | 3 | 48 | 1.24409e-14 |
| rho_rho_3pt | 27 | 189 | 6.07355e-16 |

Maximum absolute difference: **1.2195766457225513e-13**. Only the declared
`eta_eta_3pt` control contains an exactly zero channel; it has one key, 16 zero
values and exactly zero graphs. All positive cases have nonempty graph coverage.

The fresh NPT outputs also passed the same per-value gate against **all 30**
prior retained experimental NPT outputs: 925 keys, 4,197 values,
maximum absolute difference 0; 30/30 databases
were byte-identical. Only saved outputs were read; no old executable was run.
This is a same-chain compatibility comparison, not new paired devel/no_1pt validation.

The four CORR deferrals remain `ff_3pt`, `fsq_3pt`, `glue` and `tetra_F27_S2`.
`ff_3pt` remains deferred for NPT too. The separate permitted NPT-only lane
passed fsq/glue/tetra: six keys, 96 finite values, no zero channels. It does not
establish CORR support. The policy file is unchanged. The reopened
`nuc_nuc_3pt` paired case uses the explicit validated direct-DISCO collection,
not a plain-shift recipe or a reconstructed shard/packer dataset.

Primary and DISCO provenance exactly match the prior merged devel run. Tool,
archive, input and payload hashes were rechecked. The [machine-readable
record](no1pt-clean-build.json) includes per-case results, source/backport pins,
provenance and evidence hashes. Fresh run inputs, databases, exports, logs and
reports remain in the ignored build workspace; no generated payloads are in Git.

The completed invocations were:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 runs/no1pt-clean-20261103-002/verify_stack.py
PYTHONDONTWRITEBYTECODE=1 python3 runs/no1pt-clean-20261103-002/run_suite.py --smoke
PYTHONDONTWRITEBYTECODE=1 python3 runs/no1pt-clean-20261103-002/run_suite.py
PYTHONDONTWRITEBYTECODE=1 python3 runs/no1pt-clean-20261103-002/run_suite.py --npt-only
PYTHONDONTWRITEBYTECODE=1 python3 runs/no1pt-clean-20261103-002/audit_suite.py
PYTHONDONTWRITEBYTECODE=1 python3 runs/no1pt-clean-20261103-002/audit_additional.py
```

Run launchers preserve their exact underlying commands and use fresh output
directories; choose new output directories for a repeat, rather than overwriting
these successful results. No cleanup removed historical evidence or source data.
