# Pull Request

## Purpose

Describe the source snapshot, normalization change, schema change, or documentation change.

## Change type

- [ ] source snapshot
- [ ] schema change
- [ ] code change
- [ ] docs only
- [ ] consumer contract
- [ ] release candidate

## Data boundary

- [ ] Public source data only.
- [ ] No VA internal exports.
- [ ] No PII/PHI.
- [ ] No employee contact data.
- [ ] No tickets.
- [ ] No ServiceNow exports.
- [ ] No CMDB exports.
- [ ] No credentials or tokens.
- [ ] No production write-back.

## Validation

```text
VALIDATION_RESULT:
RECORD_COUNT:
DUPLICATE_COUNT:
SECRET_FINDING_COUNT:
DENIED_MARKER_FINDING_COUNT:
```

## Source

```text
Source:
Snapshot UTC:
Source manifest:
```

## Consumer impact

- [ ] no consumer impact
- [ ] display-only
- [ ] reconciliation
- [ ] validation
- [ ] automation lookup
- [ ] write-back requested separately

## Reviewer checklist

- [ ] Source is allowed.
- [ ] Diff is understandable.
- [ ] Evidence receipts exist.
- [ ] Checksums generated if release candidate.
- [ ] No sensitive data.
- [ ] Consumer contract unchanged or reviewed.
