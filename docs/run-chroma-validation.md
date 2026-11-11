# run_chroma devel validation

10 November 2026. The standalone saved-field driver is implemented on Kanoni
**devel**, based on `78cb23b`. Source hashes, tool hashes, exact run paths and
qualifications are in the [machine-readable record](run-chroma-validation.json).
See [usage and limits](run-chroma.md).

## Results

| Check | Result |
| --- | --- |
| Standard Python 3.9 unittest command | 82 tests passed; seven optional TOML tests skipped |
| Python 3.13 unittest command | All 82 passed, no skips |
| Real run with automatic converter build | Passed: graph format 3, exact gauge roundtrip, Chroma completion and nonempty output |
| Real run reusing the converter | Passed in a second fresh directory |
| Independent numerical readback, each real run | Exactly three keys, one configuration, 16 time samples: 48 finite complex values, no zero-valued channels |
| Comparison with archived standalone Chroma output | Both databases byte-identical; maximum absolute difference zero; unchanged strict per-value gate passes |
| Output layout | Only generated outputs in each run; original/prepared XMLs and selected weights outside under run_inputs/ |
| Data/evidence preservation | MOD pair, source inputs, accepted baseline references, historical evidence and .DS_Store unchanged |

Both real runs were launched from `/private/tmp`, with explicit absolute
`REDSTAR_BIN` and `CHROMA_BIN`. The driver chose the correct execution working
directory. The graph and Chroma inputs are respectively
`regressions/direct/pion/graph.xml` and `regressions/corr_superb/chroma.xml`.
They retain the saved-field pion settings: 4³×16, ten vectors, origin zero,
16 samples, original gauge, solver, flavor, smearing and RNG settings.
Each run recorded **680 CG solves**; this is an on-demand propagator test,
not a zero-solve cached-tensor test.

The first run compiled the converter from the selected bin directory's
`chroma-config`. This local validation directory explicitly selects the
corrected historical devel Chroma executable and the existing compatible
GCC Chroma/QDP configuration used for conversion. Their distinct paths,
configuration hash and actual compiler/link command are retained; this is not
a new installed stack. The second run reused that converter. Both conversions
reported an exact MOD-to-QIO readback. The driver builds no Redstar, QDP or
Chroma libraries and performs no branch merge.

Each run requested one OpenMP worker, one BLAS worker, the default 6 GiB planner
budget, 1,800-second executable timeout and 8,192 MiB command-process RSS cap.
The existing Chroma/converter use GCC/libgomp. Redstar and the independent
exporter use Clang/libomp in separate processes; no process mixes the runtimes.
This is a single-process SINGLE-QMP validation, not a new MPI qualification.

## Numerical reference and scope

Independent `dbutil keysxml` and the numbered exporter checked complete keys,
configuration/time shapes and finite values. Both new results match
`runs/direct-pion-mod-20261101-001/superb.sdb1` exactly, including its SHA-256:

```text
583d427f6081d762f7c098dfa582b81b6a430f46b51403dbea7c4ac4c525f5b4
```

The independent relative-only comparison passes at `1e-12`; the additional
per-value check retains `1e-9` relative tolerance plus `1e-12` times the reference
global maximum. No key or channel was discarded, and no baseline was created
or replaced.

The archived reference's original run record remains **numerical_mismatch**:
that earlier experiment compared Chroma against a separate legacy NPT dataset.
Reproducing its Chroma output does not resolve or relabel that historical
NPT/CORR mismatch. This validation establishes saved-field Chroma reproducibility
and runner behavior, not a new matched native-double NPT/CORR result.
No full native suite, GPU, multi-rank execution or general on-demand GenProp
qualification is added. The accepted coverage/deferrals and release manifest
are unchanged.

## Retained evidence

Full logs, compiler command, reports, graph, converted gauge, output databases
and independent exports are under:

```text
runs/run-chroma-validation-20261110-001/auto-build/
runs/run-chroma-validation-20261110-001/prebuilt-importer/
runs/run-chroma-validation-20261110-001/*-comparison/
```

The selected original/prepared XML snapshots are under `run_inputs/auto-build/`
and `run_inputs/prebuilt-importer/`. The numerical audit, test logs and hashes
remain alongside the run directories. The initial new-unit fixture failure
(`/var` versus `/private/var` path comparison) is retained and superseded by
the final passing 82-test runs. Production gates were not weakened.

Run metadata deliberately reports `executables_passed` with
`numerical_readback_validated=false`: the independent numerical audit above is
a separate operation, rather than an unsupported claim based on exit status.

## Publication cleanup: 11 November 2026

The ignored root `.DS_Store` was removed at the user request before committing
and pushing this work. Its ignore rule remains. The preservation statements
above describe the 10 November validation; its historical evidence, source/data
hashes, outputs and earlier mismatch record are unchanged. The machine-readable
record includes the removed metadata file's size/hash and this dated cleanup.
