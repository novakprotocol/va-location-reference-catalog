# Public / Internal Boundary

Current public catalog posture:

- This repository may publish a public, no-key, static GitHub Pages catalog.
- Public pages must contain only public-source reference data.
- Public pages must not contain internal operational status, restricted fields, ticket data, staffing data, vulnerability data, outage data, user data, or internal system-of-record data.
- The public Veterans Crisis Line banner is public-site safety UX and is intentionally locked to the top of public pages.
- Internal-only deployments may remove or replace that public emergency-resource banner if the internal portal has its own approved emergency-resource surface.

## Public lane

The public lane is for:

- Facility reference lookup.
- Public address, website, type, public coordinates, source and review-state labels.
- Candidate-only public contact/hour evidence.
- Read-only review surfaces.
- Export of public/reference rows.

The public lane is not the source of authority for restricted or live operational data.

## Internal overlay lane

The internal overlay should be separate from the public static catalog.

The internal overlay may add:

- Internal routing.
- Ownership and resolver groups.
- Internal escalation notes.
- ServiceNow or ticket references.
- Live operational status.
- CMDB/IPAM/DNS reference validation.
- Work-hour policy context.
- Approval workflow state.
- Sensitive operational metadata.

The internal overlay must not be pushed to public GitHub Pages.

## GitOps rule

Public and internal truth should not be mixed in one rendered artifact.

Recommended model:

```text
public catalog repo / public Pages = public reference truth
internal overlay repo or private branch = internal operational enrichment
joined internal portal/dashboard = public base + private overlay
```

## Safe join key

Use stable public facility identifiers as join keys where available:

```text
facility_id
station_code
source_system
source_url
```

Do not use patient/user/person identifiers in the public catalog.