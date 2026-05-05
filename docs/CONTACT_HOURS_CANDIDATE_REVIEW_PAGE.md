# Contact/Hours Candidate Review Page

## Purpose

`contact-hours-candidates.html` provides a static GitHub Pages review surface for public-source contact and hours candidate evidence.

## Guardrails

- This page is candidate review only.
- It does not promote phone or hours values into approved facility records.
- National/shared numbers are tagged and should not be treated as facility primary contact values without review.
- Low-confidence and possible non-primary values require human review before promotion.

## Inputs

- `data/enriched/va_locations.contact_hours_candidates.json`
- `data/enriched/va_locations.contact_hours_candidates.jsonl`
- `data/enriched/va_locations.contact_hours_candidates.csv`
- `evidence/latest_public_contact_hours_candidates.json`

## Review flow

1. Open `contact-hours-candidates.html`.
2. Search by facility name, facility ID, phone, hours text, source URL, or context.
3. Filter by phone role and confidence.
4. Review public source URL and captured context.
5. Promote only later through a separate reviewed GitOps change.