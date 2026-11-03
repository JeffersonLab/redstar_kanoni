# ARB merge into Redstar devel

Validated and integrated locally on 3 November 2026. `redstar.devel/devel`
fast-forwarded from `d17e6a8e5adfcd5230ab9fd970d00619cbeb37b4` to the tested
merge `b194fdfcfe93742ba6887e4374fd5a32a002415f`. Its second parent is
ARB `f65c45fbd77a80960c8f4471c9c5acd2adb73946`. Both source checkouts were clean;
no existing work was reset or stashed. This records local integration, not a push.

The merge retains ARB's optional NPT memory auditing and three-hadron
momentum-class independence fix. The relevant implementations exactly match
the ARB parent. Devel's data preparation scripts, `KANONI_DATA_DIR` support,
portable numerical template and `cont_op->second.B` baryon metadata fix remain
unchanged from the devel parent. Devel remains the baseline; this does not
promote experimental no_1pt or change its graph-format requirements.

## Build qualification

A fresh archive of the exact merge was configured, built with `make -j4`,
checked with `make check`, and installed under
`runs/arb-merge-build-20261103-001/`. Apple Clang 21.0.0, C++20, LLVM libomp
and Accelerate were used on arm64 macOS. Existing matching ADAT, Hadron,
ColorVec and tensor installations were reused, rather than rebuilt.
Their recorded source revisions, compiler details and installed binary hashes
are in the [machine-readable record](arb-merge-validation.json).

`make check` succeeded; it builds check programs but declares no Automake
`TESTS` suite. Separate compiled OpenMP checks using installed `redstar-config`
flags observed actual teams of one and four workers. Dynamic-library inspection
found libomp and no GNU OpenMP runtime. Source checkouts and saved numerical
baselines were unchanged during validation.

## Targeted behavior checks

With `NPT_MEMORY_AUDIT=1`, all eight numerical cases emitted structured records
with contiguous sequence numbers and the expected initialization, evaluation,
output and finalization stages. A fresh audit-off pion run emitted no audit
records and passed comparison against audit-on output at relative tolerance
`1e-12`, ignore tolerance zero. Without jemalloc, an optional heap-profile
request warned and completed; `NPT_HEAP_DUMP_REQUIRED=1` failed as expected.
These expected negative-test results are separate from numerical failures.

The unmodified `generate_nonint_spectrum_3ops` example produced 190 raw records
and 48 selected operators on both builds, with identical XML maps. Changing only
`rel2_max` from 3 to 4 produced 294 raw records on both builds. The merge selected
74 operators versus devel's 71: all shared definitions were unchanged, and the
three additions contain the ±002 momentum pair. This exercises the correction
that prevents comparing different constituent momentum classes as dependent.
No operators were removed. Inputs, logs and exact added names are retained.

## Numerical regression results

The checksum-pinned public kanoni-v1 legacy SDB dataset was used directly,
read-only, with four workers and fake data disabled. Fresh graph and NPT outputs
were checked for graph/key/operator coverage, full finite readback and expected
configuration/time shapes, then compared against existing hash-pinned devel
baselines using independent key/value exports. The existing relative `1e-12`
regression tolerance and zero ignore tolerance were unchanged.

| Case | Keys | Finite complex values | Result |
| --- | ---: | ---: | --- |
| 1pt | 3 | 48 | Passed |
| eta_eta_3pt | 1 | 16 | Exact symmetry-zero control; passed |
| nuc | 1 | 16 | Passed |
| nuc.p100 | 2 | 14 | Passed |
| pion | 3 | 48 | Passed |
| pion_3pt | 1 | 7 | Passed |
| pipi_i1 | 1 | 16 | Passed |
| rho_rho_3pt | 27 | 189 | Passed |
| Total | 39 | 354 | Eight comparisons passed |

Every candidate correlator SDB was byte-identical to its saved devel baseline.
The eta control retained its expected key count and exactly zero graphs/values;
it is not a positive channel. Baselines were neither replaced nor re-established.
This legacy-baseline gate is separate from the unchanged native NPT/CORR
per-value acceptance gate documented in [regression coverage](regressions.md).

## Evidence and reproduction

Local retained evidence, relative to the Kanoni checkout:

- `runs/arb-merge-build-20261103-001/`: exact source archive, build/install,
  configuration and build logs, provenance, audit checks and three-hadron runs.
- `runs/validation-20261103-143727-k99zpk4v/results.json`: numerical validation.
- `runs/validation-20261103-143727-k99zpk4v/regressions.json`: baseline comparisons.
- `runs/validation-20261103-143656-t9i9_8ea/`: initial blocked attempt. Sandbox
  denial of `ps` prevented process monitoring; it did not establish a numerical
  failure. The successful retry had process-inspection access.

The build directory retains `config.log`, generated Makefiles and the exact
configure arguments. `tools.toml` and `tests.toml` in the build evidence directory
select the installed merge and the eight pinned baseline cases. To repeat the
regression stage from the Kanoni root using that retained installation:

```sh
NPT_MEMORY_AUDIT=1 PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_regressions.py \
  --tools runs/arb-merge-build-20261103-001/tools.toml \
  --list runs/arb-merge-build-20261103-001/tests.toml \
  --threads 4 --timeout 300
```

Use Python 3.11+ or the documented TOML fallback, and permit child-process
inspection for the existing memory monitor. The runner creates a fresh suite;
do not overwrite saved evidence. For another machine, provide equivalent local
tool paths. Generated binaries, SDBs and logs remain Git-ignored; the compact
JSON record preserves result summaries and evidence hashes.

## Limits

Linux `/proc` RSS and `mallinfo2` fields report unavailable on this macOS build.
Real jemalloc heap dumps were not tested. This was a targeted eight-case legacy
regression, not a repeat of the native-double NPT/CORR matrix or a clean rebuild
of all dependencies. It establishes no Linux, MPI, GPU, latest-YLM or ensemble
physics validation. Existing [deferrals](regression-policy.json) remain in force.
