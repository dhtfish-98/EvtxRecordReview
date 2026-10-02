# Origin and attribution

This is new Codex-assisted code for bitfish886, informed by
[williballenthin/python-evtx](https://github.com/williballenthin/python-evtx/tree/1edde3655c676bd44990ce9762d6b8f73334ed1d),
frozen at `1edde3655c676bd44990ce9762d6b8f73334ed1d`, Apache-2.0. The original
Willi Ballenthin/Mandiant authorship and upstream historical acknowledgement of
Andreas Schuster are retained in NOTICE and the complete upstream license.
The applicant is not represented as the sole original author of upstream work.

The entire selected source scope was read: all five Evtx runtime modules
(BinaryParser, Evtx, Nodes, Views and package init), all 12 evtx_scripts entries,
README, pyproject and full LICENSE.TXT: 20 files, 4,209 lines; all fixed Git blob
identities and SHA-256 values are in `evidence/scope-gate.json`. This is complete
selected-scope review, not a claim to audit the entire upstream repository, its
other docs/CI, dependencies, Perl Parse-Evtx or libevtx's complete C implementation.

The replacement writes a new cursor/AST/type/projection/integrity-ledger model.
It removes unbounded input mmap, raw/slack/whole-XML dumps, file writes, dynamic
field helpers and optional XML dependencies. It does not promise full upstream
compatibility. The shared local-reader pattern is attributed in NOTICE.

Primary format references were Microsoft's MS-EVEN6 2.2.12 BinXML grammar,
2.2.12.3 substitution types and 3.1.4.7.2 NULL suppression (entire selected
technical content), plus libyal/libevtx's EVTX format document at
`53ff3377d1360a9a3a428e7190c289757ccbf82b`, SHA-256
`74e3d02a95c41a74d2187af65a0ba8be22afb5370bdc147474edb67cc30619d3`,
selected complete lines 1..990 covering headers/chunks/records/BinXML/values.
The remaining document/GFDL appendix and C implementation were not fully read.
Additionally, the entire 104-line `libevtx/evtx_file_header.h` at that same commit
was read: its four-byte chunk-count array agrees with the document and differs
from historical python-evtx's two-byte declaration. This finite profile and its
compatibility boundary are explicit in DEFENSIVE_SCOPE; the rest of C is unaudited.
Reference text is not shipped, copied into runtime, or relabeled as applicant work.

Research verification runs the fixed original parser with hexdump 3.3 against new
synthetic binary fixtures and two frozen upstream binary test fixtures. These
research dependencies and raw logs are excluded from distribution. Fixed fixture
Git blob/hash identity and aggregate comparison results are in VALIDATION.
This does not certify original log authenticity or Windows exporter equivalence.
The Windows validation adapters are new reviewed Codex-assisted test code, based
on Microsoft's documented [EventLogReader](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.eventing.reader.eventlogreader?view=netframework-4.8)
and [EventLogRecord.ToXml](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.eventing.reader.eventlogrecord.toxml?view=netframework-4.8) APIs with FilePath input.
They use fixed historical input files and disclose no raw event contents.
