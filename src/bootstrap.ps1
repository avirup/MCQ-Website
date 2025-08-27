#!/usr/bin/env pwsh
Write-Host "Setting up MCQ Platform (Windows)" -ForegroundColor Cyan

if (-Not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Green
    python -m venv venv
}

Write-Host "Activating venv and installing requirements..." -ForegroundColor Green
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Setup complete. To start the server, run:" -ForegroundColor Yellow
Write-Host "venv\Scripts\activate" -ForegroundColor Yellow
Write-Host "flask run" -ForegroundColor Yellow
