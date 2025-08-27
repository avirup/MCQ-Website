
Param(
    [string]$PythonExe = "python",
    [string]$FlaskApp = "manage.py"
)

Write-Host "== MCQ Platform Bootstrap ==" -ForegroundColor Cyan

# 1) Create venv if missing
if (!(Test-Path -Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $PythonExe -m venv venv
    if ($LASTEXITCODE -ne 0) { throw "Failed to create venv" }
}

# 2) Activate venv
$venvActivate = ".\venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "Activating venv..." -ForegroundColor Yellow
    & $venvActivate
} else {
    throw "Activation script not found: $venvActivate"
}

# 3) Install requirements
Write-Host "Installing requirements..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Failed to install requirements" }

# 4) Set FLASK_APP for the session
$env:FLASK_APP = $FlaskApp
if (Test-Path ".flaskenv") {
    Write-Host "Using .flaskenv for FLASK settings (development)"
} else {
    Write-Host "FLASK_APP set to $FlaskApp"
}

# 5) Initialize DB migrations if missing
if (!(Test-Path ".\migrations")) {
    Write-Host "Initializing migrations..." -ForegroundColor Yellow
    flask db init
} else {
    Write-Host "Migrations already initialized."
}

# 6) Run migrate & upgrade (safe even if no changes)
Write-Host "Running migrate & upgrade..." -ForegroundColor Yellow
flask db migrate -m "auto" | Out-Null
flask db upgrade

# 7) Run server
Write-Host "Starting Flask dev server at http://127.0.0.1:5000 ..." -ForegroundColor Green
flask run
