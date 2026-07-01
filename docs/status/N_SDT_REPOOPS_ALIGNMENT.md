# N-SDT + RepoOps Alignment Record

Status: classification-first alignment record.

## Actual Repo Purpose

`va-location-reference-catalog` is a public-source, Git-governed, schema-validated VA facility location reference catalog. It should remain a narrow reference-data product with evidence and review receipts.

## Classification

| Field | Value |
|---|---|
| Repo classification | data/reference catalog |
| N-SDT treatment | public-data truth boundary + operator continuity |
| RepoOps treatment | data-spine profile |
| Current risk | existing docs mention a private pilot while GitHub metadata was observed as public on 2026-07-01 |
| Safety rule | treat all content as public-safe and public-source-only |

## Better Or Stronger Signal Found

This repo already has useful data governance signals: source policy, operating model, schema, validation script, release candidate builder, evidence files, and a GitHub validation workflow. The missing piece was the lightweight handoff spine for AI and human operators.

## Required Local Follow-Up

```powershell
python .\scripts\validate_catalog.py
python .\scripts\build_release_candidate.py
git diff --check
```

Do not run public-source imports in an alignment-only pass. Imports belong in a separate data refresh branch with owner review.

## Local Checks Run On 2026-07-01

- PASS `python .\scripts\validate_catalog.py` with 2137 records
- PASS `git diff --check`
- SKIPPED `python .\scripts\build_release_candidate.py` in the local working tree because it rewrites timestamped release/evidence files; the configured GitHub PR workflow runs this command without committing generated noise.

## Guardrails

- Do not commit PII, PHI, internal VA exports, credentials, tokens, or private operational data.
- Do not treat private repository wording as a safety control.
- Do not claim production approval without owner review.
- Do not let RepoOps change catalog truth; RepoOps only describes how the repo is operated.
