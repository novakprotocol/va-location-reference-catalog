# 08 — Producer and Consumer Contracts

## Producer contract

Each source must declare:

```json
{
  "producer_name": "VA Facilities API",
  "source_type": "public_api",
  "source_url": "https://developer.va.gov/explore/api/va-facilities/docs",
  "auth_method": "api_key",
  "allowed_fields": [
    "facility_id",
    "name",
    "facility_type",
    "address",
    "phone",
    "hours",
    "services",
    "website",
    "latitude",
    "longitude"
  ],
  "denied_fields": [
    "employee_contact_data",
    "internal_extensions",
    "credentials",
    "pii",
    "phi"
  ],
  "freshness_target_days": 30,
  "failure_behavior": "do_not_release_new_catalog"
}
```

## Consumer contract

Each consumer must declare:

```json
{
  "consumer_name": "example-grafana-site-labels",
  "owner": "observability-team",
  "consumer_type": "display_only",
  "allowed_outputs": [
    "data/approved/va_locations.json"
  ],
  "allowed_fields": [
    "facility_id",
    "station_code",
    "name",
    "facility_type",
    "visn",
    "state",
    "source_snapshot_utc",
    "catalog_version"
  ],
  "write_back_allowed": false,
  "approval_reference": "pilot-only",
  "last_reviewed": "YYYY-MM-DD"
}
```

## Consumer types

| Type | Allowed behavior | Disallowed behavior |
|---|---|---|
| display_only | show labels and metadata | write to source systems |
| reconciliation | compare and report | overwrite records |
| validation | fail/pass reference checks | mutate production |
| automation_lookup | enrich generated configs | deploy changes without separate approval |
| writeback | only by separate approval | default denied |

## Deny-by-default

If a consumer is not registered, it is not production-approved.

## Write-back rule

Write-back is a separate product lane.

This repo should not silently become an automation authority.
