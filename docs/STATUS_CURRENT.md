# Current Status — VA IaT Location Reference Catalog

```text
PROJECT=VA IaT Location Reference Catalog
REPO=novakprotocol/va-location-reference-catalog
VISIBILITY=private
DEFAULT_BRANCH=main
CURRENT_VERIFIED_BASE=a85b050ccab6852a0fcee1717e4a52d3989f8dd6
STATUS=private pilot scaffold pushed
DATA_BOUNDARY=public-source-only
PRODUCTION_WRITEBACK=denied
VA_INTERNAL_DATA=denied
PII_PHI=denied
```

## What is real now

- Private GitHub repository exists.
- `main` contains the initial scaffold.
- The repo has docs, contracts, schema, policy markers, validation scripts, and placeholder data/evidence directories.
- No real VA facility records have been fetched or approved yet.
- No VA API key is stored in Git.
- No internal VA data should be placed in this repo.

## Current safe next step

Run the local population workflow from a controlled local checkout using a VA API key stored only in the shell environment, then open a pull request with generated public-source outputs and evidence receipts.

## Approval posture

This pilot is safe for private proof-of-concept use only when it remains public-source-only. Production adoption needs VA-approved hosting, secrets management, records/privacy/security review, and owner approval.
