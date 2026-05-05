#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import html
import json
import re
import time
from pathlib import Path
from typing import Any

START = time.time()

REPO = Path(".")
ENRICHED = Path("data/enriched/va_locations.enriched.json")
APPROVED = Path("data/approved/va_locations.json")
OUT_JSON = Path("data/enriched/va_locations.with_physical_addresses.json")
OUT_JSONL = Path("data/enriched/va_locations.with_physical_addresses.jsonl")
OUT_CSV = Path("data/enriched/va_locations.with_physical_addresses.csv")
EVIDENCE = Path("evidence/latest_physical_address_enrichment.json")

ADDRESS_KEYS = {
    "line1": ["line1", "address1", "address_line_1", "addressLine1", "street", "street1", "street_address", "streetAddress", "streetAddress1"],
    "line2": ["line2", "address2", "address_line_2", "addressLine2", "street2", "suite", "unit"],
    "city": ["city", "locality", "addressLocality", "municipality"],
    "state": ["state", "state_code", "province", "region", "addressRegion"],
    "postal_code": ["zip", "zipcode", "zip_code", "postal", "postal_code", "postalCode"],
    "country": ["country", "country_code", "addressCountry"],
}

PHONE_KEYS = ["phone", "main_phone", "phone_number", "telephone", "public_phone", "contact_phone"]

BRAND_REPLACEMENTS = [
    ("VA IaT Location Reference Catalog", "Public VA Facility Location Catalog"),
    ("VA-IaT Location Reference Catalog", "Public VA Facility Location Catalog"),
    ("VA IaT Location Catalog", "Public VA Facility Location Catalog"),
    ("VA-IaT Location Catalog", "Public VA Facility Location Catalog"),
    ("VA IaT", "Public VA Facility Catalog"),
    ("VA-IaT", "Public VA Facility Catalog"),
]

TEXT_SUFFIXES = {".md", ".html", ".txt", ".json", ".yml", ".yaml"}
SKIP_PARTS = {"data", ".git"}


def log(message: str) -> None:
    print(f"[{int(time.time() - START):04d}s] {message}", flush=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def first_value(d: dict[str, Any], keys: list[str]) -> str:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            v = d[k]
            if isinstance(v, dict):
                if "name" in v:
                    return str(v["name"]).strip()
                if "code" in v:
                    return str(v["code"]).strip()
            return str(v).strip()
    return ""


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"\s+", " ", text).strip(" \t\r\n,")
    return text


def normalize_address(value: Any, source: str, confidence: str) -> dict[str, str] | None:
    if not value:
        return None

    if isinstance(value, str):
        formatted = clean_text(value)
        if len(formatted) < 5:
            return None
        return {
            "line1": "",
            "line2": "",
            "city": "",
            "state": "",
            "postal_code": "",
            "country": "US",
            "formatted": formatted,
            "source": source,
            "confidence": confidence,
        }

    if not isinstance(value, dict):
        return None

    line1 = clean_text(first_value(value, ADDRESS_KEYS["line1"]))
    line2 = clean_text(first_value(value, ADDRESS_KEYS["line2"]))
    city = clean_text(first_value(value, ADDRESS_KEYS["city"]))
    state = clean_text(first_value(value, ADDRESS_KEYS["state"]))
    postal = clean_text(first_value(value, ADDRESS_KEYS["postal_code"]))
    country = clean_text(first_value(value, ADDRESS_KEYS["country"])) or "US"

    if isinstance(value.get("addressCountry"), dict):
        country = clean_text(value["addressCountry"].get("name") or value["addressCountry"].get("code") or country)

    parts = []
    if line1:
        parts.append(line1)
    if line2:
        parts.append(line2)
    tail = " ".join(x for x in [city + "," if city else "", state, postal] if x).strip()
    if tail:
        parts.append(tail)
    if country and country.upper() not in {"US", "USA", "UNITED STATES"}:
        parts.append(country)

    formatted = clean_text(", ".join(parts))
    if not formatted:
        formatted = clean_text(value.get("formatted") or value.get("full") or value.get("display") or "")
    if len(formatted) < 5:
        return None

    return {
        "line1": line1,
        "line2": line2,
        "city": city,
        "state": state,
        "postal_code": postal,
        "country": country,
        "formatted": formatted,
        "source": source,
        "confidence": confidence,
    }


def nested_candidates(record: dict[str, Any]) -> list[Any]:
    out: list[Any] = []
    out.append(record)
    for key in ["physical_address", "address", "mailing_address", "location", "attributes", "raw", "source_record"]:
        if key in record:
            out.append(record[key])
    for key in ["address", "mailingAddress", "physicalAddress"]:
        attrs = record.get("attributes")
        if isinstance(attrs, dict) and key in attrs:
            out.append(attrs[key])
    return out


def extract_address_from_record(record: dict[str, Any]) -> dict[str, str] | None:
    for candidate in nested_candidates(record):
        addr = normalize_address(candidate, "current_record", "record_field")
        if addr:
            return addr

    flat = {k: record.get(k) for keys in ADDRESS_KEYS.values() for k in keys if k in record}
    addr = normalize_address(flat, "current_record", "flattened_fields")
    if addr:
        return addr

    return None


def find_jsonld_addresses(text: str) -> list[dict[str, str]]:
    addresses: list[dict[str, str]] = []
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        text,
        flags=re.I | re.S,
    )

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if "address" in obj:
                addr = normalize_address(obj["address"], "public_facility_page_jsonld", "json_ld")
                if addr:
                    addresses.append(addr)
            if any(k in obj for k in ["streetAddress", "addressLocality", "addressRegion", "postalCode"]):
                addr = normalize_address(obj, "public_facility_page_jsonld", "json_ld")
                if addr:
                    addresses.append(addr)
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    for raw in scripts:
        body = html.unescape(raw).strip()
        body = re.sub(r"^\s*<!--", "", body)
        body = re.sub(r"-->\s*$", "", body)
        try:
            walk(json.loads(body))
        except Exception:
            continue

    return addresses


def find_regex_address(text: str) -> dict[str, str] | None:
    def rx(prop: str) -> str:
        m = re.search(rf'"{re.escape(prop)}"\s*:\s*"([^"]+)"', text, flags=re.I)
        if not m:
            m = re.search(rf'{re.escape(prop)}["\']?\s*[:=]\s*["\']([^"\']+)["\']', text, flags=re.I)
        return clean_text(m.group(1)) if m else ""

    candidate = {
        "streetAddress": rx("streetAddress"),
        "addressLocality": rx("addressLocality"),
        "addressRegion": rx("addressRegion"),
        "postalCode": rx("postalCode"),
        "addressCountry": rx("addressCountry") or "US",
    }
    return normalize_address(candidate, "public_facility_page_regex", "regex_schema_org")


def extract_address_from_html_file(path: Path) -> dict[str, str] | None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    for addr in find_jsonld_addresses(text):
        if addr:
            return addr

    return find_regex_address(text)


def build_html_address_map(records: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    ids = [str(r.get("facility_id", "")).strip().lower() for r in records if r.get("facility_id")]
    ids = sorted(set(ids), key=len, reverse=True)
    mapping: dict[str, dict[str, str]] = {}

    html_files = list(Path("data/raw/public_hours").glob("*/*.html"))
    log(f"PUBLIC_HOURS_HTML_FILES={len(html_files)}")

    for path in html_files:
        stem = path.stem.lower()
        matched = None
        for fid in ids:
            if stem == fid or stem.startswith(fid + "_"):
                matched = fid
                break
        if not matched or matched in mapping:
            continue
        addr = extract_address_from_html_file(path)
        if addr:
            mapping[matched] = addr

    return mapping


def extract_phone(record: dict[str, Any]) -> str:
    for key in PHONE_KEYS:
        if record.get(key):
            return clean_text(record.get(key))
    attrs = record.get("attributes")
    if isinstance(attrs, dict):
        for key in PHONE_KEYS:
            if attrs.get(key):
                return clean_text(attrs.get(key))
    return ""


def get_field(record: dict[str, Any], keys: list[str]) -> str:
    for k in keys:
        if record.get(k) not in (None, ""):
            return clean_text(record.get(k))
    return ""


def write_csv(records: list[dict[str, Any]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "facility_id",
        "name",
        "source_system",
        "station_code",
        "facility_type",
        "latitude",
        "longitude",
        "physical_address_formatted",
        "physical_address_line1",
        "physical_address_line2",
        "physical_address_city",
        "physical_address_state",
        "physical_address_postal_code",
        "physical_address_country",
        "physical_address_source",
        "physical_address_confidence",
        "public_phone",
        "website_url",
    ]

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in records:
            a = r.get("physical_address") if isinstance(r.get("physical_address"), dict) else {}
            writer.writerow({
                "facility_id": get_field(r, ["facility_id"]),
                "name": get_field(r, ["name", "title"]),
                "source_system": get_field(r, ["source_system", "source"]),
                "station_code": get_field(r, ["station_code", "station"]),
                "facility_type": get_field(r, ["facility_type", "type", "classification"]),
                "latitude": get_field(r, ["latitude", "lat"]),
                "longitude": get_field(r, ["longitude", "lon", "lng"]),
                "physical_address_formatted": a.get("formatted", ""),
                "physical_address_line1": a.get("line1", ""),
                "physical_address_line2": a.get("line2", ""),
                "physical_address_city": a.get("city", ""),
                "physical_address_state": a.get("state", ""),
                "physical_address_postal_code": a.get("postal_code", ""),
                "physical_address_country": a.get("country", ""),
                "physical_address_source": a.get("source", ""),
                "physical_address_confidence": a.get("confidence", ""),
                "public_phone": get_field(r, ["public_phone", "phone", "main_phone", "telephone"]),
                "website_url": get_field(r, ["website_url", "url", "source_url", "link"]),
            })


def patch_public_names() -> int:
    changed = 0
    for path in REPO.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue

        try:
            original = path.read_text(encoding="utf-8")
        except Exception:
            continue

        updated = original
        for old, new in BRAND_REPLACEMENTS:
            updated = updated.replace(old, new)

        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1

    naming_doc = Path("docs/PUBLIC_NAMING.md")
    naming_doc.write_text('''# Public Naming

Public-facing name:

```text
Public VA Facility Location Catalog
```

Internal working/repo name may remain:

```text
va-location-reference-catalog
```

Rationale:

- Keep `VA` because the catalog scope is public VA facility/location information.
- Remove `IaT` from the public name because it sounds like an internal architecture/product claim.
- Keep GitOps wording in architecture docs where it describes the operating model.
- Do not imply official VA production ownership, certification, or endorsement.
''', encoding="utf-8")
    changed += 1
    return changed


def write_addresses_page() -> None:
    page = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Public VA Facility Location Catalog - Addresses</title>
  <style>
    :root { color-scheme: dark; }
    body { margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #07111f; color: #eef5ff; }
    header { padding: 28px 32px; border-bottom: 1px solid #1d3557; background: #0b1728; }
    h1 { margin: 0 0 8px; font-size: 28px; }
    p { color: #b8c7da; }
    main { padding: 24px 32px; }
    .bar { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 18px; }
    input { min-width: 340px; max-width: 720px; flex: 1; padding: 12px 14px; border-radius: 10px; border: 1px solid #2a4468; background: #0e1c30; color: #eef5ff; }
    a { color: #7cc7ff; }
    .stats { color: #b8c7da; font-size: 14px; }
    table { width: 100%; border-collapse: collapse; background: #0b1728; border: 1px solid #1d3557; }
    th, td { text-align: left; vertical-align: top; padding: 10px 12px; border-bottom: 1px solid #162944; }
    th { position: sticky; top: 0; background: #10213a; z-index: 1; }
    tr:hover { background: #10213a; }
    .muted { color: #94a9c2; }
    .addr { max-width: 420px; }
    .nowrap { white-space: nowrap; }
  </style>
</head>
<body>
<header>
  <h1>Public VA Facility Location Catalog - Addresses</h1>
  <p>Public-source facility locations, coordinates, and physical-address enrichment. This is not an official VA production system.</p>
  <p><a href="./index.html">Main catalog</a> Â· <a href="./aliases-hours.html">Aliases and hours</a></p>
</header>
<main>
  <div class="bar">
    <input id="q" placeholder="Search name, city, state, station code, facility id, or address..." />
    <span class="stats" id="stats">Loading...</span>
  </div>
  <table>
    <thead>
      <tr>
        <th>Facility</th>
        <th>Station</th>
        <th>Physical address</th>
        <th>Coordinates</th>
        <th>Phone</th>
        <th>Source</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>
</main>
<script>
const DATA_URL = "./data/enriched/va_locations.with_physical_addresses.json";
const q = document.getElementById("q");
const rows = document.getElementById("rows");
const stats = document.getElementById("stats");
let records = [];

function field(r, names) {
  for (const n of names) {
    if (r[n] !== undefined && r[n] !== null && String(r[n]).trim() !== "") return String(r[n]);
  }
  return "";
}

function esc(s) {
  return String(s || "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function render() {
  const term = q.value.trim().toLowerCase();
  const filtered = records.filter(r => {
    if (!term) return true;
    const a = r.physical_address || {};
    return [
      field(r, ["facility_id"]),
      field(r, ["name", "title"]),
      field(r, ["station_code", "station"]),
      field(r, ["source_system", "source"]),
      field(r, ["facility_type", "type"]),
      a.formatted,
      a.city,
      a.state,
      a.postal_code,
      field(r, ["public_phone", "phone", "telephone"])
    ].join(" ").toLowerCase().includes(term);
  }).slice(0, 500);

  const addressCount = records.filter(r => r.physical_address && r.physical_address.formatted).length;
  stats.textContent = `${filtered.length} shown / ${records.length} total Â· ${addressCount} with physical address`;

  rows.innerHTML = filtered.map(r => {
    const a = r.physical_address || {};
    const lat = field(r, ["latitude", "lat"]);
    const lon = field(r, ["longitude", "lon", "lng"]);
    const url = field(r, ["website_url", "url", "source_url", "link"]);
    const name = field(r, ["name", "title"]);
    const fid = field(r, ["facility_id"]);
    const phone = field(r, ["public_phone", "phone", "telephone"]);
    return `<tr>
      <td><strong>${esc(name)}</strong><br><span class="muted">${esc(fid)}</span></td>
      <td class="nowrap">${esc(field(r, ["station_code", "station"]))}<br><span class="muted">${esc(field(r, ["source_system", "source"]))}</span></td>
      <td class="addr">${esc(a.formatted || "")}<br><span class="muted">${esc([a.line1, a.line2, a.city, a.state, a.postal_code].filter(Boolean).join(" Â· "))}</span></td>
      <td class="nowrap">${esc(lat)}, ${esc(lon)}</td>
      <td class="nowrap">${esc(phone)}</td>
      <td>${url ? `<a href="${esc(url)}" target="_blank" rel="noopener">public page</a>` : ""}<br><span class="muted">${esc(a.source || "")}</span></td>
    </tr>`;
  }).join("");
}

fetch(DATA_URL)
  .then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status} loading ${DATA_URL}`);
    return r.json();
  })
  .then(data => {
    records = Array.isArray(data) ? data : (data.records || []);
    render();
  })
  .catch(err => {
    stats.textContent = "Failed to load address data: " + err.message;
  });

q.addEventListener("input", render);
</script>
</body>
</html>
'''
    Path("addresses.html").write_text(page, encoding="utf-8")

    for html_file in [Path("index.html"), Path("aliases-hours.html")]:
        if html_file.exists():
            text = html_file.read_text(encoding="utf-8", errors="ignore")
            if "addresses.html" not in text:
                link = '\n<p><a href="./addresses.html">Physical address view</a></p>\n'
                if "</body>" in text:
                    text = text.replace("</body>", link + "</body>")
                else:
                    text += link
                html_file.write_text(text, encoding="utf-8")


def main() -> None:
    source_path = ENRICHED if ENRICHED.exists() else APPROVED
    if not source_path.exists():
        raise SystemExit("Missing catalog input. Expected data/enriched/va_locations.enriched.json or data/approved/va_locations.json")

    records = read_json(source_path)
    if not isinstance(records, list):
        raise SystemExit(f"Catalog is not a list: {source_path}")

    log(f"INPUT={source_path}")
    log(f"RECORD_COUNT={len(records)}")

    html_address_map = build_html_address_map(records)
    log(f"HTML_ADDRESS_MATCH_COUNT={len(html_address_map)}")

    with_address = 0
    record_field_count = 0
    html_count = 0
    phone_count = 0

    enriched_records: list[dict[str, Any]] = []

    for r in records:
        if not isinstance(r, dict):
            continue
        rr = dict(r)

        address = extract_address_from_record(rr)
        if address:
            record_field_count += 1
        else:
            fid = str(rr.get("facility_id", "")).strip().lower()
            address = html_address_map.get(fid)
            if address:
                html_count += 1

        if address:
            rr["physical_address"] = address
            with_address += 1
        else:
            rr["physical_address_status"] = "not_found_in_current_public_sources"

        phone = extract_phone(rr)
        if phone:
            rr["public_phone"] = phone
            phone_count += 1

        enriched_records.append(rr)

    write_json(OUT_JSON, enriched_records)
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSONL.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in enriched_records), encoding="utf-8")
    write_csv(enriched_records)

    if ENRICHED.exists():
        write_json(ENRICHED, enriched_records)

    write_addresses_page()
    naming_changes = patch_public_names()

    receipt = {
        "result": "PASS",
        "boundary": "public-source facility address enrichment only; no internal VA data; no patient, claimant, employee, ticket, CMDB, or credential data",
        "input": str(source_path),
        "outputs": [str(OUT_JSON), str(OUT_JSONL), str(OUT_CSV), "addresses.html"],
        "record_count": len(enriched_records),
        "records_with_physical_address": with_address,
        "record_field_address_count": record_field_count,
        "public_html_address_count": html_count,
        "public_phone_count": phone_count,
        "public_naming_files_changed_or_written": naming_changes,
        "created_utc": dt.datetime.now(dt.UTC).isoformat(),
    }
    write_json(EVIDENCE, receipt)

    log("ADDRESS_ENRICHMENT_RESULT=PASS")
    log(f"RECORDS_WITH_PHYSICAL_ADDRESS={with_address}")
    log(f"PUBLIC_PHONE_COUNT={phone_count}")
    log(f"EVIDENCE={EVIDENCE}")


if __name__ == "__main__":
    main()
