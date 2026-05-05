<#
.SYNOPSIS
  Populate the VA IaT Location Reference Catalog locally and open a GitHub PR.

.DESCRIPTION
  - Uses VA_API_KEY from the current PowerShell environment only.
  - Does not write VA_API_KEY to disk.
  - Fetches public VA Facilities API data using existing Python scripts.
  - Normalizes, validates, builds release candidate artifacts, commits generated data/evidence, and opens a PR.
  - Stops immediately on failed external commands so failed data is not committed.

.REQUIREMENTS
  - git
  - gh
  - python
  - authenticated gh session with repo and workflow scope

.SAFETY
  Public-source-only. No internal VA exports. No PII/PHI. No ServiceNow/CMDB exports.
#>

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

$StartTime = Get-Date
$StepNo = 0
$ApiKeyCleared = $false

function Step {
    param([string]$Message)
    $script:StepNo++
    $Elapsed = [int]((Get-Date) - $script:StartTime).TotalSeconds
    Write-Host ''
    Write-Host ('===== {0:D2} :: {1} | elapsed={2}s =====' -f $script:StepNo, $Message, $Elapsed)
}

function Fail {
    param([string]$Message)
    throw $Message
}

function Require-Command {
    param([string]$Name)
    $Cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $Cmd) { Fail "Required command not found: $Name" }
    return $Cmd.Source
}

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory=$true)][string]$Command,
        [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments
    )

    & $Command @Arguments
    $ExitCode = $LASTEXITCODE
    if ($ExitCode -ne 0) {
        Fail "Command failed with exit code ${ExitCode}: $Command $($Arguments -join ' ')"
    }
}

function Clear-ApiKey {
    Remove-Item Env:\VA_API_KEY -ErrorAction SilentlyContinue
    $script:ApiKeyCleared = $true
    Write-Host 'VA_API_KEY_REMOVED_FROM_ENV=PASS'
}

function Assert-FileExists {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        Fail "Expected output file missing: $Path"
    }
}

$RepoPath = Join-Path $env:USERPROFILE 'Desktop\VA-IaT-LocationCatalog-Pilot\va-location-reference-catalog'
$FullRepo = 'novakprotocol/va-location-reference-catalog'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$WorkBranch = "work/populate-public-va-facilities-$Stamp"

try {
    Step 'VERIFY TOOLS AND REPO'
    Require-Command git | Out-Host
    Require-Command gh | Out-Host
    Require-Command python | Out-Host

    if (-not (Test-Path -LiteralPath $RepoPath)) {
        Fail "Repo path not found: $RepoPath"
    }

    Set-Location -LiteralPath $RepoPath
    Write-Host "REPO_PATH=$RepoPath"
    Write-Host "GITHUB_REPO=$FullRepo"

    Invoke-NativeChecked gh auth status

    if (-not $env:VA_API_KEY) {
        Fail 'VA_API_KEY is not set in this PowerShell session. Set it in memory only: $env:VA_API_KEY = ''...'''
    }

    if ($env:VA_API_KEY -match '^(PASTE|PASTE_|PASTE-|CHANGEME|CHANGE_ME|TODO|REPLACE|REPLACE_ME|YOUR_|YOUR-)' -or $env:VA_API_KEY -eq 'PASTE_REAL_KEY_HERE' -or $env:VA_API_KEY -eq 'PASTE_KEY_HERE') {
        Fail 'VA_API_KEY still looks like a placeholder. Set the real key in memory only, then rerun.'
    }

    Step 'SYNC MAIN AND CREATE WORK BRANCH'
    Invoke-NativeChecked git checkout main
    Invoke-NativeChecked git pull --ff-only origin main
    Invoke-NativeChecked git checkout -B $WorkBranch

    Step 'RUN PUBLIC SOURCE FETCH'
    Invoke-NativeChecked python scripts/fetch_va_facilities.py
    Assert-FileExists 'data/raw/va_facilities_api/latest_snapshot.txt'

    Step 'NORMALIZE PUBLIC SOURCE DATA'
    Invoke-NativeChecked python scripts/normalize_va_facilities.py
    Assert-FileExists 'data/normalized/va_locations.json'
    Assert-FileExists 'data/normalized/va_locations.csv'
    Assert-FileExists 'data/normalized/va_locations.jsonl'

    Step 'VALIDATE CATALOG'
    Invoke-NativeChecked python scripts/validate_catalog.py
    Assert-FileExists 'evidence/latest_validation.json'

    Step 'BUILD RELEASE CANDIDATE'
    Invoke-NativeChecked python scripts/build_release_candidate.py
    Assert-FileExists 'data/approved/release_candidate_manifest.json'

    Step 'REMOVE API KEY FROM PROCESS ENVIRONMENT'
    Clear-ApiKey

    Step 'SHOW GENERATED FILES'
    Invoke-NativeChecked git status --short

    Step 'COMMIT GENERATED DATA AND EVIDENCE'
    Invoke-NativeChecked git add data evidence

    git diff --cached --quiet
    $HasStagedChanges = ($LASTEXITCODE -ne 0)

    if (-not $HasStagedChanges) {
        Fail 'No generated data/evidence changes were staged. Nothing to PR.'
    }

    Invoke-NativeChecked git commit -m 'data: add public VA facilities catalog candidate'

    Step 'PUSH BRANCH'
    Invoke-NativeChecked git push -u origin $WorkBranch

    Step 'OPEN PR'
    $Body = @"
## Purpose

Add a generated public-source VA Facilities catalog candidate.

## Boundary

- Public source data only.
- No VA internal exports.
- No PII/PHI.
- No employee contact data.
- No tickets.
- No ServiceNow exports.
- No CMDB exports.
- No credentials or tokens.
- No production write-back.

## Validation

Generated by local script after all gates passed:

```text
python scripts/fetch_va_facilities.py
python scripts/normalize_va_facilities.py
python scripts/validate_catalog.py
python scripts/build_release_candidate.py
```

Owner review required before treating any output as approved.
"@

    Invoke-NativeChecked gh pr create --title 'data: add public VA facilities catalog candidate' --body $Body --base main --head $WorkBranch

    Step 'DONE'
    Write-Host ''
    Write-Host 'RESULT=PASS'
    Write-Host "GITHUB_REPO=$FullRepo"
    Write-Host "BRANCH=$WorkBranch"
    Write-Host "HEAD=$(git rev-parse --short HEAD)"
    Write-Host "LOCAL_REPO_PATH=$RepoPath"
    Write-Host ''
}
finally {
    if (-not $ApiKeyCleared) {
        Step 'CLEAN API KEY FROM PROCESS ENVIRONMENT'
        Clear-ApiKey
    }
}

