# 11 — GitOps and IaT Alignment

## GitOps alignment

This catalog aligns to GitOps when:

- The approved catalog is declarative.
- Desired reference state is stored in Git.
- Releases are immutable.
- Consumers pull approved artifacts.
- Consumers reconcile their local view against the catalog.
- Drift becomes visible.

## IaT alignment

IaT needs reliable identity dimensions.

This catalog provides the site/location dimension.

Recommended IaT relationship:

```text
asset_record
  has location_ref

location_ref
  points to VA IaT Location Reference Catalog record

catalog record
  points to source evidence and release manifest
```

## Labels

Recommended labels:

```yaml
iat.va.gov/facility-id: "vha_688"
iat.va.gov/station-code: "688"
iat.va.gov/station-code-confidence: "derived"
iat.va.gov/facility-type: "health"
iat.va.gov/visn: "5"
iat.va.gov/catalog-version: "2026.05.05.1"
iat.va.gov/source-system: "va_facilities_api"
```

## Fail-closed rules

Consumers should fail closed when:

- Facility ID is unknown.
- Station code is conflicting.
- Catalog version is expired.
- Approval state is not approved.
- Consumer is not registered.
- Field is not approved for that consumer.
- Output checksum does not match release manifest.

## Over-the-horizon addition

Add a reconciliation agent later:

```text
approved catalog → compare CMDB/SNOW/Grafana labels → produce drift report → human review
```

Not:

```text
approved catalog → overwrite CMDB/SNOW automatically
```
