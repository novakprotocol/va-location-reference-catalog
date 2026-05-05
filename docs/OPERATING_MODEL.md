# 05 — Data Product Model

## Product identity

```text
Product: Public VA Facility Location Catalog
Type: governed reference-data product
Primary output: approved location identity catalog
Primary use: read-only reference and reconciliation
```

## Data product principles

1. Source-traced.
2. Schema-versioned.
3. Deterministic generation.
4. Evidence-backed.
5. Reviewed before approval.
6. Released immutably.
7. Consumed through contracts.
8. Deny-by-default for production consumers.
9. No sensitive data in private pilot.
10. No write-back without separate approval.

## Channels

| Channel | Purpose | Consumer access |
|---|---|---|
| `raw` | Original source snapshot | No direct consumption |
| `intermediate` | Parsed source material | No direct consumption |
| `normalized` | Generated schema-conforming data | Test only |
| `approved` | Reviewed catalog | Approved consumers |
| `released` | Immutable release artifact | Production consumers after approval |
| `rejected` | Known-bad / denied records | Data quality review only |

## Versioning

Recommended catalog version:

```text
YYYY.MM.DD.N
```

Example:

```text
2026.05.05.1
```

Recommended schema version:

```text
1.0.0
```

A release artifact should include:

```text
catalog_version
schema_version
git_commit
git_tag
source_snapshot_utc
record_count
checksum_manifest
validation_receipt
```

## Lineage ID

Every record should have a `lineage_id`.

Example:

```text
source_system:VA Facilities API|facility_id:vha_688|snapshot:20260505T120000Z
```

The lineage ID should allow an operator to trace:

```text
approved record → normalized record → raw source file → fetch receipt → source URL
```


# 12 — Release and Evidence Model

## Release manifest

Every release should produce:

```json
{
  "catalog_name": "Public VA Facility Location Catalog",
  "catalog_version": "2026.05.05.1",
  "schema_version": "1.0.0",
  "git_commit": "abc123",
  "git_tag": "va-location-catalog-2026.05.05.1",
  "source_snapshot_utc": "2026-05-05T12:00:00Z",
  "record_count": 1234,
  "created_utc": "2026-05-05T12:30:00Z",
  "validation_result": "PASS",
  "policy_result": "PASS",
  "approved_by": "pilot-owner",
  "consumer_contract_version": "1.0.0"
}
```

## Checksum manifest

Generate SHA256 checksums for:

```text
va_locations.json
va_locations.csv
va_locations.jsonl
index_by_facility_id.json
index_by_station_code.json
consumer_contract.json
release_manifest.json
```

## Evidence bundle

A release evidence bundle should contain:

```text
source_manifest.json
latest_fetch.json
latest_normalization.json
latest_validation.json
latest_policy.json
latest_drift.json
release_manifest.json
checksums.sha256
change_summary.md
```

## Release channels

```text
pilot
candidate
approved
deprecated
revoked
```

## Revocation

A release should be revoked if:

- Sensitive data is discovered.
- Source corruption is discovered.
- Schema error affects consumers.
- Wrong station mappings are approved.
- Release checksum mismatch occurs.
