param(
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

$Repo = "1kz-ma1/HINANEX"
$Branch = "main"
$RequiredCheck = "test"

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Require-Command "gh"

Write-Host "Checking GitHub authentication..."
& gh auth status
if ($LASTEXITCODE -ne 0) {
    throw "GitHub authentication check failed. Run 'gh auth login' and try again."
}

Write-Host "Checking latest '$RequiredCheck' workflow on $Branch..."
$latestRunJson = & gh run list --repo $Repo --workflow test.yml --branch $Branch --limit 1 --json status,conclusion,databaseId,headSha,url
if ($LASTEXITCODE -ne 0) {
    throw "Failed to query the latest '$RequiredCheck' workflow run."
}

$latestRun = $latestRunJson | ConvertFrom-Json

if (-not $latestRun) {
    throw "No test workflow run was found on main. Run CI successfully before enabling protection."
}

$run = @($latestRun)[0]
if ($run.status -ne "completed" -or $run.conclusion -ne "success") {
    throw "Latest test workflow is not green. status=$($run.status), conclusion=$($run.conclusion)"
}

Write-Host "Latest test workflow: success"
Write-Host "Run: $($run.url)"

if ($VerifyOnly) {
    Write-Host ""
    Write-Host "Current main protection:"

    $verifyResponse = & gh api "repos/$Repo/branches/$Branch/protection"
    $verifyExitCode = $LASTEXITCODE
    $verifyResponse | Out-Host

    if ($verifyExitCode -ne 0) {
        throw "Failed to read branch protection. gh exit code: $verifyExitCode"
    }

    exit 0
}

$payload = @{
    required_status_checks = @{
        strict = $true
        contexts = @($RequiredCheck)
    }
    enforce_admins = $true
    required_pull_request_reviews = @{
        dismiss_stale_reviews = $false
        require_code_owner_reviews = $false
        required_approving_review_count = 0
        require_last_push_approval = $false
    }
    restrictions = $null
    required_linear_history = $false
    allow_force_pushes = $false
    allow_deletions = $false
    block_creations = $false
    required_conversation_resolution = $false
    lock_branch = $false
    allow_fork_syncing = $false
}

$tempFile = Join-Path $env:TEMP "hinanex-main-protection.json"

try {
    $json = $payload | ConvertTo-Json -Depth 10 -Compress

    # Write UTF-8 without BOM so GitHub can parse the request body consistently
    # in both Windows PowerShell 5.1 and PowerShell 7+.
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tempFile, $json, $utf8NoBom)

    Write-Host ""
    Write-Host "Applying protection to ${Repo}:$Branch ..."

    $applyResponse = & gh api --method PUT -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" "repos/$Repo/branches/$Branch/protection" --input $tempFile
    $applyExitCode = $LASTEXITCODE
    $applyResponse | Out-Host

    if ($applyExitCode -ne 0) {
        throw "Failed to apply branch protection. gh exit code: $applyExitCode"
    }
}
finally {
    if (Test-Path $tempFile) {
        Remove-Item $tempFile -Force
    }
}

Write-Host ""
Write-Host "Protection applied."
Write-Host "- Pull request required"
Write-Host "- Required status check: $RequiredCheck"
Write-Host "- Branch must be up to date before merge"
Write-Host "- Force push disabled"
Write-Host "- Branch deletion disabled"
Write-Host "- Rules apply to repository admins / Merge Captain"
Write-Host ""
Write-Host "Verify with:"
Write-Host "  .\\scripts\\run-main-protection.ps1 -VerifyOnly"
