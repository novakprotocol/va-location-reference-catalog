# Next Run

## Start Here

1. Read `.repo-standard.yml`, `AGENTS.md`, `COMMANDS.md`, `README.md`, `docs/SOURCE_POLICY.md`, and `docs/status/N_SDT_REPOOPS_ALIGNMENT.md`.
2. Confirm whether the repo visibility is still public. If it is public, assume every committed byte must be public-safe.
3. Run the safe local checks in `COMMANDS.md` before changing data.
4. If the task is a catalog refresh, create a dedicated branch and follow `docs/RUN_NOW_NO_KEY_PUBLIC_IMPORT.md`.
5. Record any generated evidence and review status in the pull request.

## Do Not Do By Default

- Do not run download/import commands for a docs-only alignment task.
- Do not commit secrets, private VA data, internal exports, or sensitive screenshots.
- Do not claim the catalog is production-approved unless owner review says so.
