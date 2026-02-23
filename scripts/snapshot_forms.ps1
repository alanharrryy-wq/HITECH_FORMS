Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Repo root = parent of /scripts
$repo = Split-Path -Parent $PSScriptRoot

Write-Progress -Activity "HITECH_FORMS snapshot" -Status "Generating snapshot" -PercentComplete 35
python (Join-Path $repo "tools\snapshot\forms_snapshot.py")

Write-Progress -Activity "HITECH_FORMS snapshot" -Status "Done" -PercentComplete 100
Start-Process explorer.exe (Join-Path $repo "docs\snapshots")
