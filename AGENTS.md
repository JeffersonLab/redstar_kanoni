# Working on redstar_kanoni

## Scope and repository state

- This public repository distributes Redstar example inputs and a checksum-pinned
  dataset. Read README.md and test_inputs/data-manifest.json first.
- Inspect the branch, working tree and index before editing. Preserve deliberately
  staged changes, operator inventories and deletions; do not reset or bulk-commit
  unrelated work. The current working branch is devel.

## Dataset and paths

- Run ./setup-data to install regular, read-only SDB files in checkout data/.
  KANONI_DATA_DIR/--data-dir may select another real directory. Setup imports copy
  source payloads, verifies checksums and retires only verified legacy aliases;
  never create data-directory or SDB symlinks. The former --adopt mode is removed.
- Set KANONI_DATA_DIR to the actual Kanoni data/ directory for external consumers.
  Explicit --database-dir wins over the environment. Numerical test templates use
  ../data/ paths; runners rebase them relative to each fresh run directory and
  refer directly to regular SDBs, without per-run data aliases or copies.
- Pass canonical XML paths such as test_inputs/pipi_i1.xml. Do not recreate
  top-level XML compatibility symlinks or add implicit basename lookup. Relative
  input paths resolve from the caller’s working directory.
- Do not depend on top-level ~/Downloads/*.sdb aliases. Never delete or overwrite
  the actual dataset while cleaning symlinks or run directories.
- The public kanoni-data-v1 release and manifest have immutable sizes/SHA-256
  values. Verify downloads/imports; publish a new version for changed data.
- Keep SDB payloads, generated correlator databases, binaries, logs and numerical
  run directories out of Git. Small numerical inputs and operator weights belong
  in test_inputs; actual SDB payloads belong in Git-ignored data/. Source databases
  are read-only.

## XML schemas and physics

- Classify XML by its root and consuming executable. RedstarNPt graph/numerical
  inputs require Param/version 14. OpsList, GenerateXML and ProjectedOpWeights
  have their own schemas; do not change their version merely to match Redstar.
- v14 NPointList is a child of RedstarNPt, outside Param. CG settings live under
  Param/cgc_options and include explicit target-momentum rotation/version.
- Current operator keys are SUNClass and use mom_class. Literal mom_type is not
  an alias. Jointly rotate constituent momenta; sorting each momentum separately
  changes multiparticle operators.
- scripts/migrate_inputs.py uses the installed convert_proj_weights_util to
  convert legacy one/two-constituent operator definitions through the actual
  Redstar/Hadron type conversion. Keep original source snapshots and its report.
- Preserve explicit phasings, creation/smearing flags, flavor/mass labels, time
  layout and quantum numbers. Do not alter these or turn on fake data to obtain
  a passing test. Source and target momentum conventions must agree.
- weights/v3 is historical source. Prefer validated weights/v4 for runtime.
  Regenerate missing conversions with convert_proj_weights_util, not a global
  search/replace of names or momentum tags.

## Running and validation

- Set REDSTAR_BIN to one consistent installed Redstar stack; use its matching
  ADAT dbutil. Never mix GCC/libgomp and Clang/libomp libraries in one process.
- Run each attempt in a fresh runs/ directory. Relative XML paths resolve from
  the process working directory. Never overwrite an old successful run to pass.
- scripts/validate_inputs.py stages portable inputs and real database paths,
  limits diagnostic output, checks graph/key/assembly coverage, independently
  exports numerical values with dbutil or the checked numbered-file helper for
  oversized/colliding names, and compares extracted operator
  definitions against stored keys. Record timeouts/errors precisely.
- Check finite complex values, expected one-configuration/time shapes and
  nonempty graph coverage. A zero exit status does not prove a useful correlator.
  Report zero-valued channels, unevaluatable graphs and fake-data mode explicitly.
  The eta_eta input is a separately declared isospin-zero control; require exactly
  zero graphs/values and its expected key count. It is not a positive channel.
- Do not weaken checks, invent missing weights/data, or discard failing channels.
  Explain exact missing input/schema/physics issues and keep failed-run evidence.
- Single-configuration runs are software validation, not fitted physical masses
  or ensemble statistics. Replica fitting is the separate matelem_fitter/example
  workflow; its bundled 135-key fixture is derived data, not a raw Kanoni SDB.

## Documentation and cleanup

- Keep README commands consistent with script help and executable arguments.
  Document actual tested results and limits; never label an XML run report as a
  numerical correlator database or graph binary.
- Preserve unique successful run inputs, final data, validation reports, hashes
  and source/compiler provenance. Compress reproducible large diagnostics and
  archive obsolete failures before removing them. Record cleanup actions.
- Use PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v for
  setup/runner regressions. Workflow changes also require fresh real-tool runs.
