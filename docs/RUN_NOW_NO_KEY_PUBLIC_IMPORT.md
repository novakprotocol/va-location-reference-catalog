# Run Now: No-Key Public Import

This path replaces the API-key Day0 path for the private pilot.

## Why

The live VA Facilities API path can require a VA API key or license/token approval. That is not a good dependency for a private pilot. This lane imports public, no-key sources instead.

## Public source candidates

The first preferred source is listed in:

```text
config/public_sources.json
```

Preferred Day0 source:

```text
https://discover.va.gov/va-locator-facility-list/
```

The VA.gov Directory is also a public corroborating reference:

```text
https://www.va.gov/directory/
```

## Option A: Import directly from configured public no-key source

Run from the repo root:

```powershell
cd "$env:USERPROFILE\Desktop\VA-IaT-LocationCatalog-Pilot\va-location-reference-catalog"

git checkout main
git pull --ff-only origin main

git checkout -B work/no-key-public-source-import-local-run
python .\scripts\import_public_sources.py --download
python .\scripts\validate_catalog.py
python .\scripts\build_release_candidate.py

git status --short
```

If the generated data looks good:

```powershell
git add data\raw data\normalized data\approved evidence
git commit -m "data: import no-key public VA facility catalog candidate"
git push -u origin work/no-key-public-source-import-local-run
gh pr create --repo novakprotocol/va-location-reference-catalog --base main --head work/no-key-public-source-import-local-run --title "data: import no-key public VA facility catalog candidate" --body "No-key public-source import. No VA API key used. Human review required."
```

## Option B: Import a local HTML/CSV/JSON file

Save or download a public-only source file, then run:

```powershell
cd "$env:USERPROFILE\Desktop\VA-IaT-LocationCatalog-Pilot\va-location-reference-catalog"

git checkout main
git pull --ff-only origin main

git checkout -B work/no-key-local-source-import-local-run
python .\scripts\import_public_sources.py --source-file "$env:USERPROFILE\Downloads\YOUR_PUBLIC_SOURCE_FILE.html" --source-url "https://public-source-url.example" --source-system "manual_public_source_drop"
python .\scripts\validate_catalog.py
python .\scripts\build_release_candidate.py

git status --short
```

Then commit and open a PR:

```powershell
git add data\raw data\normalized data\approved evidence
git commit -m "data: import local public VA facility source candidate"
git push -u origin work/no-key-local-source-import-local-run
gh pr create --repo novakprotocol/va-location-reference-catalog --base main --head work/no-key-local-source-import-local-run --title "data: import local public VA facility source candidate" --body "Local public-source import. No VA API key used. Human review required."
```

## PDF note

PDFs should be treated as evidence unless converted/exported to HTML/CSV first. The importer intentionally parses structured HTML, CSV, and JSON because those are safer for repeatable GitOps catalog generation.

## Boundary

Do not commit:

- API keys.
- Credentials.
- Tokens.
- PII/PHI.
- ServiceNow exports.
- CMDB exports.
- Internal VA directories.
- Internal network/security/configuration data.

## Expected outputs

```text
data/raw/public_sources/<timestamp>/...
data/normalized/va_locations.json
data/normalized/va_locations.csv
data/normalized/va_locations.jsonl
data/normalized/index_by_facility_id.json
data/normalized/index_by_station_code.json
data/normalized/unmatched_station_codes.json
data/approved/release_manifest.json
data/approved/checksums.sha256
evidence/latest_import_public_sources.json
evidence/latest_validation.json
evidence/latest_release_manifest.json
```

## Review rule

Generated records remain `review_pending` until owner review. Do not treat them as production-approved facility truth until merged and reviewed.
