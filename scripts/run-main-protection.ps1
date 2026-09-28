$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "setup-main-protection.ps1"
$content = Get-Content -Path $scriptPath -Raw -Encoding UTF8
$scriptBlock = [scriptblock]::Create($content)
& $scriptBlock @args
