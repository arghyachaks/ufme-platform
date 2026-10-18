# UFME developer commands for Windows PowerShell.
# Usage: .\scripts\dev.ps1 <command>
#   stack     start Postgres, Redis, API and worker in Docker
#   deps      start only Postgres and Redis (run the API yourself with 'api')
#   setup     create services\api\.venv and install dev dependencies
#   api       run the API with hot reload (needs 'deps' running)
#   migrate   apply database migrations
#   test      run backend tests (SQLite, no Docker needed)
#   format    auto-fix imports and formatting (run before committing)
#   lint      ruff + mypy
#   types     regenerate frontend TypeScript types from the running API
#   down      stop the Docker stack
param([Parameter(Position = 0)][string]$Command = "help")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Api = Join-Path $Root "services\api"
$Compose = Join-Path $Root "infra\docker\docker-compose.yml"
$Py = Join-Path $Api ".venv\Scripts\python.exe"

switch ($Command) {
  "stack"   { docker compose -f $Compose up --build -d; Write-Host "API: http://127.0.0.1:8000/docs" }
  "deps"    { docker compose -f $Compose up -d postgres redis }
  "down"    { docker compose -f $Compose down }
  "setup"   { Push-Location $Api; python -m venv .venv; & $Py -m pip install -r requirements-dev.txt; Pop-Location }
  "api"     { Push-Location $Api; & $Py -m uvicorn app.main:app --reload; Pop-Location }
  "migrate" { Push-Location $Api; & $Py -m alembic upgrade head; Pop-Location }
  "test"    { Push-Location $Api; & $Py -m pytest --cov=app --cov-report=term-missing; Pop-Location }
  "format"  { Push-Location $Api; & $Py -m ruff check --fix .; & $Py -m ruff format .; Pop-Location }
  "lint"    { Push-Location $Api; & $Py -m ruff check .; & $Py -m ruff format --check .; & $Py -m mypy app; Pop-Location }
  "types"   { Push-Location (Join-Path $Root "apps\web"); npm run gen:api-types; Pop-Location }
  default   { Get-Content $PSCommandPath | Select-Object -Skip 1 -First 12 }
}
