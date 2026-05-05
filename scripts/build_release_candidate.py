#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

START = time.time()

def log(message: str) -> None:
    print(f"[{int(time.time() - START):04d}s] {message}", flush=True)

def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def git_value(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git"] + args, text=True).strip()
    except Exception:
        return "unknown"

def main() -> None:
    normalized = Path("data/normalized")
    approved = Path("data/approved")
    approved.mkdir(parents=True, exist_ok=True)

    required = [
        "va_locations.json",
        "va_locations.csv",
        "va_locations.jsonl",
        "index_by_facility_id.json",
        "index_by_station_code.json",
        "unmatched_station_codes.json",
    ]

    missing = [name for name in required if not (normalized / name).exists()]
    if missing:
        raise SystemExit(f"Missing normalized outputs: {missing}")

    for name in required:
        shutil.copy2(normalized / name, approved / name)

    records = json.loads((approved / "va_locations.json").read_text(encoding="utf-8"))
    catalog_version = records[0].get("catalog_version") if records else dt.datetime.now(dt.UTC).strftime("%Y.%m.%d.1")
    schema_version = records[0].get("schema_version") if records else "1.0.0"

    consumer_contract_src = Path("contracts/consumer_registry.json")
    if consumer_contract_src.exists():
        shutil.copy2(consumer_contract_src, approved / "consumer_registry.json")

    manifest = {
        "catalog_name": "VA IaT Location Reference Catalog",
        "catalog_version": catalog_version,
        "schema_version": schema_version,
        "git_commit": git_value(["rev-parse", "HEAD"]),
        "git_branch": git_value(["branch", "--show-current"]),
        "record_count": len(records),
        "created_utc": dt.datetime.now(dt.UTC).isoformat(),
        "validation_receipt": "evidence/latest_validation.json",
        "release_channel": "candidate",
        "write_back_allowed": False
    }

    write_json(approved / "release_manifest.json", manifest)

    checksum_lines = []
    for path in sorted(approved.glob("*")):
        if path.is_file():
            checksum_lines.append(f"{sha256(path)}  {path.as_posix()}")
    (approved / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    write_json(Path("evidence/latest_release_manifest.json"), manifest)
    log(f"PASS release candidate built: data/approved")
    log(f"CATALOG_VERSION={catalog_version}")
    log(f"RECORD_COUNT={len(records)}")

if __name__ == "__main__":
    main()
