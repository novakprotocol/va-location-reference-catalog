# Commands

Run from the repository root.

## Safe Local Checks

```powershell
python .\scripts\validate_catalog.py
python .\scripts\build_release_candidate.py
git diff --check
```

## Owner-Approved Data Refresh Only

These commands can download public data and update generated files. Run them only in a dedicated branch after confirming the source policy.

```powershell
python .\scripts\import_public_sources.py --download
python .\scripts\validate_catalog.py
python .\scripts\build_release_candidate.py
```

## Review Before Commit

```powershell
git status --short
git diff -- data docs config schemas scripts evidence
```
