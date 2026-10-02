# Defensive scope and finite format model

Only local immutable EVTX bytes are input. There is no host collection, remote
reader, archive or stdin input, code/entity execution, message DLL access, record
injection, clearing, repair, writable output file or carving. The CLI writes JSON
or JSONL to stdout. The API never imports input data as Python or XML code.

## Integrity and provenance

Declared 4096-byte file headers and 65536-byte physical chunks are checked before
record parsing. File CRC covers bytes 0..119. Chunk header CRC covers 0..119 plus
128..511; chunk data CRC covers 512 through the allocated-free offset. Records
require a 24-byte header, bounded aligned length, signature, full payload and
matching trailing length. Duplicate IDs, first/last-ID discrepancies and last
record-offset discrepancies are FAIL. File allocation-number ambiguity, dirty
metadata, unknown nonzero chunk flag fields and uninterpreted record-number ranges
are OPEN. Physical ordering is reported; circular logical ordering, inactive
chunks, trailing/slack contents and recovered-record identity are not inferred.

The file chunk-count profile is the modern libyal DWORD at byte offset 42,
followed by 74 uninterpreted bytes at 46..119. The frozen historical python-evtx
uses a WORD at 42 and 76 uninterpreted bytes at 44..119. Both real comparison
fixtures have zero high WORD, so they do not establish which width Windows used.
This project accepts at most 256 chunks; a nonzero high WORD exceeds that profile
and is OPEN as `chunks_budget`, without asserting a universal reserved-zero rule.

## BinXML interpretation

The parser implements EOF, element start/close/end, inline UTF-16 values,
attributes, CDATA, character/entity references, processing-instruction pairs,
resident/referenced template instances, normal/optional substitutions and fragment
headers. Defined continuation forms 0x41/45/46/47/48/49 are interpreted. Element and
attribute lengths delimit independent cursor spans. Names require valid bounded
UTF-16, XML names and terminators, with 65599 hash and bucket consistency checks.
Pointers must stay in the allocated chunk. Used name/template back-references must
already be parsed. Bucket chains are checked after the record walk so later
resident definitions are valid forward links; unresolved chains/tables are OPEN,
cycles and out-of-bounds links FAIL. Slack definitions are never loaded.

Each template AST is rebound immutably per record. Dependency NULL omits its
element; optional substitution NULL omits its immediate parent element or its
attribute. Ordinary type/index/length inconsistencies FAIL. Nested BinXML supports
direct elements without dependency WORDs and resident/referenced template streams,
with recursive depth/work bounds. No textual XML parser, entity loader or XML
renderer is used in the runtime. Only the five predefined XML entities are
interpreted. Unknown entities remain OPEN and are never fetched or expanded.

Scalar support: NULL, UTF-16 string with at most one optional trailing NUL,
ASCII-only ANSI projection, signed/unsigned 8/16/32/64-bit integers, float/double,
EVTX DWORD boolean 0/1, binary bytes as internal typed hex, GUID little-endian,
4/8-byte size integers, FILETIME, 16-byte SYSTEMTIME, bounded SID, Hex32/Hex64 and
nested BinXML. FILETIME uses integer arithmetic; calendar overflow remains OPEN
with raw ticks retained. SYSTEMTIME milliseconds are converted without the old
microsecond error. Nonfinite IEEE values retain a finite JSON bits descriptor.
Wire boolean dialects of other protocols are not asserted as EVTX compatibility.

Supported typed arrays are NULL-separated UTF-16/ASCII strings and fixed-width
integer, float/double, boolean, GUID, FILETIME, SYSTEMTIME and Hex32/Hex64 arrays.
They retain vectors and explicitly OPEN repeated-element expansion. Size-integer
arrays have an ambiguous width and remain OPEN; SID, binary and nested-BinXML
arrays are not implemented and remain OPEN. Unknown types, flags, variants,
multiple fragments, foreign default namespaces and prefix resolution are OPEN.
Name paths are lexical evidence, without full XML namespace or Windows schema
validation. NULL descriptors with nonempty residual storage and nonzero record
alignment bytes remain OPEN, with boundaries and source digests retained.

## Evidence boundaries

FAIL indicates a local definite integrity/format contradiction. OPEN does not
assert malware or corruption. CRC and matching template facts do not authenticate
the acquisition, prove an event happened, identify a user, or prove CVP eligibility.
Strict mode stops a record walk on uninterpreted structure; lenient mode continues
only when its record boundary is independently established. Known prior failures
remain in the ledger even when later work or reporting is limited. Numeric field
facts and selected values from a partial record retain UNVERIFIED provenance.

Every active recursion/loop/reference/value/hash/report dimension is bounded.
The output cap is applied during serialization. Strings are escaped in at most 512-code-point segments, producing at most
6,144 ASCII bytes per serialization chunk; a cap overflow returns a small summary.
The source reader rejects links at all path components and verifies length and
identity, but does not claim immunity to every concurrent filesystem race.
Secure-open platform flags and dir_fd capability are required before file access.
An over-cap API input is never hashed and has null SHA-256 plus OPEN digest status.
