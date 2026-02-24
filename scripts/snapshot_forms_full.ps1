Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Repo root = parent of /scripts
$repo = Split-Path -Parent $PSScriptRoot

Write-Progress -Activity "HITECH_FORMS full snapshot" -Status "Generating full snapshot" -PercentComplete 40
python (Join-Path $repo "tools\snapshot\forms_snapshot_full.py")

Write-Progress -Activity "HITECH_FORMS full snapshot" -Status "Done" -PercentComplete 100
Start-Process explorer.exe (Join-Path $repo "docs\snapshots")
