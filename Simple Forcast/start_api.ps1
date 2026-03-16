# ThingsBoard Power Forecast API - Startup Script
# Run this script to start the API server on Windows

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ThingsBoard Power Forecast API - Startup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please create a .env file from .env.template" -ForegroundColor Yellow
    Write-Host "Example:" -ForegroundColor White
    Write-Host "  Copy-Item .env.template .env" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Then edit .env with your ThingsBoard credentials." -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Cyan
    pause
    exit
}

Write-Host "✓ Configuration file found" -ForegroundColor Green

# Check if virtual environment exists
if (Test-Path "venv") {
    Write-Host "✓ Virtual environment found" -ForegroundColor Green
    Write-Host "  Activating virtual environment..." -ForegroundColor Gray
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "ℹ  No virtual environment found (optional)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Starting API server..." -ForegroundColor Green
Write-Host ""
Write-Host "API will be available at:" -ForegroundColor White
Write-Host "  - Swagger UI:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  - ReDoc:        http://localhost:8000/redoc" -ForegroundColor Cyan
Write-Host "  - Health Check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Start the API
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
