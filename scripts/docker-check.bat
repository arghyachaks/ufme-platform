@echo off
rem Double-click to run the local Docker gate (same as the pre-push hook). Log: tmp\docker-check.log
cd /d "%~dp0.."
set "BASH=%ProgramFiles%\Git\bin\bash.exe"
if not exist "%BASH%" set "BASH=bash"
"%BASH%" scripts/docker-check.sh
echo EXIT %ERRORLEVEL% >> tmp\docker-check.log
