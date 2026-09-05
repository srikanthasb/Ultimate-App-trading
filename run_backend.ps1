$ErrorActionPreference = 'Stop'
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host 'Create the virtual environment first: python -m venv .venv' -ForegroundColor Yellow
    exit 1
}
& .\.venv\Scripts\python.exe -m uvicorn src.api.api:app --host 127.0.0.1 --port 8000
