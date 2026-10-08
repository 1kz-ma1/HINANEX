# HINANEX local GSI 10/22 demo acceptance runner (PowerShell 5.1+).
# Requires a PREVIOUSLY archived official GeoJSON. Never fetches/replaces that raw file.
# Keep this runner in an isolated integration-preview worktree.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ArchivePath,
    [ValidateSet('13123', '15100', '23100')]
    [string]$RegionCode = '13123',
    [string]$PythonExe = 'C:\HINANEX\pipeline\.venv\Scripts\python.exe',
    [string]$SourceUrl = 'https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson',
    [string]$ExpectedSha256 = '2748FEA7E1145FD2A3BDFAD05B3FEA4B86127FAFD017F253FE327472F89A3A41',
    [switch]$PublishPreview
)

$ErrorActionPreference = 'Stop'
# Validate exact z10 official source URL before touching data or publishing.
$pattern = '^https://cyberjapandata\.gsi\.go\.jp/xyz/skhb01/10/(\d+)/(\d+)\.geojson$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = (Resolve-Path -LiteralPath $PythonExe).Path
$raw = (Resolve-Path -LiteralPath $ArchivePath).Path
$found = (Get-FileHash -LiteralPath $raw -Algorithm SHA256).Hash
if ($ExpectedSha256 -and ($found -ine $ExpectedSha256)) {
    throw "Archived raw SHA256 mismatch. Original left unchanged: expected $ExpectedSha256 / actual $found"
}
if (-not (Test-Path -LiteralPath (Join-Path $repo 'validation\validation\verify_gsi_catalog_acceptance.py'))) {
    throw "This worktree lacks the current integrated local acceptance checker."
}

# Unique run folder; do not overwrite past audit JSON or edited source files.
$runId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$runDir = Join-Path $repo ("pipeline\data\verified\gsi-acceptance-runs\" + $runId)
New-Item -ItemType Directory -Force -Path $runDir -ErrorAction Stop | Out-Null
$rows = Join-Path $runDir 'gsi_records.json'
$cAudit = Join-Path $runDir 'c_raw_acceptance.json'
$provenance = Join-Path $runDir 'c_https_provenance.json'
$catalog = Join-Path $runDir 'gsi_flood_site_catalog.json'
Write-Host "HINANEX validation run: $runDir"
Write-Host "Archived raw: $raw / SHA256: $found"

function Assert-Success([string]$stage) {
    if ($LASTEXITCODE -ne 0) {
        throw "$stage failed (exit $LASTEXITCODE). Existing archives and preview output were NOT changed."
    }
}

Push-Location $repo
try {
    & $python '.\pipeline\prepare_gsi_flood_tile.py' --region $RegionCode --raw $raw --source-url $SourceUrl --out $rows
    Assert-Success 'D source normalization'

    & $python '.\validation\validation\verify_gsi_flood_source.py' --region $RegionCode --raw $raw --source-url $SourceUrl --records $rows --acceptance-out $cAudit
    Assert-Success 'C independent raw-row audit'

    # This step contacts GSI. It must not be bypassed after network errors or changed bytes.
    & $python '.\validation\validation\verify_gsi_flood_provenance.py' --raw $raw --source-url $SourceUrl --c-acceptance $cAudit --report-out $provenance
    Assert-Success 'C official HTTPS byte replay'

    & $python '.\pipeline\run_verified_flood_site_reference.py' --region $RegionCode --raw $raw --records $rows --c-acceptance $cAudit --provenance $provenance --out $catalog
    Assert-Success 'D provenance-gated reference catalog'

    & $python '.\validation\validation\verify_gsi_catalog_acceptance.py' --region $RegionCode --raw $raw --records $rows --c-acceptance $cAudit --provenance $provenance --catalog $catalog --source-url $SourceUrl
    Assert-Success 'C cross-role local catalog acceptance'

    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) { throw 'Node.js is required to run the E consumer regressions.' }
    foreach ($test in @(
        '.\gis\tests\d_region_adapter.test.js',
        '.\gis\tests\map_controller.test.js',
        '.\gis\tests\region_exports.integration.test.js',
        '.\gis\tests\facility_list.test.js',
        '.\gis\tests\flood_discovery.test.js'
    )) {
        & $node.Source $test
        Assert-Success "E Node regression: $test"
    }

    if ($PublishPreview) {
        $currentBranch = [string](& git branch --show-current)
        $currentBranch = $currentBranch.Trim()
        Assert-Success 'Read git branch'
        if ($currentBranch -eq 'main') {
            throw 'Publishing is prohibited from a main checkout. Use an isolated preview worktree.'
        }
        $outputDir = Join-Path $repo ('pipeline\data\output\gsi_verified_tiles\' + $RegionCode)
        New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
        $previewCatalog = Join-Path $outputDir ('10-' + $tileX + '-' + $tileY + '.json')
        if (Test-Path -LiteralPath $previewCatalog) {
            throw "Preview output already exists; will not replace it: $previewCatalog"
        }
        # Stage in destination folder, then rename only after every check passes.
        $stagePath = Join-Path $outputDir ('.gsi-catalog-' + $runId + '.tmp')
        Copy-Item -LiteralPath $catalog -Destination $stagePath -ErrorAction Stop
        [System.IO.File]::Move($stagePath, $previewCatalog)
        Write-Host "Preview-only catalog created: $previewCatalog"
    } else {
        Write-Host 'Not published to static GIS. Add -PublishPreview in a fresh isolated worktree after review.'
    }
    Write-Host "LOCAL GSI ACCEPTANCE COMPLETE (NOT BROWSER OR EVACUATION SAFETY ACCEPTANCE)"
    Write-Host "Evidence (kept locally): $runDir"
}
finally {
    Pop-Location
}

if (-not ($SourceUrl -cmatch $pattern)) {
    throw 'SourceUrl must be exact official GSI skhb01 z10 HTTPS tile.'
}
$tileX = [int]$Matches[1]
$tileY = [int]$Matches[2]
if ($tileX -ge 1024 -or $tileY -ge 1024) {
    throw 'GSI z10 tile x/y out of range.'
}
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = (Resolve-Path -LiteralPath $PythonExe).Path
$raw = (Resolve-Path -LiteralPath $ArchivePath).Path
$found = (Get-FileHash -LiteralPath $raw -Algorithm SHA256).Hash
if ($ExpectedSha256 -and ($found -ine $ExpectedSha256)) {
    throw "Archived raw SHA256 mismatch. Original left unchanged: expected $ExpectedSha256 / actual $found"
}
if (-not (Test-Path -LiteralPath (Join-Path $repo 'validation\validation\verify_gsi_catalog_acceptance.py'))) {
    throw "This worktree lacks the current integrated local acceptance checker."
}

# Unique run folder; do not overwrite past audit JSON or edited source files.
$runId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$runDir = Join-Path $repo ("pipeline\data\verified\gsi-acceptance-runs\" + $runId)
New-Item -ItemType Directory -Force -Path $runDir -ErrorAction Stop | Out-Null
$rows = Join-Path $runDir 'gsi_records.json'
$cAudit = Join-Path $runDir 'c_raw_acceptance.json'
$provenance = Join-Path $runDir 'c_https_provenance.json'
$catalog = Join-Path $runDir 'edogawa_flood_site_catalog.json'
Write-Host "HINANEX validation run: $runDir"
Write-Host "Archived raw: $raw / SHA256: $found"

function Assert-Success([string]$stage) {
    if ($LASTEXITCODE -ne 0) {
        throw "$stage failed (exit $LASTEXITCODE). Existing archives and preview output were NOT changed."
    }
}

Push-Location $repo
try {
    & $python '.\pipeline\prepare_gsi_flood_tile.py' --region $RegionCode --raw $raw --source-url $SourceUrl --out $rows
    Assert-Success 'D source normalization'

    & $python '.\validation\validation\verify_gsi_flood_source.py' --region $RegionCode --raw $raw --source-url $SourceUrl --records $rows --acceptance-out $cAudit
    Assert-Success 'C independent raw-row audit'

    # This step contacts GSI. It must not be bypassed after network errors or changed bytes.
    & $python '.\validation\validation\verify_gsi_flood_provenance.py' --raw $raw --source-url $SourceUrl --c-acceptance $cAudit --report-out $provenance
    Assert-Success 'C official HTTPS byte replay'

    & $python '.\pipeline\run_verified_flood_site_reference.py' --region $RegionCode --raw $raw --records $rows --c-acceptance $cAudit --provenance $provenance --out $catalog
    Assert-Success 'D provenance-gated reference catalog'

    & $python '.\validation\validation\verify_gsi_catalog_acceptance.py' --region $RegionCode --raw $raw --records $rows --c-acceptance $cAudit --provenance $provenance --catalog $catalog --source-url $SourceUrl
    Assert-Success 'C cross-role local catalog acceptance'

    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) { throw 'Node.js is required to run the E consumer regressions.' }
    foreach ($test in @(
        '.\gis\tests\d_region_adapter.test.js',
        '.\gis\tests\map_controller.test.js',
        '.\gis\tests\region_exports.integration.test.js',
        '.\gis\tests\facility_list.test.js',
        '.\gis\tests\flood_discovery.test.js'
    )) {
        & $node.Source $test
        Assert-Success "E Node regression: $test"
    }

    if ($PublishPreview) {
        $currentBranch = [string](& git branch --show-current)
        $currentBranch = $currentBranch.Trim()
        Assert-Success 'Read git branch'
        if ($currentBranch -eq 'main') {
            throw 'Publishing is prohibited from a main checkout. Use an isolated preview worktree.'
        }
        $outputDir = Join-Path $repo 'pipeline\data\output'
        New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
        $previewCatalog = Join-Path $outputDir 'edogawa_flood_site_catalog.json'
        if (Test-Path -LiteralPath $previewCatalog) {
            throw "Preview output already exists; will not replace it: $previewCatalog"
        }
        # Stage in destination folder, then rename only after every check passes.
        $stagePath = Join-Path $outputDir ('.gsi-catalog-' + $runId + '.tmp')
        Copy-Item -LiteralPath $catalog -Destination $stagePath -ErrorAction Stop
        [System.IO.File]::Move($stagePath, $previewCatalog)
        Write-Host "Preview-only catalog created: $previewCatalog"
    } else {
        Write-Host 'Not published to static GIS. Add -PublishPreview in a fresh isolated worktree after review.'
    }
    Write-Host "LOCAL GSI ACCEPTANCE COMPLETE (NOT BROWSER OR EVACUATION SAFETY ACCEPTANCE)"
    Write-Host "Evidence (kept locally): $runDir"
}
finally {
    Pop-Location
}
