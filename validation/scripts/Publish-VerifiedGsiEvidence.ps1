# Restore a locally C-accepted tile after publication-only failure.
# Uses preserved evidence; does NOT perform a new official HTTPS fetch.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$EvidenceDirectory,
    [Parameter(Mandatory = $true)] [string]$ArchivePath,
    [Parameter(Mandatory = $true)] [string]$SourceUrl,
    [ValidateSet('13123', '15100', '23100')]
    [string]$RegionCode = '13123',
    [string]$PythonExe = 'C:\HINANEX\pipeline\.venv\Scripts\python.exe',
    [switch]$PublishPreview
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$evidence = (Resolve-Path -LiteralPath $EvidenceDirectory).Path
$raw = (Resolve-Path -LiteralPath $ArchivePath).Path
$python = (Resolve-Path -LiteralPath $PythonExe).Path
$pattern = '^https://cyberjapandata\.gsi\.go\.jp/xyz/skhb01/10/(\d+)/(\d+)\.geojson$'
if (-not ($SourceUrl -cmatch $pattern)) {
    throw 'SourceUrl must be exact official GSI skhb01 z10 tile URL.'
}
$x = [int]$Matches[1]
$y = [int]$Matches[2]
if ($x -ge 1024 -or $y -ge 1024) {
    throw 'Official GSI z10 tile coordinates out of range.'
}

$records = Join-Path $evidence 'gsi_records.json'
$cAudit = Join-Path $evidence 'c_raw_acceptance.json'
$provenance = Join-Path $evidence 'c_https_provenance.json'
$catalog = Join-Path $evidence 'gsi_flood_site_catalog.json'
foreach ($required in @($records, $cAudit, $provenance, $catalog)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Complete C/D provenance evidence required: $required"
    }
}
# The read-only checker recomputes independent raw acceptance and the D output,
# verifies archived hash, the existing C HTTPS MATCH report, and tile geometry.
$verifyArgs = @(
    (Join-Path $repo 'validation\validation\verify_gsi_catalog_acceptance.py'),
    '--region', $RegionCode, '--raw', $raw, '--records', $records,
    '--c-acceptance', $cAudit, '--provenance', $provenance,
    '--catalog', $catalog, '--source-url', $SourceUrl
)
& $python @verifyArgs
if ($LASTEXITCODE -ne 0) {
    throw "Saved official-source evidence could not be revalidated (exit $LASTEXITCODE)."
}
Write-Host 'Saved C HTTPS MATCH and D catalog revalidated; NO fresh network replay was done.'
if (-not $PublishPreview) {
    Write-Host 'No static GIS file written. Use -PublishPreview explicitly in a preview worktree.'
    return
}
# A detached worktree prints literal HEAD rather than an empty branch string.
$refs = @(& git -C $repo rev-parse --abbrev-ref HEAD)
if ($LASTEXITCODE -ne 0 -or $refs.Count -ne 1 -or
    [string]::IsNullOrWhiteSpace([string]$refs[0])) {
    throw 'Git worktree not identifiable; refusing publication.'
}
if (([string]$refs[0]).Trim() -eq 'main') {
    throw 'Never publish a preview artifact from the main worktree.'
}

$destinationDir = Join-Path $repo ('pipeline\data\output\gsi_verified_tiles\' + $RegionCode)
$destination = Join-Path $destinationDir ('10-' + $x + '-' + $y + '.json')
if (Test-Path -LiteralPath $destination) {
    throw "Tile already published; refusing overwrite: $destination"
}
New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
$temp = Join-Path $destinationDir ('.staged-' + [guid]::NewGuid().ToString('N') + '.tmp')
try {
    Copy-Item -LiteralPath $catalog -Destination $temp -ErrorAction Stop
    [System.IO.File]::Move($temp, $destination)
}
finally {
    if (Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Force
    }
}
Write-Host "Published immutable reference-only tile: $destination"
Write-Host 'This is NOT certification of site opening, safety or municipal completeness.'
