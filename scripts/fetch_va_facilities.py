#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

START = time.time()

def log(message: str) -> None:
    print(f"[{int(time.time() - START):04d}s] {message}", flush=True)

def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)

def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def fetch_url(url: str, api_key: str, accept: str) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(
        url,
        headers={
            "apikey": api_key,
            "Accept": accept,
            "User-Agent": "va-location-reference-catalog/2.0"
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return getattr(resp, "status", 200), resp.read(), {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), {k.lower(): v for k, v in exc.headers.items()}

def main() -> None:
    api_key = os.environ.get("VA_API_KEY", "").strip()
    if not api_key:
        fail("VA_API_KEY is required. Export it in your shell; do not commit it.")

    explicit_base = os.environ.get("VA_API_BASE", "").strip().rstrip("/")
    bases = [explicit_base] if explicit_base else [
        "https://api.va.gov/services/va_facilities/v1",
        "https://api.va.gov/services/va_facilities/v0",
    ]

    snapshot = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path("data/raw/va_facilities_api") / snapshot
    out_dir.mkdir(parents=True, exist_ok=True)

    last_error = None
    for base in bases:
        if not base:
            continue

        url = f"{base}/facilities/all"
        log(f"FETCH {url}")
        status, body, headers = fetch_url(url, api_key=api_key, accept="application/geo+json")

        meta = {
            "result": "PASS" if status == 200 else "FAIL",
            "source_system": "VA Facilities API",
            "source_url": url,
            "snapshot_utc": snapshot,
            "http_status": status,
            "content_type": headers.get("content-type"),
            "body_file": str(out_dir / "response.body")
        }

        (out_dir / "response.body").write_bytes(body)
        write_json(out_dir / "response.meta.json", meta)

        if status == 200:
            try:
                parsed = json.loads(body.decode("utf-8"))
            except Exception as exc:
                fail(f"HTTP 200 returned non-JSON body saved at {out_dir / 'response.body'}: {exc}")

            write_json(out_dir / "facilities.geojson", parsed)
            Path("data/raw/va_facilities_api/latest_snapshot.txt").write_text(str(out_dir) + "\n", encoding="utf-8")
            write_json(Path("evidence/latest_fetch.json"), meta)
            log(f"PASS raw snapshot: {out_dir}")
            return

        last_error = f"{url} returned HTTP {status}; body saved at {out_dir / 'response.body'}"
        log(last_error)

    fail(last_error or "No API base succeeded.")

if __name__ == "__main__":
    main()
