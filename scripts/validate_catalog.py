#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

START = time.time()

SECRET_PATTERNS = [
    re.compile(r"apikey\s*[:=]\s*[A-Za-z0-9_\-]{12,}", re.I),
    re.compile(r"Bearer\s+[A-Za-z0-9_\.\-]{20,}", re.I),
    re.compile(r"BEGIN (RSA|OPENSSH|PRIVATE) KEY", re.I),
]

# Keep these precise. A generic word such as "patient" creates false positives
# in policy fields such as not_approved_for=["patient lookup"].
DENIED_MARKERS = [
    "ssn",
    "social security number",
    "patient_id",
    "patient id",
    "patient name",
    "patient ssn",
    "date of birth",
    "dob",
    "claimant_id",
    "claimant id",
    "employee_id",
    "employee id",
    "internal extension",
    "servicenow export",
    "cmdb export",
]

SCAN_ROOTS = [
    Path("data/normalized"),
    Path("data/approved"),
    Path("evidence"),
]

SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".ico"}
DENIED_MARKER_EXCLUDED_KEYS = {"approved_for", "not_approved_for"}


def log(message: str) -> None:
    print(f"[{int(time.time() - START):04d}s] {message}", flush=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def iter_scan_files():
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if ".git" in path.parts or not path.is_file():
                continue
            if path.suffix.lower() in SKIP_SUFFIXES:
                continue
            yield path


def scan_secret_patterns() -> list[str]:
    findings = []
    for path in iter_scan_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(str(path))
                break
    return sorted(set(findings))


def value_contains_denied_marker(value: Any) -> bool:
    text = str(value).lower()
    return any(marker in text for marker in DENIED_MARKERS)


def scan_record_for_denied_markers(value: Any, path: str = "") -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if key_text in DENIED_MARKER_EXCLUDED_KEYS:
                continue
            if value_contains_denied_marker(key_text):
                return True
            if scan_record_for_denied_markers(child, f"{path}.{key_text}" if path else key_text):
                return True
        return False
    if isinstance(value, list):
        return any(scan_record_for_denied_markers(child, path) for child in value)
    if value is None:
        return False
    return value_contains_denied_marker(value)


def scan_denied_markers(records: list[dict[str, Any]]) -> list[str]:
    findings = []
    for idx, record in enumerate(records):
        if scan_record_for_denied_markers(record):
            findings.append(f"record[{idx}] facility_id={record.get('facility_id', 'unknown')}")
    return findings


def main() -> None:
    path = Path("data/normalized/va_locations.json")
    records: list[dict[str, Any]] = []
    errors = []

    if not path.exists():
        errors.append("Missing normalized catalog: data/normalized/va_locations.json")
    else:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            errors.append("Catalog must be a JSON array.")
        else:
            records = [item for item in loaded if isinstance(item, dict)]
            if len(records) != len(loaded):
                errors.append("Catalog contains non-object records.")

    if len(records) == 0:
        errors.append("Catalog contains zero records.")

    ids = [r.get("facility_id") for r in records]
    duplicates = sorted([fid for fid, count in Counter(ids).items() if fid and count > 1])

    if duplicates:
        errors.append(f"duplicate facility IDs: {duplicates[:20]}")

    required = [
        "schema_version",
        "catalog_version",
        "lineage_id",
        "facility_id",
        "source_system",
        "source_snapshot_utc",
        "name",
        "station_code_confidence",
        "approval_state",
    ]

    for idx, record in enumerate(records):
        for field in required:
            if field not in record:
                errors.append(f"record {idx} missing {field}")

    secret_findings = scan_secret_patterns()
    denied_findings = scan_denied_markers(records)

    if secret_findings:
        errors.append(f"possible secret pattern in generated data/evidence files: {secret_findings[:20]}")
    if denied_findings:
        errors.append(f"possible denied data marker in generated records: {denied_findings[:20]}")

    result = "PASS" if not errors else "FAIL"
    receipt = {
        "result": result,
        "record_count": len(records),
        "duplicate_count": len(duplicates),
        "secret_finding_count": len(secret_findings),
        "denied_marker_finding_count": len(denied_findings),
        "error_count": len(errors),
        "errors": errors[:100],
        "validated_utc": dt.datetime.now(dt.UTC).isoformat(),
    }

    write_json(Path("evidence/latest_validation.json"), receipt)
    log(f"VALIDATION_RESULT={result}")
    log(f"RECORD_COUNT={len(records)}")

    if errors:
        for error in errors[:20]:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
