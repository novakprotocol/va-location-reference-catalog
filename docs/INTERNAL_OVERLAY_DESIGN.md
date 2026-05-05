# Internal Overlay Design

## Purpose

The public catalog is useful for public reference lookup. The internal overlay makes it useful for VA operations without leaking restricted or operational data to the public site.

## Recommended deployment shape

```text
Public GitHub Pages
  public/no-key/reference-only catalog

Private internal overlay
  restricted VA-only operational fields

Internal portal/dashboard
  joins public reference rows to private overlay rows at runtime
```

## Internal-only fields

Examples of fields that belong in the internal overlay:

- owning team
- resolver group
- operating unit
- facility owner
- internal contact
- escalation path
- ServiceNow assignment group
- CMDB CI
- authoritative source links
- live open/closed status
- outage or degradation state
- after-hours coverage
- SLA/SLO notes
- internal notes
- restricted comments

## Approval model

Public updates and internal updates should have separate approval gates.

Public updates should verify:

- no secrets
- no internal-only fields
- public source traceability
- schema validity
- static page safety

Internal updates should verify:

- need-to-know scope
- data classification
- owner approval
- audit trail
- operational correctness