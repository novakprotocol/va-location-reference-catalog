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
    re.compile(r"VA_API_KEY\s*=", re.I),
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

def log(message: str) -> None:
    print(f"[{int(time.time() - START):04d}s] {message}", flush=True)

def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def scan_text_patterns(patterns, casefold_markers=False) -> list[str]:
    findings = []
    for path in Path(".").rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if casefold_markers:
            low = text.lower()
            if any(marker in low for marker in patterns):
                findings.append(str(path))
        else:
            for pattern in patterns:
                if pattern.search(text):
                    findings.append(str(path))
                    break
    return sorted(set(findings))

def main() -> None:
    path = Path("data/normalized/va_locations.json")
    records = []
    errors = []

    if path.exists():
        records = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            errors.append("Catalog must be a JSON array.")
            records = []

    ids = [r.get("facility_id") for r in records if isinstance(r, dict)]
    duplicates = sorted([fid for fid, count in Counter(ids).items() if fid and count > 1])

    if duplicates:
        errors.append(f"duplicate facility IDs: {duplicates[:20]}")

    required = ["schema_version", "catalog_version", "lineage_id", "facility_id", "source_system", "source_snapshot_utc", "name", "station_code_confidence", "approval_state"]
    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record {idx} is not an object")
            continue
        for field in required:
            if field not in record:
                errors.append(f"record {idx} missing {field}")

    secret_findings = scan_text_patterns(SECRET_PATTERNS)
    # Avoid flagging this validator for denied marker strings by excluding current file from marker scan output later.
    denied_findings = [f for f in scan_text_patterns(DENIED_MARKERS, casefold_markers=True) if not f.endswith("validate_catalog.py")]

    if secret_findings:
        errors.append(f"possible secret pattern in files: {secret_findings[:20]}")
    if denied_findings:
        errors.append(f"possible denied data marker in files: {denied_findings[:20]}")

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
