# Public contact and hours candidates

## Status

This repository stores public-source contact and hours candidates as review evidence.

These fields are **not** approved as authoritative operational contact fields yet.

## Current policy

- Public pages may be fetched only from public HTTP/HTTPS URLs already present in the catalog.
- Extracted phone numbers are stored as candidates.
- Extracted hours strings are stored as candidates.
- National/shared VA numbers are tagged and must not be blindly promoted to facility phone.
- The approved catalog remains separate from candidate enrichment until a review rule is accepted.

## Generated artifacts

- scripts/enrich_public_contact_hours_candidates.py
- data/enriched/va_locations.contact_hours_candidates.json
- data/enriched/va_locations.contact_hours_candidates.jsonl
- data/enriched/va_locations.contact_hours_candidates.csv
- evidence/latest_public_contact_hours_candidates.json
- data/raw/public_contact_hours_candidates/

## GitOps meaning

This is a candidate evidence layer. Reviewers can inspect source URL, raw SHA-256, parser version, extracted UTC time, confidence, and review status before approving any field promotion.