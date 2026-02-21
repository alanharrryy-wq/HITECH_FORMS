
$ErrorActionPreference = "Stop"

function Step($percent, $msg) {
  Write-Progress -Activity "HITECH_FORMS Bootstrap" -Status $msg -PercentComplete $percent
  Write-Host "[$percent%] $msg"
}

Step 5 "Setting deterministic environment..."
$env:PYTHONHASHSEED = "0"

Step 10 "Ensuring folders..."
$folders = @(".\.venv", ".\var", ".\var\logs", ".\var\exports")
foreach ($f in $folders) { if (!(Test-Path $f)) { New-Item -ItemType Directory -Path $f | Out-Null } }

Step 20 "Creating venv if missing..."
if (!(Test-Path ".\.venv\Scripts\python.exe")) { python -m venv .\.venv }
$Py = ".\.venv\Scripts\python.exe"

Step 30 "Upgrading pip..."
& $Py -m pip install --upgrade pip

Step 42 "Installing dependencies..."
& $Py -m pip install -r .\requirements.txt
& $Py -m pip install -r .\requirements-dev.txt

Step 50 "Installing project (editable)..."
& $Py -m pip install -e .

Step 65 "Running migrations..."
& $Py -m hitech_forms.ops.cli db upgrade

Step 75 "Seeding demo data (idempotent)..."
& $Py -m hitech_forms.ops.cli seed --demo

Step 82 "Ruff auto-fix + format..."
& $Py -m ruff check src tests --fix
& $Py -m ruff format src tests

Step 88 "Running integration gate (Wave 1)..."
& $Py -m hitech_forms.ops.ci lint
& $Py -m hitech_forms.ops.ci typecheck
& $Py -m hitech_forms.ops.ci start-smoke
& $Py -m hitech_forms.ops.ci e2e --flows smoke_health
& $Py -m hitech_forms.ops.ci determinism-check

Step 92 "Starting server..."
$port = 8000
$env:HFORMS_DB_PATH = ".\var\hitech_forms.db"
$env:HFORMS_HOST = "127.0.0.1"
$env:HFORMS_PORT = "$port"
Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command `"$Py -m hitech_forms.ops.cli runserver --host 127.0.0.1 --port $port`""

Step 97 "Opening browser..."
Start-Sleep -Seconds 1
Start-Process "http://127.0.0.1:$port/admin/forms"

Step 100 "Done. 🚀"
Write-Progress -Activity "HITECH_FORMS Bootstrap" -Completed

