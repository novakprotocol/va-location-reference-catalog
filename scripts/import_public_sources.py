#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

START = time.time()

EXPECTED_HEADERS = [
    "facility id",
    "name",
    "city",
    "state",
    "latitude",
    "longitude",
    "classification",
    "visn",
    "facility type",
    "website",
]

STATE_RE = re.compile(r"^[A-Z]{2}$")
URL_RE = re.compile(r"https?://\S+", re.I)


def log(message: str) -> None:
    print(f"[{int(time.time() - START):04d}s] {message}", flush=True)


def now_utc() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def stamp_utc() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_url(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VA-IaT-LocationCatalog-Pilot/1.0 public-source-import",
            "Accept": "text/html,application/json,text/csv,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:  # noqa: S310 - public source import only
        data = response.read()
    dest.write_bytes(data)


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell_parts: list[str] = []
        self._current_href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_table and self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell_parts = []
            self._current_href = None
        elif self._in_cell and tag == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href")
            if href:
                self._current_href = href

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._in_cell:
            text = " ".join(" ".join(self._current_cell_parts).split())
            if self._current_href and not URL_RE.search(text):
                text = self._current_href
            self._current_row.append(html.unescape(text).strip())
            self._in_cell = False
            self._current_cell_parts = []
            self._current_href = None
        elif tag == "tr" and self._in_row:
            if any(cell for cell in self._current_row):
                self._current_table.append(self._current_row)
            self._in_row = False
            self._current_row = []
        elif tag == "table" and self._in_table:
            if self._current_table:
                self.tables.append(self._current_table)
            self._in_table = False
            self._current_table = []


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def normalize_coordinate(value: str, limit: float) -> float | None:
    raw = clean_text(value)
    if not raw:
        return None
    raw = raw.replace(",00", "")
    negative = raw.startswith("-")
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    number = float(digits)
    while number > limit and number >= 10:
        number = number / 10.0
    if negative:
        number = -number
    if abs(number) > limit:
        return None
    return round(number, 8)


def derive_station_code(facility_id: str) -> tuple[str | None, str]:
    value = clean_text(facility_id)
    if not value:
        return None, "not_available"
    # Examples: vba_306, vha_402GA, vc_0141V, nca_042. Keep the authoritative facility_id intact.
    match = re.search(r"_(\d+[A-Z]*)$", value, re.I)
    if match:
        return match.group(1), "derived"
    return None, "not_available"


def row_to_record(row: dict[str, str], *, source_system: str, raw_source_file: str, source_url: str | None, snapshot_utc: str, catalog_version: str) -> dict[str, Any]:
    facility_id = clean_text(row.get("facility id") or row.get("facility_id") or row.get("id"))
    name = clean_text(row.get("name"))
    city = clean_text(row.get("city"))
    state = clean_text(row.get("state"))
    classification = clean_text(row.get("classification")) or None
    visn = clean_text(row.get("visn")) or None
    facility_type = clean_text(row.get("facility type") or row.get("facility_type")) or None
    website = clean_text(row.get("website")) or None
    lat = normalize_coordinate(clean_text(row.get("latitude")), 90.0)
    long = normalize_coordinate(clean_text(row.get("longitude")), 180.0)
    station_code, station_confidence = derive_station_code(facility_id)

    return {
        "schema_version": "1.0.0",
        "catalog_version": catalog_version,
        "lineage_id": hashlib.sha256(f"{source_system}|{facility_id}|{name}|{city}|{state}".encode("utf-8")).hexdigest(),
        "facility_id": facility_id,
        "source_system": source_system,
        "source_snapshot_utc": snapshot_utc,
        "source_url": source_url,
        "raw_source_file": raw_source_file,
        "name": name,
        "facility_type": facility_type,
        "classification": classification,
        "visn": visn,
        "station_code": station_code,
        "station_code_confidence": station_confidence,
        "approval_state": "review_pending",
        "approved_for": [],
        "not_approved_for": ["direct production write-back", "patient lookup", "employee lookup", "clinical workflow"],
        "address": {
            "city": city or None,
            "state": state or None,
            "street": None,
            "postal_code": None,
            "country": "US",
        },
        "phone": None,
        "website": website,
        "lat": lat,
        "long": long,
        "operating_status": None,
    }


def parse_html_table(path: Path, *, source_system: str, source_url: str | None, snapshot_utc: str, catalog_version: str) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    parser = TableParser()
    parser.feed(text)
    records: list[dict[str, Any]] = []

    for table in parser.tables:
        if not table:
            continue
        header = [clean_text(cell).lower() for cell in table[0]]
        if not {"facility id", "name", "city", "state"}.issubset(set(header)):
            continue
        for row in table[1:]:
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            row_dict = {header[idx]: clean_text(row[idx]) for idx in range(len(header))}
            if not row_dict.get("facility id") or not row_dict.get("name"):
                continue
            records.append(row_to_record(row_dict, source_system=source_system, raw_source_file=str(path), source_url=source_url, snapshot_utc=snapshot_utc, catalog_version=catalog_version))

    return records


def parse_csv(path: Path, *, source_system: str, source_url: str | None, snapshot_utc: str, catalog_version: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = {clean_text(k).lower(): clean_text(v) for k, v in row.items() if k is not None}
            if not normalized.get("facility id") and normalized.get("facility_id"):
                normalized["facility id"] = normalized["facility_id"]
            if not normalized.get("facility id") or not normalized.get("name"):
                continue
            records.append(row_to_record(normalized, source_system=source_system, raw_source_file=str(path), source_url=source_url, snapshot_utc=snapshot_utc, catalog_version=catalog_version))
    return records


def parse_json(path: Path, *, source_system: str, source_url: str | None, snapshot_utc: str, catalog_version: str) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidates: list[Any] = []
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        for key in ("data", "records", "facilities", "items", "results"):
            if isinstance(payload.get(key), list):
                candidates = payload[key]
                break
    records: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        normalized = {clean_text(k).lower().replace("_", " "): clean_text(v) for k, v in item.items() if isinstance(k, str)}
        if not normalized.get("facility id") and item.get("facility_id"):
            normalized["facility id"] = clean_text(item.get("facility_id"))
        if not normalized.get("name") and item.get("attributes") and isinstance(item["attributes"], dict):
            attrs = item["attributes"]
            normalized.update({clean_text(k).lower().replace("_", " "): clean_text(v) for k, v in attrs.items() if isinstance(k, str)})
        if not normalized.get("facility id") or not normalized.get("name"):
            continue
        records.append(row_to_record(normalized, source_system=source_system, raw_source_file=str(path), source_url=source_url, snapshot_utc=snapshot_utc, catalog_version=catalog_version))
    return records


def parse_source_file(path: Path, *, source_system: str, source_url: str | None, snapshot_utc: str, catalog_version: str) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm", ".txt"}:
        return parse_html_table(path, source_system=source_system, source_url=source_url, snapshot_utc=snapshot_utc, catalog_version=catalog_version)
    if suffix == ".csv":
        return parse_csv(path, source_system=source_system, source_url=source_url, snapshot_utc=snapshot_utc, catalog_version=catalog_version)
    if suffix == ".json":
        return parse_json(path, source_system=source_system, source_url=source_url, snapshot_utc=snapshot_utc, catalog_version=catalog_version)
    raise SystemExit(f"Unsupported source file type: {path}")


def write_outputs(records: list[dict[str, Any]], *, source_receipts: list[dict[str, Any]], snapshot_utc: str, catalog_version: str) -> None:
    if not records:
        raise SystemExit("No importable facility records were found. Use a supported public HTML/CSV/JSON source.")

    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        by_id[record["facility_id"]] = record
    records = [by_id[key] for key in sorted(by_id)]

    out = Path("data/normalized")
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "va_locations.json", records)

    fields = [
        "facility_id", "name", "facility_type", "classification", "visn", "station_code", "station_code_confidence",
        "approval_state", "source_system", "source_snapshot_utc", "source_url", "website", "lat", "long"
    ]
    with (out / "va_locations.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = {field: record.get(field) for field in fields}
            writer.writerow(row)

    with (out / "va_locations.jsonl").open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    write_json(out / "index_by_facility_id.json", {record["facility_id"]: idx for idx, record in enumerate(records)})
    write_json(out / "index_by_station_code.json", {record["station_code"]: record["facility_id"] for record in records if record.get("station_code")})
    write_json(out / "unmatched_station_codes.json", [record["facility_id"] for record in records if not record.get("station_code")])

    receipt = {
        "result": "PASS",
        "catalog_version": catalog_version,
        "source_snapshot_utc": snapshot_utc,
        "record_count": len(records),
        "source_receipts": source_receipts,
        "outputs": [
            "data/normalized/va_locations.json",
            "data/normalized/va_locations.csv",
            "data/normalized/va_locations.jsonl",
            "data/normalized/index_by_facility_id.json",
            "data/normalized/index_by_station_code.json",
            "data/normalized/unmatched_station_codes.json",
        ],
        "created_utc": now_utc(),
    }
    write_json(Path("evidence/latest_import_public_sources.json"), receipt)
    log(f"IMPORT_RESULT=PASS")
    log(f"RECORD_COUNT={len(records)}")
    log(f"CATALOG_VERSION={catalog_version}")


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Import public no-key VA facility source files into normalized catalog outputs.")
    parser.add_argument("--manifest", default="config/public_sources.json")
    parser.add_argument("--download", action="store_true", help="Download preferred public sources from manifest before import.")
    parser.add_argument("--source-file", action="append", default=[], help="Local public source file to import. May be repeated.")
    parser.add_argument("--source-url", default=None, help="Optional provenance URL for --source-file.")
    parser.add_argument("--source-system", default="local_public_source_drop")
    args = parser.parse_args()

    snapshot_utc = now_utc()
    catalog_version = dt.datetime.now(dt.UTC).strftime("%Y.%m.%d.1")
    source_receipts: list[dict[str, Any]] = []
    source_files: list[tuple[Path, str, str | None]] = []

    if args.download:
        manifest = load_manifest(Path(args.manifest))
        raw_root = Path("data/raw/public_sources") / stamp_utc()
        for source in manifest.get("sources", []):
            if not source.get("preferred_for_day0"):
                continue
            url = source["url"]
            source_id = source["source_id"]
            dest = raw_root / f"{source_id}.html"
            log(f"DOWNLOAD {url}")
            download_url(url, dest)
            source_receipts.append({
                "source_id": source_id,
                "source_url": url,
                "local_path": str(dest),
                "sha256": sha256_file(dest),
                "bytes": dest.stat().st_size,
                "downloaded_utc": now_utc(),
            })
            source_files.append((dest, source_id, url))

    for src in args.source_file:
        path = Path(src)
        if not path.exists():
            raise SystemExit(f"Source file not found: {path}")
        source_receipts.append({
            "source_id": args.source_system,
            "source_url": args.source_url,
            "local_path": str(path),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "loaded_utc": now_utc(),
        })
        source_files.append((path, args.source_system, args.source_url))

    if not source_files:
        raise SystemExit("No source files selected. Use --download or --source-file.")

    all_records: list[dict[str, Any]] = []
    for path, source_system, source_url in source_files:
        log(f"IMPORT {path}")
        imported = parse_source_file(path, source_system=source_system, source_url=source_url, snapshot_utc=snapshot_utc, catalog_version=catalog_version)
        log(f"SOURCE_RECORDS={len(imported)} source={path}")
        all_records.extend(imported)

    write_outputs(all_records, source_receipts=source_receipts, snapshot_utc=snapshot_utc, catalog_version=catalog_version)


if __name__ == "__main__":
    main()
