# Historical datalib serial, graph and storage checkpoints

> **Historical checkpoints (5–6 November 2026); superseded.**
> The dated results and implementation details below are retained as evidence of
> those early stages. Compatibility headers, external xpath_reader dependencies,
> format-3/Stich support and integration holds described here are not current
> reorg behavior or pending instructions. Later work removed those interfaces
> and completed standalone, Chroma, full regression and MPI validation. See
> [datalib's current reorg reports](https://github.com/JeffersonLab/datalib/tree/rge/devel-datalib-reorg/docs/reorg).
> Local evidence paths below refer to the original checkpoint workspace.

5 November 2026. All listed checks passed. No commits, pushes or merges were
made. QDP, evaluator and Chroma integration remain on hold.

## What changed

- New standalone datalib repository, serial only, with an independent configure
  dependency on the sibling xpath_reader installation and libxml2/libomp.
- Nine canonical ADAT source/header files relocated into datalib, with explicit
  Datalib namespaces. Source hashes and adaptations are in datalib/provenance.json.
- ADAT --with-datalib=PREFIX is required. Compatibility headers preserve current
  source entry points; extracted implementations are excluded from libadat.a.
- All repositories, including ADAT's existing dependency checkouts, use
  rge/devel-datalib-reorg. No new datalib submodule was added.

## Validated results

- Datalib make check passed: exact frozen binary/XML bytes and decoded values,
  checksum, one-based arrays, multidimensional arrays and OpenMP teams 1 and 4.
- Original canonical codecs read output emitted by the installed new codec;
  candidate files are byte-identical to the frozen reference fixtures.
- ADAT make check passed, including version-4 XML/binary content roundtrip and
  rejection of unsupported versions. A real one-graph pion fixture roundtrip
  passed independently using the refactored ADAT reader.
- Preserved MOD inspection tests passed, including independent wire fixtures,
  corruption and offset checks. No QDP runtime was required.
- Database replication integration passed: one key, 4,096 replicas, preserved
  metadata, reproducible seeds, zero-noise agreement with dbmerge, statistical
  noise checks, rejected invalid/overwrite requests and unchanged source data.
- An installed ADAT consumer compiled through adat-config and passed the same
  primitive/XML fixtures. The standalone exported flags contain no ADAT, QDP,
  QMP, MPI or GMP dependency. libadat.a no longer defines the extracted binary
  reader classes. The standalone consumer links libomp, without libgomp/MPI/QDP.
- QDP requests, disabling required OpenMP, and configuring ADAT without datalib
  were rejected as intended.

## Review limits and intentional behavior change

This is the initial primitive/XML-codec and container slice. The shared graph
and key model, graph-specific codecs, ENSEM disentangling, storage/evaluator
and QDP adapters are NOT extracted yet. Chroma/CORR_SUPERB has not been built.
The small format-3 graph fixture is frozen for future compatibility work; this
checkpoint does not implement or validate a new format-3 graph reader. Existing
formats and the numerical regression policy have not changed. No full numerical
correlator regression or multi-rank test is claimed.

One binary error-path fix rejects incomplete reads before checksumming partial
input. The original reader left EOF failures unthrown. Valid output bytes are
unchanged. The reference probe also exposed the old XML writer's lack of text
escaping; its behavior is documented and unchanged. Accepted XML fixtures use
valid text; the malformed legacy output is retained in evidence/.

## Evidence and next review

- evidence/phase1-results.json: scope, passed checks, fixture/tool hashes, limits.
- evidence/adat-extraction.patch: ADAT source change for review.
- datalib/provenance.json: each extraction source and exact hashes.
- datalib/tests/fixtures/manifest.json: frozen primitive/XML and graph fixtures.
- evidence/*-attempt*.json and logs: retained failed build/setup attempts.
- evidence/bootstrap-generated-*.patch: generated helper updates preserved before
  removing that noise from the isolated source diffs.
- evidence/*.py: execution scripts used, including reference producer setup.

Before moving graph models, review the compatibility wrappers and public types,
approve the short-read error behavior, and decide which legacy XML behaviors
should be addressed separately. The next implementation step is the graph/key
model and serial graph codec extraction, preserving the frozen graph bytes;
QDP and all merges still require separate review.

Workspace: `/Users/admin/Downloads/macos-datalib-reorg/`. Paths above are relative
to that workspace. These are local build/review records, not a public release.


## 6 November graph extraction

The first checkpoint's six recorded tool and archive hashes matched. Its
installed primitive codec passed the frozen fixture checks after the reboot.

Datalib now owns the graph models and serial codecs. Format 3 retains its
per-graph `Stich` records in `Datalib::GraphV3::CorrGraphMap_t`. Format 4 keeps
`Hadron::CorrGraphMap_t` and ADAT's `hadron/corr_graph.h` compatibility header.
The reorganization builds use fresh OpenMP prefixes under
`/Users/admin/Downloads/macos-datalib-reorg/install/`.

Both graph writers match the previous binary and XML writers byte for byte on
the frozen pion inputs. The original fixture hashes match. The previous XML
reader yields a one-byte difference in canonically ordered correlator key/value
data compared with its binary reader. The extracted XML reader reproduces that
legacy result for each format. Cross-version and truncated inputs are rejected.

Both builds and test targets passed. Installed-consumer checks covered both
standalone codecs, the ADAT format-4 graph API, MOD inspection and database
replication. The build logs, hash record and source review patch are in
`/Users/admin/Downloads/macos-datalib-reorg/evidence/graph-20261106-001/`.
The workspace handoff is `/Users/admin/Downloads/macos-datalib-reorg/GRAPH-REVIEW.md`.
QDP, the evaluator, Chroma integration and merges remain on hold.


## 6 November storage extraction

The graph probes passed again and their archive and fixture hashes matched.
The first storage slice moves the version-0 correlator container to
`datalib/storage/corr_storage.h`. ADAT's `io/corr_storage.h` forwards the
existing `ADATIO::KeyValueDB` API. The typed FILEDB and tensor adapters remain
in ADAT.

The reader accepts both byte orders and the writer reproduces the valid
legacy fixture bytes. The extraction fixes a dictionary encoder defect that
dropped complete tokens at a branch boundary. The original reader accepts
the corrected mixed-token output in the same version-0 format. Construction
also closes the file handle on failure.

Both fresh OpenMP builds and all installed checks passed. Datalib tests
covered the two byte orders, metadata, chunked rows, compressed keys and
checksum rejection. The installed ADAT tools passed graph and MOD checks and
replicated three keys with 4,096 samples each. The source database hash
matched after testing.

See `/Users/admin/Downloads/macos-datalib-reorg/STORAGE-REVIEW.md` for the
handoff and `evidence/storage-20261106-001/` in that workspace for the build
record and validation hashes. QDP, the evaluator, Chroma integration and
merges remain on hold.


## 6 November FILEDB extraction

The storage checkpoint passed again with matching archive, header and fixture
hashes. Datalib now owns FILEDB key and value serialization and the typed
all-configuration store helpers. ADAT forwards its existing serializers and
uses the same helpers with its bundled FILEDB provider. Standalone consumers
can select the separately built provider through `--with-filedb=PREFIX`.
Both providers use the existing FILEDB pin `db2a795a`.

The legacy DISCO check exposed a compatibility gap in the first checkpoint's
strict short-read behavior. The FILEDB adapter now accepts a complete payload
that ends without a CRC. Present trailers still require four bytes and a
matching checksum. Partial trailers and truncated payloads are rejected.

Frozen serialized key and value bytes match. The old and new readers opened
each other's databases and preserved metadata, configuration counts and values.
The installed ADAT DISCO readback matched the raw reference for all 144 keys
and 2,304 finite complex values. The source checksum matched afterward.

Fresh OpenMP builds, all 11 installed checks and the core-only build passed.
The review handoff is
`/Users/admin/Downloads/macos-datalib-reorg/FILEDB-REVIEW.md`. Logs and hashes
are under `evidence/filedb-20261106-001/` in the reorganization workspace.
QDP, the evaluator, Chroma integration and merges remain on hold.
