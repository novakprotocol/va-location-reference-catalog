# Run Now — Local Population Workflow

This runbook populates the catalog from the public VA Facilities API using a local shell environment variable.

## Do not commit secrets

```text
VA_API_KEY must only exist in your shell environment.
Do not write VA_API_KEY into .env, scripts, docs, screenshots, logs, tickets, or GitHub comments.
```

## Windows PowerShell run

From a fresh PowerShell window:

```powershell
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

cd "$env:USERPROFILE\Desktop\VA-IaT-LocationCatalog-Pilot\va-location-reference-catalog"

git checkout main
git pull --ff-only origin main

git checkout -B work/populate-public-va-facilities-$(Get-Date -Format yyyyMMdd-HHmmss)

$env:VA_API_KEY = '<paste-api-key-here-for-this-shell-only>'
python scripts/fetch_va_facilities.py
python scripts/normalize_va_facilities.py
python scripts/validate_catalog.py
python scripts/build_release_candidate.py

Remove-Item Env:\VA_API_KEY -ErrorAction SilentlyContinue

git status --short
```

## Review before commit

```powershell
git diff --stat
git diff -- data/normalized data/approved evidence
```

Confirm:

- No credentials.
- No tokens.
- No PII/PHI.
- No internal VA exports.
- No ServiceNow or CMDB exports.
- Generated evidence receipts exist.

## Commit and push

```powershell
git add data evidence
git commit -m "data: add public VA facilities catalog candidate"
git push -u origin HEAD

gh pr create `
  --title "data: add public VA facilities catalog candidate" `
  --body "Public-source-only catalog candidate generated locally. Requires owner review before approval." `
  --base main `
  --head (git branch --show-current)
```

## Expected outputs

```text
data/raw/va_facilities_api/<snapshot>/facilities_all.geojson
data/raw/va_facilities_api/<snapshot>/source_manifest.json
data/normalized/va_locations.json
data/normalized/va_locations.csv
data/normalized/va_locations.jsonl
data/normalized/index_by_facility_id.json
data/normalized/index_by_station_code.json
data/approved/va_locations.json
data/approved/checksums.sha256
data/approved/release_manifest.json
evidence/latest_fetch.json
evidence/latest_normalization.json
evidence/latest_validation.json
evidence/latest_release_manifest.json
```
