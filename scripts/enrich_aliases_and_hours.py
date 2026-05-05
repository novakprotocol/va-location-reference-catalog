#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

START = time.time()
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_RE = re.compile(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun):\s*([^\n\r<]+)", re.I)
TAG_RE = re.compile(r"<[^>]+>")


def log(message: str) -> None:
    print(f"[{int(time.time() - START):04d}s] {message}", flush=True)


def now_utc() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def normalize(value: Any) -> str:
    return clean_text(value).lower()


def safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "_", value.lower()).strip("_")[:120] or "source"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def record_search_text(record: dict[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, default=str).lower()


def download(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VA-IaT-LocationCatalog-Pilot/1.0 alias-hours-enrichment",
            "Accept": "text/html,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as response:  # noqa: S310 - public official pages only
        return response.read().decode("utf-8", errors="ignore")


def html_to_text(page: str) -> str:
    page = re.sub(r"(?i)<br\s*/?>", "\n", page)
    page = re.sub(r"(?i)</(p|li|h1|h2|h3|h4|div|section|tr)>", "\n", page)
    text = TAG_RE.sub(" ", page)
    return html.unescape(text).replace("\r", "\n")


def extract_facility_hours(page: str) -> dict[str, Any]:
    text = html_to_text(page)
    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
    start_idx = None
    for idx, line in enumerate(lines):
        lower = line.lower()
        if lower in {"facility hours", "office hours"} or lower.endswith("facility hours") or lower.endswith("office hours"):
            start_idx = idx
            break
    if start_idx is None:
        for idx, line in enumerate(lines):
            lower = line.lower()
            if "facility hours" in lower or "office hours" in lower:
                start_idx = idx
                break

    search_block = "\n".join(lines[start_idx:start_idx + 35] if start_idx is not None else lines[:120])
    matches = DAY_RE.findall(search_block)
    hours = {}
    for day, value in matches:
        norm_day = day[:3].title()
        if norm_day in DAYS:
            hours[norm_day] = clean_text(value)

    # Some VA.gov pages state open/closed language without seven day rows.
    if not hours:
        open_247 = re.search(r"\b(open\s+24\s*/\s*7|24\s+hours|24/7)\b", search_block, re.I)
        if open_247:
            hours = {day: "Open 24 hours" for day in DAYS}

    return {
        "hours": hours,
        "confidence": "public_page_facility_hours" if len(hours) >= 5 else "not_found_or_partial",
        "raw_hint": search_block[:1000],
    }


def record_matches_seed(record: dict[str, Any], seed: dict[str, Any]) -> bool:
    match = seed.get("match", {})
    if not isinstance(match, dict):
        return False

    station_code = normalize(match.get("station_code"))
    name_contains = normalize(match.get("name_contains"))
    facility_id = normalize(match.get("facility_id"))
    website_contains = normalize(match.get("website_contains"))
    any_contains = normalize(match.get("any_contains"))

    record_station = normalize(record.get("station_code"))
    record_name = normalize(record.get("name"))
    record_facility_id = normalize(record.get("facility_id"))
    record_website = normalize(record.get("website"))
    record_all = record_search_text(record)

    if facility_id and facility_id != record_facility_id:
        return False
    if station_code and station_code != record_station:
        return False
    if name_contains and name_contains not in record_name:
        return False
    if website_contains and website_contains not in record_website:
        return False
    if any_contains and any_contains not in record_all:
        return False
    return bool(station_code or name_contains or facility_id or website_contains or any_contains)


def apply_aliases(records: list[dict[str, Any]], seed_path: Path) -> int:
    if not seed_path.exists():
        log(f"ALIAS_SEED_NOT_FOUND={seed_path}")
        return 0
    seed = read_json(seed_path)
    aliases = seed.get("aliases", []) if isinstance(seed, dict) else []
    count = 0
    for record in records:
        current = record.setdefault("site_aliases", [])
        for item in aliases:
            if not isinstance(item, dict):
                continue
            if not record_matches_seed(record, item):
                continue
            alias_payload = {
                "alias": clean_text(item.get("alias")).upper(),
                "meaning": clean_text(item.get("meaning")),
                "alias_type": clean_text(item.get("alias_type")) or "local_mnemonic",
                "confidence": clean_text(item.get("confidence")) or "review_pending",
                "source_reference": clean_text(item.get("source_reference")) or "manual_seed",
                "review_state": clean_text(item.get("review_state")) or "review_pending",
            }
            if alias_payload["alias"] and alias_payload not in current:
                current.append(alias_payload)
                count += 1
        record["alias_search_terms"] = sorted({a.get("alias", "") for a in current if a.get("alias")} | {a.get("meaning", "") for a in current if a.get("meaning")})
    return count


def filter_records(records: list[dict[str, Any]], *, facility_ids: list[str], station_codes: list[str], queries: list[str]) -> list[dict[str, Any]]:
    facility_set = {normalize(v) for v in facility_ids if normalize(v)}
    station_set = {normalize(v) for v in station_codes if normalize(v)}
    query_terms = [normalize(v) for v in queries if normalize(v)]

    if not facility_set and not station_set and not query_terms:
        return records

    selected = []
    for record in records:
        facility_id = normalize(record.get("facility_id"))
        station_code = normalize(record.get("station_code"))
        searchable = record_search_text(record)
        if facility_set and facility_id in facility_set:
            selected.append(record)
            continue
        if station_set and station_code in station_set:
            selected.append(record)
            continue
        if query_terms and all(term in searchable for term in query_terms):
            selected.append(record)
            continue
    return selected


def enrich_hours(records: list[dict[str, Any]], *, limit: int, sleep_seconds: float, raw_root: Path) -> int:
    enriched = 0
    fetched = 0
    for record in records:
        if limit and fetched >= limit:
            break
        url = clean_text(record.get("website")) or clean_text(record.get("source_url"))
        if not url or not url.lower().startswith("http"):
            record.setdefault("facility_hours", None)
            record["facility_hours_confidence"] = "no_public_location_url"
            continue
        try:
            log(f"FETCH_HOURS {record.get('facility_id')} station={record.get('station_code')} {url}")
            page = download(url)
            fetched += 1
            raw_path = raw_root / f"{safe_name(clean_text(record.get('facility_id')))}_{safe_name(clean_text(record.get('name')))}.html"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(page, encoding="utf-8")
            parsed = extract_facility_hours(page)
            record["facility_hours"] = parsed["hours"] or None
            record["facility_hours_confidence"] = parsed["confidence"]
            record["facility_hours_source_url"] = url
            record["facility_hours_raw_sha256"] = sha256_text(page)
            record["facility_hours_raw_file"] = str(raw_path)
            if parsed["hours"]:
                enriched += 1
        except Exception as exc:  # keep bulk enrichment moving
            record["facility_hours"] = None
            record["facility_hours_confidence"] = "fetch_failed"
            record["facility_hours_error"] = str(exc)[:250]
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(description="Add human-reviewed aliases and public VA.gov facility hours to catalog records.")
    parser.add_argument("--input", default="data/approved/va_locations.json")
    parser.add_argument("--alias-seed", default="config/site_alias_seed.json")
    parser.add_argument("--output", default="data/enriched/va_locations.enriched.json")
    parser.add_argument("--download-hours", action="store_true")
    parser.add_argument("--hours-limit", type=int, default=0, help="0 means all selected records with a public URL")
    parser.add_argument("--facility-id", action="append", default=[], help="Only fetch hours for matching facility_id. May be repeated.")
    parser.add_argument("--station-code", action="append", default=[], help="Only fetch hours for matching station_code. May be repeated.")
    parser.add_argument("--query", action="append", default=[], help="Only fetch hours for records containing this text. May be repeated.")
    parser.add_argument("--sleep", type=float, default=0.25)
    args = parser.parse_args()

    input_path = Path(args.input)
    records = read_json(input_path)
    if not isinstance(records, list):
        raise SystemExit("Input catalog must be a JSON array.")

    alias_count = apply_aliases(records, Path(args.alias_seed))
    selected_records = filter_records(records, facility_ids=args.facility_id, station_codes=args.station_code, queries=args.query)
    raw_root = Path("data/raw/public_hours") / dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    hours_count = enrich_hours(selected_records, limit=args.hours_limit, sleep_seconds=args.sleep, raw_root=raw_root) if args.download_hours else 0

    output_path = Path(args.output)
    write_json(output_path, records)
    receipt = {
        "result": "PASS",
        "input": str(input_path),
        "output": str(output_path),
        "alias_seed": args.alias_seed,
        "record_count": len(records),
        "selected_record_count": len(selected_records),
        "selected_facility_ids": args.facility_id,
        "selected_station_codes": args.station_code,
        "selected_queries": args.query,
        "alias_assignment_count": alias_count,
        "hours_enriched_count": hours_count,
        "download_hours": bool(args.download_hours),
        "hours_limit": args.hours_limit,
        "created_utc": now_utc(),
        "boundary": "public-source and human-reviewed alias enrichment only",
    }
    write_json(Path("evidence/latest_alias_hours_enrichment.json"), receipt)
    log("ENRICH_ALIAS_HOURS_RESULT=PASS")
    log(f"RECORD_COUNT={len(records)}")
    log(f"SELECTED_RECORD_COUNT={len(selected_records)}")
    log(f"ALIAS_ASSIGNMENT_COUNT={alias_count}")
    log(f"HOURS_ENRICHED_COUNT={hours_count}")
    log(f"OUTPUT={output_path}")


if __name__ == "__main__":
    main()
