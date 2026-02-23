Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Repo root = parent of /scripts
$repo = Split-Path -Parent $PSScriptRoot

Write-Progress -Activity "HITECH_FORMS snapshot validate" -Status "Validating snapshot" -PercentComplete 55
python (Join-Path $repo "tools\snapshot\validate_snapshot.py")

Write-Progress -Activity "HITECH_FORMS snapshot validate" -Status "Done" -PercentComplete 100
Start-Process explorer.exe (Join-Path $repo "docs\snapshots")
