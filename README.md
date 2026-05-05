# VA Location Reference Catalog

Private pilot repository for the Public VA Facility Location Catalog.

## Purpose

Generate a public-source, Git-governed, schema-validated, evidence-backed location reference catalog.

## Current Day0 path

Use the no-key public-source import lane first.

```powershell
cd "$env:USERPROFILE\Desktop\Public VA Facility Catalog-LocationCatalog-Pilot\va-location-reference-catalog"

git checkout main
git pull --ff-only origin main

git checkout -B work/no-key-public-source-import-local-run
python .\scripts\import_public_sources.py --download
python .\scripts\validate_catalog.py
python .\scripts\build_release_candidate.py
```

Then review, commit, push, and open a PR:

```powershell
git status --short
git add data\raw data\normalized data\approved evidence
git commit -m "data: import no-key public VA facility catalog candidate"
git push -u origin work/no-key-public-source-import-local-run
gh pr create --repo novakprotocol/va-location-reference-catalog --base main --head work/no-key-public-source-import-local-run --title "data: import no-key public VA facility catalog candidate" --body "No-key public-source import. No VA API key used. Human review required."
```

See:

```text
docs/RUN_NOW_NO_KEY_PUBLIC_IMPORT.md
config/public_sources.json
```

## Optional future API path

The VA API-key path is optional/future only. Do not block the private pilot on getting a key.

## Boundary

Public data only during private pilot.

Do not commit:

- PII/PHI.
- Employee contact data.
- Internal VA exports.
- Tickets.
- CMDB exports.
- ServiceNow exports.
- Internal directories.
- Credentials.
- Tokens.
- API keys.
- Internal network/security/configuration data.

## Expected outputs

```text
data/raw/public_sources/<timestamp>/...
data/normalized/va_locations.json
data/normalized/va_locations.csv
data/normalized/va_locations.jsonl
data/approved/release_manifest.json
data/approved/checksums.sha256
evidence/latest_import_public_sources.json
evidence/latest_validation.json
evidence/latest_release_manifest.json
```
