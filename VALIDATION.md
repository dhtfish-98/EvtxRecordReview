# Measured validation and limits

Local source tests: 81 methods PASS on Python 3.14.6. Tests use a separately
written EVTX writer, not runtime parsing functions, and encode actual chunk/name/
template/value/record bytes. Coverage includes resident and referenced templates,
multiple chunks, exact 100 ns times, all declared scalars, vector arrays, nested
BinXML direct/template forms, optional NULL/dependency suppression, PI/CDATA/
entities/continuation, source origins, privacy, deterministic immutable input,
CRC/trailer/length/ID mutations, forward table links/cycles, UTF-16 corruption,
unsupported types, budgets, controlled short reads/changed identity and CLI status.
Controlled missing flags/dir_fd support fail before opening and use fixed CLI
diagnostics; controlled SHA instrumentation confirms zero digest calls for an
over-cap input. A repaired-CRC high-WORD chunk count is OPEN, with no false
reserved-byte corruption assertion.
The randomized malformed test executes 240 seeded mutations and 13 truncations;
those are bounded robustness checks, not a fuzzing completeness claim.

Independent fixed-upstream-parser differential: three input fixtures, 1,604
records, 9,502 equal numeric System facts, zero identity/fact differences and zero
upstream XML parse failures. Original IDs, record offsets/lengths and raw FILETIME
integers match. Its old floating-point formatted timestamp is not an oracle for
100 ns precision. New exact integer timestamps have a separate explicit test.

The two historical upstream corpus inputs are frozen at the same 40-character
source commit. `system.evtx` SHA-256
`ccb83cfefc9038017224cd97b800b66e248fe14529649ddf47907e5a2021449e` has
1,601 bounded records and no definite structural/integrity failure under lenient
review; 1,130 records have complete BinXML evidence. Its dirty/unknown flags,
nonzero alignment, residual NULL storage, arrays and foreign namespaces remain
OPEN. The 1 MiB report cap emits a bounded OPEN summary with inspected count 1,601
and emitted count zero. A controlled validation-only observer counted records
before that ordinary output cap; it did not remove product limits or change PASS.
`issue_38.evtx` SHA-256
`becab64455866f8fae5583fbaa5dab901115e4397ea7abe14f37ad732d5d7eb9` has
one matching record and OPEN unknown flag/alignment evidence. Raw logs and XML
contents are not bundled or retained in public reports.

These results compare independent format parsers, not a Windows Event Viewer/
wevtutil export produced on a verified Windows host. That mandatory external
comparison remains OPEN. CI, remote publication, CVP acceptance and acquisition
authenticity are separate evidence states. Local package build, fresh installed
tests/CLI, distribution source and complete license identity are recorded in the
engineering evidence; they do not substitute for observed remote CI.

The separate `windows-native` CI job installs the built wheel and runs the full
reviewed `tools/windows_compare.py` and `tools/windows_export.ps1` adapters. It
downloads only the two fixed upstream corpus files, checks their SHA-256 and
length, and uses Windows EventLogReader with PathType.FilePath and ToXml. A bounded
XML reader prohibits DTDs and entity resolvers. Native RecordId, FILETIME and all
six supported numeric System facts are compared exactly, independent of order.
Only counts and canonical fact/input hashes reach CI output; raw XML and logs are
temporary and are not published. There is no live channel query or message-resource
rendering. The product's report limit remains enabled during a validation-only
internal observer. POSIX-only secure CLI path reading is deliberately unsupported
on Windows; this job compares the installed bytes API. Until an exact-commit
Windows job is observed passing, this required comparison remains OPEN and the
full runtime-validation gate remains pending. Seven adapter tests check finite
numeric schema, duplicate/missing/different facts, identity and bounded downloads;
their local PASS does not imply a native Windows result.
An eighth adapter test verifies the artifact identity gate, including changed
installed and wheel modules. The Windows job checks all ten runtime source,
wheel and installed module hashes against the final source-review manifest, and
installed metadata against wheel metadata before native export. Its aggregate
includes wheel, source-review and canonical runtime-module hashes.
The first exact-commit CI run, 37019744199 at commit
`25908d2b008f3fddf81b74d9ccc225e7db0433d5`, passed the two Linux jobs but
stopped on Windows at `installed_runtime_source_identity`, before native export.
The failure log does not contain the mismatching file bytes or hashes, so its
precise cause is not proven by that log. A controlled Git checkout with
`core.autocrlf=true` changed all ten LF runtime files to CRLF without attributes;
with the committed `.gitattributes` `eol=lf` rule, all ten raw byte hashes remained
identical to their source-review entries. That rule is included in the source
distribution. The artifact-gate regression also rejects a CRLF-only source
mutation. Raw SHA checks remain unchanged; local checkout protection does not
establish the pending native Windows comparison result.
Passing this targeted numeric comparison would not establish complete Windows
exporter equivalence for the project's unsupported types, dialects or renderings.

All new runtime, test, package, CI, documentation and license files are reviewed
in full and hashed in `evidence/source-review.json` at freeze. Build tools are
pinned and their installed metadata/licenses reviewed; their entire implementations
and Python/platform standard library are not claimed fully audited. Runtime has
no third-party dependency, network path, target XML/resource loader or target code
execution. Package hashes and actual consumer results belong to the engineering
record rather than a self-referential manifest inside their own archive.
