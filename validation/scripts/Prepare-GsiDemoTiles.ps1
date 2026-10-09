# Explicit user-invoked GSI z10 demo coverage seeding (PowerShell 5.1+).
# Downloads official raw tiles to UNIQUE local files, C-audits and HTTPS-replays
# via the acceptance runner. Never publishes GIS without -PublishPreview.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [double]$Latitude,
    [Parameter(Mandatory = $true)] [double]$Longitude,
    [ValidateSet('13123', '15100', '23100')]
    [string]$RegionCode = '13123',
    [string]$PythonExe = 'C:\HINANEX\pipeline\.venv\Scripts\python.exe',
    [switch]$IncludeNeighbors,
    [switch]$NeighborsOnly,
    [switch]$PublishPreview
)
$ErrorActionPreference = 'Stop'
if ([double]::IsNaN($Latitude) -or [double]::IsInfinity($Latitude) -or
    [double]::IsNaN($Longitude) -or [double]::IsInfinity($Longitude) -or
    [math]::Abs($Latitude) -gt 85.05112878 -or
    $Longitude -lt -180 -or $Longitude -gt 180) {
    throw 'Outside valid GSI Web Mercator coordinate range.'
}
$z = 10
$n = 1024
$rad = $Latitude * [math]::PI / 180
$x = [int][math]::Floor(($Longitude + 180) / 360 * $n)
$y = [int][math]::Floor((1 - [math]::Log([math]::Tan($rad) + 1 / [math]::Cos($rad)) / [math]::PI) / 2 * $n)
$x = [math]::Max(0, [math]::Min($n - 1, $x))
$y = [math]::Max(0, [math]::Min($n - 1, $y))
$tiles = @(@{ X = $x; Y = $y; Origin = $true })
if ($IncludeNeighbors) {
    foreach ($dy in -1..1) {
        foreach ($dx in -1..1) {
            if ($dx -eq 0 -and $dy -eq 0) { continue }
            $nextY = $y + $dy
            if ($nextY -lt 0 -or $nextY -ge $n) { continue }
            $tiles += @{ X = (($x + $dx + $n) % $n); Y = $nextY; Origin = $false }
        }
    }
}
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$runner = Join-Path $PSScriptRoot 'Run-GsiFloodLocalAcceptance.ps1'

if ($NeighborsOnly) {
    if (-not $IncludeNeighbors -or -not $PublishPreview) {
        throw 'NeighborsOnly requires -IncludeNeighbors and -PublishPreview.'
    }
    # Mere JSON file existence never bypasses C acceptance. The published file
    # must equal archived audit output by SHA and re-pass independent checks.
    $originUrl = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/$x/$y.geojson"
    $originOutput = Join-Path $repo ('pipeline\data\output\gsi_verified_tiles\' +
        $RegionCode + '\10-' + $x + '-' + $y + '.json')
    if (-not (Test-Path -LiteralPath $originOutput -PathType Leaf)) {
        throw "Origin tile must already be published: $originOutput"
    }
    $published = Get-Content -LiteralPath $originOutput -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$published.status -cne 'REFERENCE_ONLY' -or
        [string]$published.source_status -cne 'C_ACCEPTED' -or
        [string]$published.https_provenance_status -cne 'MATCH' -or
        [string]$published.region_code -cne $RegionCode -or
        [string]$published.source_raw_sha256 -notmatch '^[0-9a-fA-F]{64}$' -or
        @($published.sites).Count -lt 1 -or
        [string]$published.sites[0].source_url -cne $originUrl) {
        throw 'Origin publication contract is invalid; refuse neighbor-only run.'
    }
    $publishedDigest = (Get-FileHash -LiteralPath $originOutput -Algorithm SHA256).Hash
    $evidenceRoot = Join-Path $repo 'pipeline\data\verified\gsi-acceptance-runs'
    $rawRoot = Join-Path $repo 'pipeline\data\raw\gsi-demo-runs'
    if (-not (Test-Path -LiteralPath $evidenceRoot -PathType Container) -or
        -not (Test-Path -LiteralPath $rawRoot -PathType Container)) {
        throw 'Original archived raw data and C audit evidence are required.'
    }
    $evidence = @(Get-ChildItem -LiteralPath $evidenceRoot -Directory |
        Where-Object {
            $p = Join-Path $_.FullName 'gsi_flood_site_catalog.json'
            (Test-Path -LiteralPath $p -PathType Leaf) -and
            ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -eq $publishedDigest)
        })
    if ($evidence.Count -ne 1) {
        throw 'No unique original C/D audit catalog matches published origin SHA256.'
    }
    $archives = @(Get-ChildItem -LiteralPath $rawRoot -Recurse -File -Filter ("10-" + $x + "-" + $y + ".geojson") |
        Where-Object {
            (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash -eq
                [string]$published.source_raw_sha256
        })
    if ($archives.Count -lt 1) {
        throw 'No matching original GSI raw bytes found; refuse neighbor-only run.'
    }
    $recovery = Join-Path $PSScriptRoot 'Publish-VerifiedGsiEvidence.ps1'
    & $recovery -EvidenceDirectory $evidence[0].FullName -ArchivePath $archives[0].FullName -SourceUrl $originUrl -RegionCode $RegionCode -PythonExe $PythonExe
    if (-not $?) {
        throw 'Read-only C proof revalidation failed for the published origin.'
    }
    $tiles = @($tiles | Where-Object { -not $_.Origin })
    Write-Host "Published origin $z/$x/$y independently revalidated; now fetching neighbors only."
}

if (-not (Test-Path -LiteralPath $runner)) { throw 'Verification runner missing.' }
$runId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$archiveDir = Join-Path $repo ('pipeline\data\raw\gsi-demo-runs\' + $runId)
New-Item -ItemType Directory -Force -Path $archiveDir -ErrorAction Stop | Out-Null
Write-Host "Coarse GSI tile URLs will be requested; no exact GPS coordinate is sent."
Write-Host "Origin tile: $z/$x/$y; tiles $($tiles.Count); archives $archiveDir"
$verified = 0
$unverified = 0
foreach ($tile in $tiles) {
    $tx = [int]$tile.X
    $ty = [int]$tile.Y
    $url = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/$z/$tx/$ty.geojson"
    $raw = Join-Path $archiveDir ("10-" + $tx + "-" + $ty + ".geojson")
    try {
        Invoke-WebRequest -Uri $url -OutFile $raw -UseBasicParsing -TimeoutSec 45 -ErrorAction Stop | Out-Null
        if ((Get-Item -LiteralPath $raw).Length -eq 0) { throw 'Official response was empty.' }
        $hash = (Get-FileHash -LiteralPath $raw -Algorithm SHA256).Hash
        & $runner -ArchivePath $raw -SourceUrl $url -ExpectedSha256 $hash -RegionCode $RegionCode -PythonExe $PythonExe -PublishPreview:$PublishPreview
        $verified += 1
        Write-Host "VERIFIED tile: $z/$tx/$ty"
    }
    catch {
        $unverified += 1
        # The error might have occurred AFTER C HTTPS MATCH and all Node tests,
        # e.g. the opt-in static publication step. Do not relabel that audit as
        # failed or claim that the official source was unverified.
        Write-Warning ("TILE PIPELINE INCOMPLETE " + $z + "/" + $tx + "/" + $ty +
            " (validation OR publication; inspect the preserved audit folder): " +
            $_.Exception.Message)
        if ($tile.Origin) {
            throw 'Origin tile pipeline did not complete. Preserve its audit evidence and inspect the original error.'
        }
    }
}
Write-Host "Result: verified $verified tile(s); unverified $unverified tile(s)."
Write-Host "No evacuation safety, current opening, municipal coverage or nationwide completeness claim."
if (-not $PublishPreview) {
    Write-Host 'GIS unchanged. Use -PublishPreview explicitly in an isolated preview worktree.'
}
