<#
.SYNOPSIS
    Local development launcher for the AUTOSAR HLD Analysis Assistant.

.DESCRIPTION
    Starts the FastAPI backend on port 8000 and the Streamlit UI on port 8501.
    Creates the virtual environment and installs dependencies on first run.

.PARAMETER Setup
    Only create the environment and install dependencies, then exit.

.PARAMETER Test
    Run the unit test suite and exit.

.PARAMETER Smoke
    Run the end-to-end smoke test against an already running backend, then exit.

.EXAMPLE
    .\run.ps1
    .\run.ps1 -Setup
    .\run.ps1 -Test
#>
[CmdletBinding()]
param(
    [switch]$Setup,
    [switch]$Test,
    [switch]$Smoke
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
    & $python -m pip install --upgrade pip
    Write-Host "Installing dependencies (this takes several minutes the first time)..." -ForegroundColor Cyan
    & $python -m pip install -r requirements.txt
}

if (-not (Test-Path (Join-Path $root ".env"))) {
    Copy-Item (Join-Path $root ".env.example") (Join-Path $root ".env")
    Write-Host "Created .env from .env.example" -ForegroundColor Green
}

if ($Setup) {
    Write-Host "Setup complete." -ForegroundColor Green
    exit 0
}

if ($Test) {
    & $python -m pytest tests -q
    exit $LASTEXITCODE
}

if ($Smoke) {
    & $python scripts\smoke_test.py
    exit $LASTEXITCODE
}

# Report whether a local model is reachable, without blocking startup.
try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
    Write-Host "Ollama is reachable." -ForegroundColor Green
}
catch {
    Write-Host "Ollama is not running. The platform will start in retrieval-only mode." -ForegroundColor Yellow
    Write-Host "  To enable generated summaries: install Ollama, then run" -ForegroundColor Yellow
    Write-Host "    ollama pull qwen2.5:7b-instruct" -ForegroundColor Yellow
}

Write-Host "Starting backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
$api = Start-Process -FilePath $python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -PassThru -NoNewWindow

# The first start loads the embedding model, which can take a while.
$ready = $false
foreach ($attempt in 1..60) {
    Start-Sleep -Seconds 2
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 3 | Out-Null
        $ready = $true
        break
    }
    catch { }
}

if (-not $ready) {
    Write-Host "Backend did not become healthy in time." -ForegroundColor Red
    if (-not $api.HasExited) { Stop-Process -Id $api.Id -Force }
    exit 1
}

Write-Host "Backend ready. Starting the UI on http://localhost:8501 ..." -ForegroundColor Green
try {
    & $python -m streamlit run ui/Home.py --server.port 8501
}
finally {
    if (-not $api.HasExited) {
        Write-Host "Stopping the backend..." -ForegroundColor Cyan
        Stop-Process -Id $api.Id -Force
    }
}
