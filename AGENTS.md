# AI And Human Operating Rules

## Purpose

This repository is a public-source VA facility location reference catalog. Treat it as a governed data product, not as an internal VA system.

## Required First Reads

Before editing, read:

- `.repo-standard.yml`
- `README.md`
- `docs/SOURCE_POLICY.md`
- `docs/RUN_NOW_NO_KEY_PUBLIC_IMPORT.md`
- `docs/STATUS_CURRENT.md`
- `docs/status/N_SDT_REPOOPS_ALIGNMENT.md`
- `COMMANDS.md`
- `NEXT_RUN.md`

## Hard Boundaries

- Use public sources only.
- Do not commit PII, PHI, Veteran information, claimant information, employee personal contact data, internal directories, tickets, CMDB exports, ServiceNow exports, screenshots with sensitive data, credentials, tokens, cookies, private keys, headers, bearer tokens, or API keys.
- Do not run download/import commands unless the owner has approved a data refresh lane.
- Do not treat generated records as production-approved facility truth until reviewed and merged.
- Do not use `git add .` in data refresh work. Stage intentional paths only.
- Do not claim hosted checks passed unless the GitHub checks actually ran and passed.

## N-SDT And RepoOps Boundary

N-SDT records product truth, data boundary, and operator continuity. RepoOps records repo operating profile, checks, handoff rules, and exceptions. Keep them separate and let this repo stay a small data-spine profile.
