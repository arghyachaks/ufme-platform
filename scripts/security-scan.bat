@echo off
rem Release check: dependency and container scans with no high/critical findings.
rem Open-source scanners only: pip-audit (PyPA), npm audit, Trivy (Aqua Security). Log: tmp\security-scan.log
setlocal
cd /d "%~dp0.."
set LOG=%CD%\tmp\security-scan.log
set COMPOSE=docker compose -f infra/docker/docker-compose.yml
echo ==== %DATE% %TIME% > "%LOG%"
set FAIL=0

echo ---- python dependencies (pip-audit) >> "%LOG%"
%COMPOSE% --profile test run --rm --no-deps api-test pip-audit --progress-spinner off >> "%LOG%" 2>&1
if errorlevel 1 set FAIL=1

echo ---- web dependencies (npm audit, high+) >> "%LOG%"
%COMPOSE% --profile test run --rm --no-deps web-test sh -c "cd /repo && npm audit --omit=dev --audit-level=high" >> "%LOG%" 2>&1
if errorlevel 1 set FAIL=1

echo ---- container images (Trivy, HIGH/CRITICAL, fixable) >> "%LOG%"
%COMPOSE% build api >> "%LOG%" 2>&1
for %%I in (ufme-api) do (
  docker run --rm -v //var/run/docker.sock:/var/run/docker.sock -v ufme-trivy-cache:/root/.cache aquasec/trivy:0.57.1 image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 --no-progress %%I >> "%LOG%" 2>&1
  if errorlevel 1 set FAIL=1
)

if %FAIL%==0 (echo RESULT: PASS >> "%LOG%") else (echo RESULT: FINDINGS - see above >> "%LOG%")
echo EXIT %FAIL% >> "%LOG%"
exit /b %FAIL%
