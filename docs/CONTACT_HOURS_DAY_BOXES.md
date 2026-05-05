# Contact/Hours Day-Box Review Preview

Status: candidate-review helper only

`contact-hours-candidates.html` now renders candidate hours with a visual day-of-week preview.

## Purpose

The day boxes make candidate hours easier to review:

- `24/7` candidate language displays a clear `24/7` badge and all days open.
- Daily/open-daily language marks all days open.
- Monday-through-Friday language marks weekdays open and weekends closed.
- Unrecognized patterns remain review-needed/unknown.

## Guardrails

- This is not an approved hours mutation.
- This does not promote hours into approved catalog records.
- It is a review helper for public-source candidate text.
- Human review is still required before any official hours field is created or changed.

## Day box meaning

```text
Open day   = candidate text appears to cover that day
Closed day = candidate text appears not to cover that day
Unknown    = script could not infer that day from candidate text
24/7       = candidate text includes 24/7 or 24-hour language
```