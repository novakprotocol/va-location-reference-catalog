import argparse
import csv
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PARSER_VERSION = "public-contact-hours-candidates-v1"
NATIONAL_OR_SHARED_NUMBERS = {
    "800-698-2411",
    "800-827-1000",
    "800-535-1117",
    "800-799-4889",
    "866-900-6417",
    "877-222-8387",
    "988",
}

PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}(?!\d)")
HOURS_HINT_RE = re.compile(
    r"(visitation hours|office hours|hours:|open daily|open\s+(?:monday|mon|tuesday|tue|wednesday|wed|thursday|thu|friday|fri|saturday|sat|sunday|sun)|closed federal holidays|sunrise to sunset)",
    re.IGNORECASE,
)

def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return ""
    return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"

def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()

def extract_hours_lines(raw_html: str) -> list[str]:
    text = clean_text(raw_html)
    chunks = re.split(r"(?<=[.!?])\s+|\s{2,}", text)
    out: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        c = chunk.strip(" \t\r\n-â€“â€”:;")
        if not c:
            continue
        if HOURS_HINT_RE.search(c):
            if len(c) > 260:
                # Try to clip to the meaningful part.
                m = HOURS_HINT_RE.search(c)
                start = max(0, (m.start() if m else 0) - 40)
                c = c[start:start+260].strip()
            if c not in seen:
                out.append(c)
                seen.add(c)
        if len(out) >= 8:
            break
    return out

def extract_phone_candidates(raw_html: str) -> list[dict[str, Any]]:
    text = clean_text(raw_html)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in PHONE_RE.finditer(text):
        phone = normalize_phone(m.group(0))
        if not phone or phone in seen:
            continue
        start = max(0, m.start() - 90)
        end = min(len(text), m.end() + 90)
        context = text[start:end].strip()
        lowered = context.lower()
        if phone in NATIONAL_OR_SHARED_NUMBERS:
            role = "national_or_shared"
            confidence = "low"
        elif any(word in lowered for word in ["fax", "tty"]):
            role = "possibly_non_primary"
            confidence = "low"
        elif any(word in lowered for word in ["office", "phone", "call", "cemetery", "administration", "national cemetery"]):
            role = "facility_contact_candidate"
            confidence = "medium"
        else:
            role = "contact_candidate"
            confidence = "low"
        candidates.append({
            "phone": phone,
            "role": role,
            "confidence": confidence,
            "context": context[:260],
        })
        seen.add(phone)
    return candidates

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def load_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        data = data.get("records") or data.get("facilities") or data.get("locations") or []
    if not isinstance(data, list):
        raise ValueError(f"Expected list-like records in {path}")
    return [r for r in data if isinstance(r, dict)]

def safe_slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value[:80] or "page"

def fetch_url(url: str, out_path: Path, timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 VA-LocationReferenceCatalog public-source candidate enrichment",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            out_path.write_bytes(body)
            return {
                "ok": True,
                "http_status": getattr(resp, "status", None),
                "content_type": resp.headers.get("content-type"),
                "bytes": len(body),
                "elapsed_ms": int((time.time() - started) * 1000),
                "error": None,
            }
    except Exception as e:
        return {
            "ok": False,
            "http_status": getattr(e, "code", None),
            "content_type": None,
            "bytes": 0,
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": f"{type(e).__name__}: {e}",
        }

def is_public_http_url(url: Any) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--input", default="data/enriched/va_locations.with_physical_addresses.json")
    ap.add_argument("--out-json", default="data/enriched/va_locations.contact_hours_candidates.json")
    ap.add_argument("--out-jsonl", default="data/enriched/va_locations.contact_hours_candidates.jsonl")
    ap.add_argument("--out-csv", default="data/enriched/va_locations.contact_hours_candidates.csv")
    ap.add_argument("--evidence", default="evidence/latest_public_contact_hours_candidates.json")
    ap.add_argument("--raw-dir", default=None)
    args = ap.parse_args()

    input_path = Path(args.input)
    records = load_records(input_path)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    raw_dir = Path(args.raw_dir) if args.raw_dir else Path("data/raw/public_contact_hours_candidates") / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)

    selected = []
    seen_urls = set()
    for r in records:
        url = r.get("facility_hours_source_url") or r.get("website")
        if not is_public_http_url(url) or url in seen_urls:
            continue
        selected.append(r)
        seen_urls.add(url)
        if args.limit and len(selected) >= args.limit:
            break

    enriched = []
    flat_rows = []
    fetch_failures = 0
    fetched = 0
    pages_with_phone = 0
    pages_with_hours = 0
    total_phone_candidates = 0
    total_hours_candidates = 0
    samples = []

    for idx, r in enumerate(selected, start=1):
        url = r.get("facility_hours_source_url") or r.get("website")
        facility_id = r.get("facility_id") or f"unknown_{idx:04d}"
        filename = f"{idx:04d}_{safe_slug(str(facility_id))}_{safe_slug(Path(urllib.parse.urlparse(url).path).name or 'index.html')}"
        raw_path = raw_dir / filename

        result = fetch_url(url, raw_path, args.timeout)
        base = {
            "facility_id": r.get("facility_id"),
            "name": r.get("name"),
            "facility_type": r.get("facility_type"),
            "visn": r.get("visn"),
            "station_code": r.get("station_code"),
            "website": r.get("website"),
            "source_url": r.get("source_url"),
            "candidate_source_url": url,
            "parser_version": PARSER_VERSION,
            "extracted_utc": stamp,
            "review_status": "candidate_not_approved",
            "approved_for_direct_phone_field": False,
            "approved_for_direct_hours_field": False,
            "raw_file": str(raw_path) if result["ok"] else None,
            "raw_sha256": sha256_file(raw_path) if result["ok"] and raw_path.exists() else None,
            "fetch": result,
            "phone_candidates": [],
            "hours_candidates": [],
        }

        if not result["ok"]:
            fetch_failures += 1
            enriched.append(base)
            continue

        fetched += 1
        raw_html = raw_path.read_text(encoding="utf-8", errors="replace")
        phone_candidates = extract_phone_candidates(raw_html)
        hours_candidates = extract_hours_lines(raw_html)

        base["phone_candidates"] = phone_candidates
        base["hours_candidates"] = [
            {
                "text": h,
                "confidence": "medium" if ("visitation hours" in h.lower() or "office hours" in h.lower()) else "low",
            }
            for h in hours_candidates
        ]

        if phone_candidates:
            pages_with_phone += 1
        if hours_candidates:
            pages_with_hours += 1

        total_phone_candidates += len(phone_candidates)
        total_hours_candidates += len(hours_candidates)

        for pc in phone_candidates:
            flat_rows.append({
                "facility_id": base["facility_id"],
                "name": base["name"],
                "candidate_type": "phone",
                "candidate_value": pc["phone"],
                "confidence": pc["confidence"],
                "role": pc["role"],
                "candidate_source_url": url,
                "raw_sha256": base["raw_sha256"],
                "review_status": base["review_status"],
            })

        for hc in base["hours_candidates"]:
            flat_rows.append({
                "facility_id": base["facility_id"],
                "name": base["name"],
                "candidate_type": "hours",
                "candidate_value": hc["text"],
                "confidence": hc["confidence"],
                "role": "facility_hours_candidate",
                "candidate_source_url": url,
                "raw_sha256": base["raw_sha256"],
                "review_status": base["review_status"],
            })

        if (phone_candidates or hours_candidates) and len(samples) < 10:
            samples.append({
                "facility_id": base["facility_id"],
                "name": base["name"],
                "candidate_source_url": url,
                "phone_candidates": phone_candidates[:8],
                "hours_candidates": base["hours_candidates"][:8],
            })

        enriched.append(base)

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")

    out_jsonl = Path(args.out_jsonl)
    out_jsonl.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in enriched) + "\n", encoding="utf-8")

    out_csv = Path(args.out_csv)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "facility_id", "name", "candidate_type", "candidate_value", "confidence", "role",
            "candidate_source_url", "raw_sha256", "review_status"
        ])
        writer.writeheader()
        writer.writerows(flat_rows)

    evidence = {
        "result": "PASS",
        "parser_version": PARSER_VERSION,
        "run_started_utc": stamp,
        "run_finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_path": str(input_path),
        "record_count": len(records),
        "selected_count": len(selected),
        "fetched": fetched,
        "fetch_failed": fetch_failures,
        "pages_with_phone_candidates": pages_with_phone,
        "pages_with_hours_candidates": pages_with_hours,
        "total_phone_candidates": total_phone_candidates,
        "total_hours_candidates": total_hours_candidates,
        "outputs": {
            "json": str(out_json),
            "jsonl": str(out_jsonl),
            "csv": str(out_csv),
            "raw_dir": str(raw_dir),
        },
        "candidate_policy": {
            "approved_direct_field_mutation": False,
            "reason": "Candidates require review. National/shared numbers are tagged and not promoted directly.",
        },
        "samples": samples,
    }

    evidence_path = Path(args.evidence)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())