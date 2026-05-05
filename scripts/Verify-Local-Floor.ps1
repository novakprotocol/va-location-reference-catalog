<#
.SYNOPSIS
  Verify the local VA IaT Location Reference Catalog repo floor.
#>

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

$StartTime = Get-Date
$StepNo = 0

function Step {
    param([string]$Message)
    $script:StepNo++
    $Elapsed = [int]((Get-Date) - $script:StartTime).TotalSeconds
    Write-Host ''
    Write-Host ('===== {0:D2} :: {1} | elapsed={2}s =====' -f $script:StepNo, $Message, $Elapsed)
}

$RepoPath = Join-Path $env:USERPROFILE 'Desktop\VA-IaT-LocationCatalog-Pilot\va-location-reference-catalog'

Step 'ENTER REPO'
Set-Location -LiteralPath $RepoPath
Write-Host "REPO_PATH=$RepoPath"

Step 'VERIFY GIT STATE'
git status --short
git branch --show-current
git rev-parse --short HEAD
git remote -v

Step 'VERIFY REQUIRED FILES'
$Required = @(
    'README.md',
    '.github/workflows/validate.yml',
    '.github/pull_request_template.md',
    '.github/CODEOWNERS',
    '.gitattributes',
    'docs/STATUS_CURRENT.md',
    'docs/RUN_NOW_LOCAL_POPULATION.md',
    'contracts/consumer_registry.json',
    'contracts/producer_contract.json',
    'schemas/va_location_record.schema.json',
    'policies/deny_markers.json',
    'scripts/fetch_va_facilities.py',
    'scripts/normalize_va_facilities.py',
    'scripts/validate_catalog.py',
    'scripts/build_release_candidate.py',
    'scripts/Run-Day0-Populate-And-OpenPR.ps1'
)

$Missing = @()
foreach ($Path in $Required) {
    if (-not (Test-Path -LiteralPath $Path)) { $Missing += $Path }
}

if ($Missing.Count -gt 0) {
    Write-Host 'MISSING_FILES=FAIL'
    $Missing | ForEach-Object { Write-Host "MISSING=$_" }
    throw 'Required files missing.'
}

Write-Host 'REQUIRED_FILES=PASS'

Step 'RUN STATIC VALIDATION'
python scripts/validate_catalog.py

Step 'DONE'
Write-Host ''
Write-Host 'RESULT=PASS'
Write-Host "HEAD=$(git rev-parse --short HEAD)"
Write-Host "BRANCH=$(git branch --show-current)"
