"""CI-only native Windows export oracle for two fixed historical offline files.

Downloads are bounded research inputs, never a product runtime feature. No raw
XML/event text or per-record facts are printed or saved as CI artifacts.
"""

import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile
from unittest.mock import patch

from evtx_record_review import review
from evtx_record_review.contracts import Ledger, encoded
from evtx_record_review.projection import NUMERIC_FIELDS


COMMIT = "1edde3655c676bd44990ce9762d6b8f73334ed1d"
CORPUS = (
    ("system.evtx", 1118208, "ccb83cfefc9038017224cd97b800b66e248fe14529649ddf47907e5a2021449e", 1601),
    ("issue_38.evtx", 69632, "becab64455866f8fae5583fbaa5dab901115e4397ea7abe14f37ad732d5d7eb9", 1),
)
FIELD_NAMES = {path.rsplit("/", 1)[1]: maximum for path, maximum in NUMERIC_FIELDS.items()}


def installed_identity(project=None):
    project = Path(project) if project is not None else Path(__file__).resolve().parents[1]
    manifest_raw = (project / "evidence/source-review.json").read_bytes()
    manifest = json.loads(manifest_raw)
    modules = [row for row in manifest["files"]
               if row["path"].startswith("src/evtx_record_review/") and row["path"].endswith(".py")]
    if len(modules) != 10 or len({row["path"] for row in modules}) != 10:
        raise ValueError("runtime_manifest_contract")
    distribution = importlib.metadata.distribution("evtx-record-review")
    if distribution.version != "0.1.0":
        raise ValueError("installed_version_identity")
    hashes = {}
    for row in modules:
        relative = row["path"][4:]
        source_path = project / row["path"]
        installed_path = Path(distribution.locate_file(relative))
        if source_path.stat().st_size > 65536 or installed_path.stat().st_size > 65536:
            raise ValueError("source_installed_runtime_budget")
        source = source_path.read_bytes()
        installed = installed_path.read_bytes()
        if (hashlib.sha256(source).hexdigest() != row["sha256"]
                or hashlib.sha256(installed).hexdigest() != row["sha256"]):
            raise ValueError("installed_runtime_source_identity")
        hashes[relative] = row["sha256"]
    wheel = project / "dist/evtx_record_review-0.1.0-py3-none-any.whl"
    if wheel.stat().st_size > 1024 * 1024:
        raise ValueError("built_wheel_budget")
    with zipfile.ZipFile(wheel) as archive:
        metadata_path = "evtx_record_review-0.1.0.dist-info/METADATA"
        if archive.getinfo(metadata_path).file_size > 65536:
            raise ValueError("built_metadata_budget")
        metadata = archive.read(metadata_path)
        if distribution.read_text("METADATA").encode() != metadata:
            raise ValueError("installed_wheel_metadata_identity")
        for relative, expected in hashes.items():
            if archive.getinfo(relative).file_size > 65536:
                raise ValueError("built_runtime_budget")
            if hashlib.sha256(archive.read(relative)).hexdigest() != expected:
                raise ValueError("built_runtime_source_identity")
    return {"modules_compared": 10, "source_wheel_installed": "IDENTICAL",
            "installed_version": distribution.version,
            "source_review_sha256": hashlib.sha256(manifest_raw).hexdigest(),
            "runtime_module_hashes_sha256": hashlib.sha256(encoded(hashes)).hexdigest(),
            "built_wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}


def decimal(value, maximum):
    if (type(value) is not str or not 1 <= len(value) <= 20
            or any(char < "0" or char > "9" for char in value)):
        raise ValueError("native_numeric_contract")
    number = int(value)
    if number > maximum:
        raise ValueError("native_numeric_range")
    return number


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("native_duplicate_json_key")
        result[key] = value
    return result


def native_row(line):
    if len(line) > 4096:
        raise ValueError("native_line_budget")
    row = json.loads(line, object_pairs_hook=unique_object)
    if type(row) is not dict or set(row) != {"record_identifier", "filetime_ticks", "fields"}:
        raise ValueError("native_row_schema")
    fields = row["fields"]
    if type(fields) is not dict or not set(fields) <= set(FIELD_NAMES):
        raise ValueError("native_fields_schema")
    return {"record_identifier": decimal(row["record_identifier"], 2**64 - 1),
            "filetime_ticks": decimal(row["filetime_ticks"], 2**64 - 1),
            "fields": {key: decimal(value, FIELD_NAMES[key]) for key, value in fields.items()}}


def download(name, expected_bytes, expected_sha):
    url = "https://raw.githubusercontent.com/williballenthin/python-evtx/" + COMMIT + "/tests/data/" + name
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) != expected_bytes or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError("fixed_research_input_identity")
    return raw


def export(path, executable):
    script = Path(__file__).with_name("windows_export.ps1")
    command = [executable, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
               "-File", str(script), "-InputPath", str(path)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    timer = threading.Timer(120, process.kill)
    timer.start()
    rows, total = [], 0
    try:
        while True:
            line = process.stdout.readline(4097)
            if not line:
                break
            total += len(line)
            if total > 2 * 1024 * 1024 or len(rows) >= 2048:
                raise ValueError("native_export_budget")
            rows.append(native_row(line))
        if process.wait(timeout=10) != 0:
            raise ValueError("native_offline_export_failed")
    finally:
        timer.cancel()
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
        process.stdout.close()
    return rows


def parsed_records(raw):
    captured = {}
    finish = Ledger.finish

    def observe(self, raw, header, chunks, records, mode):
        captured["records"] = records
        return finish(self, raw, header, chunks, records, mode)

    with patch.object(Ledger, "finish", observe):
        report = review(raw, mode="lenient")
    if report["known_corruption_count"]:
        raise ValueError("new_parser_known_corruption")
    rows = []
    for row in captured["records"]:
        fields = {}
        for fact in row["fields"]:
            if "numeric_value" in fact:
                name = fact["path"].rsplit("/", 1)[1]
                if name in fields:
                    raise ValueError("new_duplicate_numeric_fact")
                fields[name] = fact["numeric_value"]
        rows.append({"record_identifier": row["record_identifier"],
                     "filetime_ticks": row["filetime_ticks"], "fields": fields})
    return rows, report


def compare(native, parsed):
    def index(rows):
        result = {}
        for row in rows:
            key = row["record_identifier"]
            if key in result:
                raise ValueError("comparison_duplicate_record_identifier")
            result[key] = row
        return result

    left, right = index(native), index(parsed)
    if left != right:
        raise ValueError("native_fact_or_identity_mismatch")
    canonical = [right[key] for key in sorted(right)]
    return {"records": len(canonical), "numeric_facts": sum(len(row["fields"]) for row in canonical),
            "canonical_numeric_identity_sha256": hashlib.sha256(encoded(canonical)).hexdigest(),
            "native_record_ids_and_FILETIME_equal": True, "mismatches": 0}


def main():
    if sys.platform != "win32":
        raise ValueError("Windows_native_runtime_required")
    executable = shutil.which("powershell.exe")
    if executable is None:
        raise ValueError("Windows_PowerShell_required")
    identity = installed_identity()
    results = []
    with tempfile.TemporaryDirectory(prefix="evtx-fixed-native-") as directory:
        for name, expected_bytes, expected_sha, expected_count in CORPUS:
            raw = download(name, expected_bytes, expected_sha)
            path = Path(directory) / name
            path.write_bytes(raw)
            native = export(path, executable)
            parsed, report = parsed_records(raw)
            result = compare(native, parsed)
            if result["records"] != expected_count or path.read_bytes() != raw:
                raise ValueError("corpus_count_or_input_changed")
            results.append({"fixture": name, "input_sha256": expected_sha, "input_unchanged": True,
                            "product_status": report["status"], "product_complete": report["complete"],
                            **result})
    print(json.dumps({"oracle": "Windows EventLogReader FilePath ToXml numeric-only export",
                      "upstream_commit": COMMIT, "result": "PASS", "results": results,
                      "artifact_identity": identity}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Validation faults must not echo the paths, source XML, values or exception.
        safe_codes = {"Windows_native_runtime_required", "Windows_PowerShell_required",
                      "fixed_research_input_identity", "native_offline_export_failed",
                      "native_export_budget", "native_line_budget", "native_row_schema",
                      "native_fields_schema", "native_duplicate_json_key", "native_numeric_contract",
                      "native_numeric_range", "new_parser_known_corruption", "new_duplicate_numeric_fact",
                      "comparison_duplicate_record_identifier", "native_fact_or_identity_mismatch",
                      "corpus_count_or_input_changed", "runtime_manifest_contract", "installed_version_identity",
                      "source_installed_runtime_budget", "built_wheel_budget",
                      "installed_runtime_source_identity", "built_metadata_budget", "built_runtime_budget",
                      "built_runtime_source_identity", "installed_wheel_metadata_identity"}
        code = str(error) if type(error) is ValueError and str(error) in safe_codes else "validation_adapter_error"
        print("Windows_native_comparison_failed:" + code, file=sys.stderr)
        raise SystemExit(1)
