#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import time
from pathlib import Path
from typing import Any

START = time.time()
SCHEMA_VERSION = "1.0.0"

def log(message: str) -> None:
    print(f"[{int(time.time() - START):04d}s] {message}", flush=True)

def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def derive_station_code(facility_id: str) -> tuple[str | None, str]:
    match = re.match(r"^vha_([A-Za-z0-9]+)$", facility_id or "")
    if match:
        return match.group(1), "derived"
    return None, "not_available"

def extract_feature_values(feature: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    props = feature.get("properties") or {}
    attrs = props.get("attributes") or feature.get("attributes") or {}
    facility_id = str(feature.get("id") or props.get("id") or attrs.get("id") or "")
    return facility_id, attrs if attrs else props

def normalize_feature(feature: dict[str, Any], raw_source_file: str, snapshot_utc: str, catalog_version: str, source_url: str | None) -> dict[str, Any]:
    facility_id, attrs = extract_feature_values(feature)
    station_code, station_confidence = derive_station_code(facility_id)

    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    long = lat = None
    if isinstance(coords, list) and len(coords) >= 2:
        long, lat = coords[0], coords[1]

    lineage_id = f"source:va_facilities_api|facility_id:{facility_id}|snapshot:{snapshot_utc}"

    return {
        "schema_version": SCHEMA_VERSION,
        "catalog_version": catalog_version,
        "lineage_id": lineage_id,
        "facility_id": facility_id,
        "station_code": station_code,
        "station_code_confidence": station_confidence,
        "source_system": "VA Facilities API",
        "source_url": source_url,
        "source_snapshot_utc": snapshot_utc,
        "name": str(attrs.get("name") or ""),
        "facility_type": attrs.get("facility_type"),
        "classification": attrs.get("classification"),
        "visn": attrs.get("visn"),
        "address": attrs.get("address"),
        "phone": attrs.get("phone") or attrs.get("phone_numbers"),
        "website": attrs.get("website"),
        "lat": lat if lat is not None else attrs.get("lat"),
        "long": long if long is not None else attrs.get("long") or attrs.get("lng"),
        "operating_status": attrs.get("operating_status"),
        "approval_state": "draft",
        "approved_for": [],
        "not_approved_for": [
            "employee_directory",
            "internal_phone_tree",
            "emergency_contact_roster",
            "automatic_production_mutation"
        ],
        "raw_source_file": raw_source_file,
    }

def main() -> None:
    latest_file = Path("data/raw/va_facilities_api/latest_snapshot.txt")
    if not latest_file.exists():
        raise SystemExit("No latest snapshot found. Run scripts/fetch_va_facilities.py first.")

    snapshot_dir = Path(latest_file.read_text(encoding="utf-8").strip())
    raw_file = snapshot_dir / "facilities.geojson"
    meta_file = snapshot_dir / "response.meta.json"

    raw = load_json(raw_file)
    meta = load_json(meta_file)

    snapshot_utc = meta.get("snapshot_utc") or dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    catalog_version = dt.datetime.now(dt.UTC).strftime("%Y.%m.%d.1")
    source_url = meta.get("source_url")

    features = raw.get("features", [])
    if not isinstance(features, list):
        raise SystemExit("Expected GeoJSON FeatureCollection with features[].")

    records = [
        normalize_feature(feature, str(raw_file), snapshot_utc, catalog_version, source_url)
        for feature in features
        if isinstance(feature, dict)
    ]
    records.sort(key=lambda r: (r.get("facility_type") or "", r.get("facility_id") or ""))

    out_dir = Path("data/normalized")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "va_locations.json"
    csv_path = out_dir / "va_locations.csv"
    jsonl_path = out_dir / "va_locations.jsonl"
    by_facility_path = out_dir / "index_by_facility_id.json"
    by_station_path = out_dir / "index_by_station_code.json"
    unmatched_path = out_dir / "unmatched_station_codes.json"

    write_json(json_path, records)
    jsonl_path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8")

    columns = [
        "schema_version", "catalog_version", "lineage_id", "facility_id", "station_code",
        "station_code_confidence", "source_system", "source_snapshot_utc", "name",
        "facility_type", "classification", "visn", "website", "lat", "long",
        "approval_state", "raw_source_file"
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    by_facility = {r["facility_id"]: r for r in records if r.get("facility_id")}
    by_station = {}
    unmatched = []
    for r in records:
        station = r.get("station_code")
        if station:
            by_station.setdefault(station, []).append(r["facility_id"])
        else:
            unmatched.append(r)

    write_json(by_facility_path, by_facility)
    write_json(by_station_path, by_station)
    write_json(unmatched_path, unmatched)

    evidence = {
        "result": "PASS",
        "schema_version": SCHEMA_VERSION,
        "catalog_version": catalog_version,
        "record_count": len(records),
        "unmatched_station_count": len(unmatched),
        "outputs": {
            "json": str(json_path),
            "csv": str(csv_path),
            "jsonl": str(jsonl_path),
            "index_by_facility_id": str(by_facility_path),
            "index_by_station_code": str(by_station_path),
            "unmatched_station_codes": str(unmatched_path)
        },
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "raw_source": str(raw_file)
    }
    write_json(Path("evidence/latest_normalization.json"), evidence)
    log(f"PASS normalized {len(records)} records")

if __name__ == "__main__":
    main()
