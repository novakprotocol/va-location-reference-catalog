# 09 — Security, Privacy, and Compliance Guardrails

## Primary guardrail

The personal/private pilot is public-data-only.

## Why this matters

A private repository is not automatically safe for VA internal data.

A private repository can still be misconfigured, shared, forked, cloned, leaked, or later made public.

## Prohibited in private pilot

```text
PII
PHI
Veteran information
patient information
claimant information
employee personal contact data
internal directories
internal extensions
ServiceNow exports
CMDB exports
emails
tickets
screenshots with sensitive info
configuration files
secrets
tokens
API keys
cookies
headers
bearer tokens
private keys
```

## Controls

### Repository controls

- Private repository.
- Branch protection.
- Pull requests.
- Required status checks.
- Secret scanning where available.
- CODEOWNERS.
- No public Pages.
- No production tokens.
- No write integrations.

### Developer controls

- Store API key only in environment.
- Never commit `.env`.
- Use `git status`.
- Use `git diff --cached`.
- Avoid `git add .` for sensitive workspaces.
- Stage files intentionally.
- Keep pilot folder separate from VA internal exports.

### CI controls

- JSON parse.
- Schema check.
- Required fields.
- Duplicate IDs.
- Secret patterns.
- Denied data markers.
- Evidence receipt.
- Drift report.

### Production controls

- VA-approved hosting.
- Enterprise identity.
- Approved secrets manager.
- Audit logging.
- Security/privacy review.
- Data steward approval.
- Records/retention review.
- Incident path for accidental sensitive data.
