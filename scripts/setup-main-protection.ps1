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
gh auth status | Out-Host

Write-Host "Checking latest '$RequiredCheck' workflow on $Branch..."
$latestRun = gh run list --repo $Repo --workflow test.yml --branch $Branch --limit 1 --json status,conclusion,databaseId,headSha,url | ConvertFrom-Json

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
    gh api "repos/$Repo/branches/$Branch/protection" | Out-Host
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
    $payload | ConvertTo-Json -Depth 10 | Set-Content -Path $tempFile -Encoding utf8

    Write-Host ""
    Write-Host "Applying protection to ${Repo}:$Branch ..."
    gh api --method PUT -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" "repos/$Repo/branches/$Branch/protection" --input $tempFile | Out-Host
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
