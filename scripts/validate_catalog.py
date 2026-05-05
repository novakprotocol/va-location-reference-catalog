#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

START = time.time()

SECRET_PATTERNS = [
    re.compile(r"apikey\s*[:=]\s*[A-Za-z0-9_\-]{12,}", re.I),
    re.compile(r"Bearer\s+[A-Za-z0-9_\.\-]{20,}", re.I),
    re.compile(r"BEGIN (RSA|OPENSSH|PRIVATE) KEY", re.I),
]

DENIED_MARKERS = [
    "ssn",
    "social security number",
    "patient",
    "claimant",
    "employee_id",
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


def log(message: str) -> None:
    print(f"[{int(time.time() - START):04d}s] {message}", flush=True)


def write_json(path: Path, payload) -> None:
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


def scan_denied_markers() -> list[str]:
    findings = []
    for path in iter_scan_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            continue
        if any(marker in text for marker in DENIED_MARKERS):
            findings.append(str(path))
    return sorted(set(findings))


def main() -> None:
    path = Path("data/normalized/va_locations.json")
    records = []
    errors = []

    if not path.exists():
        errors.append("Missing normalized catalog: data/normalized/va_locations.json")
    else:
        records = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            errors.append("Catalog must be a JSON array.")
            records = []

    if len(records) == 0:
        errors.append("Catalog contains zero records.")

    ids = [r.get("facility_id") for r in records if isinstance(r, dict)]
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
        if not isinstance(record, dict):
            errors.append(f"record {idx} is not an object")
            continue
        for field in required:
            if field not in record:
                errors.append(f"record {idx} missing {field}")

    secret_findings = scan_secret_patterns()
    denied_findings = scan_denied_markers()

    if secret_findings:
        errors.append(f"possible secret pattern in generated data/evidence files: {secret_findings[:20]}")
    if denied_findings:
        errors.append(f"possible denied data marker in generated data/evidence files: {denied_findings[:20]}")

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
