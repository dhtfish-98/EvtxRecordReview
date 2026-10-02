"""Validation-adapter controls; native Windows results require the actual CI job."""
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from contextlib import redirect_stderr
import io

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import windows_compare as adapter
from fixture import ordinary, ChunkWriter, TICKS, element, slot, pack, file, text


def system_fixture(*, header_identifier=1, system_identifier=1, header_ticks=TICKS,
                   system_ticks=TICKS, include_time=True, time_kind=17):
    children = [element("EventID", [text("4624")]),
                element("EventRecordID", [slot(0, 10)]), element("Level", [text("4")])]
    values = [(10, pack("Q", system_identifier))]
    if include_time:
        children.append(element("TimeCreated", attrs=[("SystemTime", [slot(1, 17)])]))
        values.append((time_kind, pack("Q", system_ticks)))
    tree = element("Event", [element("System", children)],
                   [("xmlns", [text("http://schemas.microsoft.com/win/2004/08/events/event")])])
    writer = ChunkWriter()
    writer.record(header_identifier, values, tree, ticks=header_ticks)
    return file([writer.finish()])


class NativeAdapterTests(unittest.TestCase):
    def test_known_numeric_row_and_exact_uint64(self):
        raw = {"record_identifier": "18446744073709551615", "filetime_ticks": "1",
               "fields": {"EventID": "65535", "Level": "4"}}
        row = adapter.native_row(json.dumps(raw).encode())
        self.assertEqual(row["record_identifier"], 2**64 - 1)
        self.assertEqual(row["fields"], {"EventID": 65535, "Level": 4})

    def test_malformed_duplicate_unknown_and_private_values_are_rejected(self):
        for line in (b'{"record_identifier":"1","record_identifier":"2"}', b'[]',
                     b'{"record_identifier":"1","filetime_ticks":"1","fields":{"Host":"PRIVATE"}}',
                     b'{"record_identifier":"1","filetime_ticks":"1","fields":{"EventID":"PRIVATE"}}',
                     b'x' * 4097):
            with self.subTest(line_length=len(line)):
                with self.assertRaises((ValueError, json.JSONDecodeError)):
                    adapter.native_row(line)

    def test_numeric_validation_never_coerces_bools_or_unknown_types(self):
        for value in (True, 1, None, "", "-1", "1\n", "1.0", "0x10", "9" * 21):
            with self.assertRaises(ValueError):
                adapter.decimal(value, 255)
        with self.assertRaises(ValueError):
            adapter.decimal("256", 255)

    def test_record_comparison_is_order_independent_and_hash_only(self):
        rows = [{"record_identifier": n, "filetime_ticks": n, "fields": {"Level": 4}}
                for n in (1, 2)]
        result = adapter.compare(rows, list(reversed(rows)))
        self.assertEqual((result["records"], result["numeric_facts"], result["mismatches"]), (2, 2, 0))
        self.assertNotIn("fields", result)
        self.assertEqual(len(result["canonical_numeric_identity_sha256"]), 64)

    def test_missing_extra_duplicate_different_identity_or_value_fails(self):
        rows = [{"record_identifier": 1, "filetime_ticks": 2, "fields": {"Level": 4}}]
        controls = [[], rows + rows,
                    [{**rows[0], "filetime_ticks": 3}],
                    [{**rows[0], "fields": {"Level": 5}}],
                    [{**rows[0], "fields": {}}]]
        for other in controls:
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(ValueError):
                    adapter.compare(rows, other)

    def test_safe_mismatch_statistics_distinguish_sets_times_presence_and_values(self):
        native = {1: {"record_identifier": 1, "filetime_ticks": 2, "fields": {"Level": 4, "Task": 1}},
                  2: {"record_identifier": 2, "filetime_ticks": 2, "fields": {}}}
        parsed = {1: {"record_identifier": 1, "filetime_ticks": 3, "fields": {"Level": 5}},
                  3: {"record_identifier": 3, "filetime_ticks": 3, "fields": {}}}
        result = adapter.comparison_diagnostics(native, parsed)["native_comparison_diagnostic"]
        self.assertEqual((result["native_records"], result["parsed_records"], result["shared_identifiers"]), (2, 2, 1))
        self.assertEqual((result["native_only_identifiers"], result["parsed_only_identifiers"]), (1, 1))
        self.assertEqual((result["FILETIME_mismatches"], result["shared_record_mismatches"]), (1, 1))
        self.assertEqual(result["FILETIME_native_minus_parsed_ticks"], {"-1": 1})
        self.assertEqual(result["field_presence_mismatches"]["Task"], 1)
        self.assertEqual(result["field_numeric_value_mismatches"]["Level"], 1)
        self.assertNotEqual(result["native_canonical_sha256"], result["parsed_canonical_sha256"])
        first = result["first_shared_difference"]
        self.assertEqual(len(first["record_identifier_sha256"]), 64)
        self.assertEqual((first["native_FILETIME"], first["parsed_FILETIME"]), (2, 3))
        with redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaisesRegex(ValueError, "native_fact_or_identity_mismatch"):
                adapter.compare(list(native.values()), list(parsed.values()))
        self.assertEqual(json.loads(stderr.getvalue())["native_comparison_diagnostic"], result)

    def test_diagnostics_never_emit_unknown_field_or_non_numeric_values(self):
        native = {1: {"record_identifier": 1, "filetime_ticks": "PRIVATE_TIME",
                      "fields": {"Level": "PRIVATE_LEVEL", "PRIVATE_KEY": "PRIVATE_DATA"}}}
        parsed = {1: {"record_identifier": 1, "filetime_ticks": 3, "fields": {"Level": 5}}}
        result = adapter.comparison_diagnostics(native, parsed)
        raw = json.dumps(result)
        self.assertNotIn("PRIVATE", raw)
        self.assertIsNone(result["native_comparison_diagnostic"]["first_shared_difference"]["native_FILETIME"])
        self.assertIsNone(result["native_comparison_diagnostic"]["first_shared_difference"]["known_numeric_fields"]["Level"]["native"])

    def test_real_fixture_capture_keeps_product_report_caps(self):
        rows, report = adapter.parsed_records(system_fixture())
        self.assertEqual((len(rows), report["status"]), (1, "PASS"))
        self.assertEqual(sum(len(row["fields"]) for row in rows), 3)
        self.assertEqual(report["adapter_raw_header_vs_event_System"]["status"], "PASS_OBSERVED_EQUALITY")

    def test_native_System_identity_remains_distinct_from_raw_record_header(self):
        raw = system_fixture(header_identifier=11, system_identifier=77,
                             header_ticks=TICKS, system_ticks=TICKS - 17)
        rows, report = adapter.parsed_records(raw)
        self.assertEqual(rows[0]["record_identifier"], 77)
        self.assertEqual(rows[0]["filetime_ticks"], TICKS - 17)
        self.assertEqual(report["records"][0]["record_identifier"], 11)
        self.assertEqual(report["records"][0]["filetime_ticks"], TICKS)
        status = report["adapter_raw_header_vs_event_System"]
        self.assertEqual((status["status"], status["identifier_differences"], status["FILETIME_differences"]),
                         ("OPEN", 1, 1))
        self.assertEqual(adapter.compare(rows, rows)["mismatches"], 0)
        wrong_domain = [{**rows[0], "record_identifier": 11, "filetime_ticks": TICKS}]
        with redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "native_fact_or_identity_mismatch"):
                adapter.compare(wrong_domain, rows)

    def test_missing_System_identity_does_not_fall_back_to_header(self):
        for raw in (ordinary(), system_fixture(include_time=False), system_fixture(time_kind=0x91)):
            with self.assertRaisesRegex(ValueError, "new_native_System_identity_uninterpreted"):
                adapter.parsed_records(raw)

    def test_download_identity_and_bounded_read_is_enforced(self):
        import hashlib
        import io
        data = b"FIXED_SYNTHETIC"
        class Reader(io.BytesIO):
            def read(self, count):
                self.last_count = count
                return super().read(count)
        fake = Reader(data)
        with patch.object(adapter.urllib.request, "urlopen", return_value=fake) as opened:
            self.assertEqual(adapter.download("system.evtx", len(data), hashlib.sha256(data).hexdigest()), data)
        self.assertEqual(fake.last_count, 2 * 1024 * 1024 + 1)
        self.assertIn(adapter.COMMIT, opened.call_args.args[0])
        with patch.object(adapter.urllib.request, "urlopen", return_value=Reader(data)):
            with self.assertRaisesRegex(ValueError, "fixed_research_input_identity"):
                adapter.download("system.evtx", len(data), "0" * 64)

    def test_installed_identity_requires_all_source_wheel_and_installed_modules(self):
        current_version = adapter.project_version(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_config = root / "pyproject.toml"
            source_config.write_text('[project]\nname = "evtx-record-review"\nversion = "'
                                     + current_version + '"\n', encoding="utf-8")
            (root / "evidence").mkdir()
            (root / "dist").mkdir()
            rows = []
            for index in range(10):
                relative = "evtx_record_review/module" + str(index) + ".py"
                raw = ("# fixed synthetic module " + str(index) + "\n").encode()
                source = root / "src" / relative
                installed = root / "installed" / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                installed.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(raw)
                installed.write_bytes(raw)
                rows.append({"path": "src/" + relative, "sha256": hashlib.sha256(raw).hexdigest()})
            manifest = root / "evidence/source-review.json"
            manifest.write_text(json.dumps({"files": rows}))
            metadata_relative = Path("actual-fixture-distribution.dist-info/METADATA")
            metadata_file = root / "installed" / metadata_relative
            metadata_file.parent.mkdir()
            metadata_file.write_bytes(b"FIXED_METADATA\r\n")
            wheel = root / ("dist/evtx_record_review-" + current_version + "-py3-none-any.whl")
            with zipfile.ZipFile(wheel, "w") as archive:
                for row in rows:
                    archive.write(root / row["path"], row["path"][4:])
                archive.writestr("evtx_record_review-" + current_version + ".dist-info/METADATA",
                                 b"FIXED_METADATA\r\n")
            class Distribution:
                version = current_version
                files = (metadata_relative,)
                def locate_file(self, name):
                    return root / "installed" / name
                def read_text(self, name):
                    return "FIXED_METADATA\n"
            distribution = Distribution()
            with patch.object(adapter.importlib.metadata, "distribution", return_value=distribution):
                distribution.version = current_version + ".post1"
                with self.assertRaisesRegex(ValueError, "installed_version_identity"):
                    adapter.installed_identity(root)
                distribution.version = current_version
                trusted_config = source_config.read_bytes()
                for invalid_config in (b"[project\n", b'[project]\nname="other"\nversion="0.1.1"\n',
                                       b'[project]\nname="evtx-record-review"\nversion="../PRIVATE"\n',
                                       b"X" * 65537):
                    source_config.write_bytes(invalid_config)
                    with self.assertRaisesRegex(ValueError, "trusted_project_version_contract"):
                        adapter.installed_identity(root)
                source_config.write_bytes(trusted_config)
                result = adapter.installed_identity(root)
                self.assertEqual(result["modules_compared"], 10)
                self.assertEqual(result["installed_version"], current_version)
                self.assertEqual(result["source_wheel_installed"], "IDENTICAL")
                self.assertEqual(result["built_wheel_sha256"], hashlib.sha256(wheel.read_bytes()).hexdigest())
                metadata_file.write_bytes(b"PRIVATE_CHANGED_METADATA\r\n")
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    with self.assertRaisesRegex(ValueError, "installed_wheel_metadata_identity"):
                        adapter.installed_identity(root)
                diagnostic = json.loads(stderr.getvalue())["metadata_identity"]
                self.assertEqual(diagnostic["installed_bytes"], len(metadata_file.read_bytes()))
                self.assertNotIn("PRIVATE", stderr.getvalue())
                metadata_file.write_bytes(b"FIXED_METADATA\n")
                with redirect_stderr(io.StringIO()):
                    with self.assertRaisesRegex(ValueError, "installed_wheel_metadata_identity"):
                        adapter.installed_identity(root)
                metadata_file.write_bytes(b"FIXED_METADATA\r\n")
                original_source = source.read_bytes()
                source.write_bytes(original_source.replace(b"\n", b"\r\n"))
                with self.assertRaisesRegex(ValueError, "installed_runtime_source_identity"):
                    adapter.installed_identity(root)
                source.write_bytes(original_source)
                installed.write_bytes(b"# CHANGED_SYNTHETIC\n")
                with self.assertRaisesRegex(ValueError, "installed_runtime_source_identity"):
                    adapter.installed_identity(root)
                installed.write_bytes(source.read_bytes())
                with zipfile.ZipFile(wheel) as archive:
                    members = {name: archive.read(name) for name in archive.namelist()}
                members["evtx_record_review/module0.py"] = b"# CHANGED_WHEEL\n"
                with zipfile.ZipFile(wheel, "w") as archive:
                    for name, raw in members.items():
                        archive.writestr(name, raw)
                with self.assertRaisesRegex(ValueError, "built_runtime_source_identity"):
                    adapter.installed_identity(root)

    def test_installed_metadata_location_and_byte_budget_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = Path("actual-fixture-distribution.dist-info/METADATA")
            target = root / relative
            target.parent.mkdir()
            target.write_bytes(b"X" * 65536)
            class Distribution:
                files = (relative,)
                def locate_file(self, name):
                    return root / name
            distribution = Distribution()
            self.assertEqual(len(adapter.installed_metadata_bytes(distribution)), 65536)
            target.write_bytes(b"X" * 65537)
            with self.assertRaisesRegex(ValueError, "installed_metadata_budget"):
                adapter.installed_metadata_bytes(distribution)
            for entries in (None, (), (relative, relative), tuple([relative] * 129)):
                distribution.files = entries
                with self.assertRaisesRegex(ValueError, "installed_metadata_location_contract"):
                    adapter.installed_metadata_bytes(distribution)


if __name__ == "__main__":
    unittest.main()
