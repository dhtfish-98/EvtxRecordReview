# EvtxRecordReview

Review an already acquired local EVTX snapshot without collecting from a host,
loading event message resources, or changing the log. The tool checks file and
chunk CRC32, record boundaries and trailers, then interprets EVTX BinXML names,
templates and typed substitutions to report positioned event evidence.

```sh
python -m pip install ./dist/evtx_record_review-0.1.0-py3-none-any.whl
evtx-record-review /absolute/physical-path/snapshot.evtx
evtx-record-review /absolute/physical-path/snapshot.evtx --mode lenient --jsonl
evtx-record-review /absolute/physical-path/snapshot.evtx --field Event/System/Computer
```

The default report reveals record identifiers, offsets, exact integer FILETIME
and calendar UTC with 100 ns precision where representable, plus literal numeric
`Event/System` fields: EventID, EventRecordID, Version, Level, Task and Opcode.
Other field names, text, providers, computer names, SIDs and EventData are hashes.
Exact `--field` paths explicitly opt into bounded JSON values. Attributes use a
final `/@Name`. No wildcard, raw XML export, attachment, DLL or EventData dump is
available. Hashes can reveal equality and are not encryption or anonymization.
Input paths are never echoed in reports or fixed diagnostic messages.

`PASS` means the declared physical records and supported structural model were
reviewed with matching CRC and no recorded gap. `FAIL` records a definite format
or integrity failure; `OPEN` records unsupported, partial or budget-limited work.
Known FAIL dominates OPEN. `complete` describes coverage, so complete FAIL does
not mean a healthy file. External authenticity, host execution, Windows exporter
equivalence and CVP application eligibility remain OPEN even for structural PASS.
CRC32 is not a cryptographic authenticity proof.

A record's `VERIFIED_STRUCTURE` requires matching file/chunk CRC, its trailer and
identifier checks, interpreted BinXML and selected projection. Template field
definition offsets can point into an earlier record; `value_origins` locate the
current record's actual substitution bytes and digest. Corrupt, unsupported or
partial records remain UNVERIFIED. Lenient mode advances only from an independently
bounded record length, retains fixed error codes and positions, and propagates
CRC failure; it does not scan for replacement magic or recover slack.

The implementation supports EVTX 3.1/3.2, chunk-local resident and previously
parsed referenced names/templates, deferred forward bucket-chain checks, scalar
variants, optional NULL/dependency suppression, nested BinXML, and typed arrays
for the finite types documented in [DEFENSIVE_SCOPE.md](DEFENSIVE_SCOPE.md).
Windows repeated-element array rendering, multi-fragment event documents,
namespace prefix resolution, nonempty NULL storage, nonzero alignment bytes,
ANSI code pages and unknown versions/types/flags remain OPEN. Paths are literal
BinXML names, not a full namespace-aware Windows event schema. Numeric values are
recorded facts, not proof of an action or a security verdict.

The API accepts immutable bytes, a tuple of up to 16 exact field paths, strict or
lenient mode, and optional `Limits`. Only `None` selects default limits; booleans,
wrong types, zero or increased limits are rejected. Defaults cap input at 16 MiB,
256 chunks, 16,384 records, 1,000,000 parse/hash steps, 32,768 references, depth 48,
1,024 UTF-16 name units, 65,536 bytes per value, 1,024 values per template and array
items, 64 MiB of canonical-value/path hashing work and bounded string
materialization, 512 retained findings and 1 MiB of serialized report. Serialization stops at the cap, rather than building an
unbounded JSON string. Oversized reports emit a bounded OPEN summary with
inspected/emitted record counts and retain known corruption priority. JSONL obeys
the same total output cap. Lower limits are supported; no budget omission is clean.
An API input exceeding the byte cap is rejected before hashing: `input_sha256`
is null and `input_digest_status` is OPEN. Admitted inputs have a whole-input
SHA-256 and explicit PASS digest status; this is byte identity, not authenticity.

The POSIX CLI opens every path component without following symbolic links,
rejects `..`, stdin, URL-like paths, directories and nonregular files, and checks
read length, device/inode, size and timestamps before/after the bounded snapshot.
Use the physical path explicitly on systems with symlinked temporary directories.
Missing O_DIRECTORY, O_NOFOLLOW, O_NONBLOCK or open-with-dir_fd support produces
a fixed input error before any file is opened.
These checks are not a transactional filesystem snapshot guarantee.
The CLI secure reader requires POSIX capabilities; Windows CI uses the installed
bytes API for native offline export comparison. That validation-only adapter
temporarily downloads two fixed public research fixtures; product runtime stays offline.

Development: install `requirements-build.txt`, run `python -m build --no-isolation`
and `PYTHONPATH=src:tests python -m unittest discover -s tests -v`. Runtime has no
third-party dependencies. See [ORIGIN.md](ORIGIN.md) for authorship and source scope
and [VALIDATION.md](VALIDATION.md) for measured evidence and remaining limits.
