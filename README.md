# VA Location Reference Catalog

Private pilot repository for the VA IaT Location Reference Catalog.

## Purpose

Generate a public-source, Git-governed, schema-validated, evidence-backed location reference catalog.

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

## Quick start

```bash
export VA_API_KEY='your-key-here'

python3 scripts/fetch_va_facilities.py
python3 scripts/normalize_va_facilities.py
python3 scripts/validate_catalog.py
python3 scripts/build_release_candidate.py
```
