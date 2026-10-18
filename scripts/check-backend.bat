@echo off
rem Sets up the backend venv, formats, lints, tests, and installs web deps. Log: tmp\checks.log
setlocal
cd /d "%~dp0.."
set LOG=%CD%\tmp\checks.log
if not exist tmp mkdir tmp
echo ==== %DATE% %TIME% > "%LOG%"
cd services\api
set PYEXE=
for %%D in ("%LOCALAPPDATA%\Programs\Python" "%ProgramFiles%" "%ProgramFiles(x86)%" "C:" "%USERPROFILE%\anaconda3" "%USERPROFILE%\miniconda3" "%LOCALAPPDATA%\anaconda3" "%ProgramData%\anaconda3") do (
  for /d %%P in ("%%~D\Python3*") do if exist "%%~P\python.exe" set "PYEXE=%%~P\python.exe"
  if exist "%%~D\python.exe" set "PYEXE=%%~D\python.exe"
)
if not defined PYEXE (where py >nul 2>&1 && set "PYEXE=py")
echo ---- candidates >> "%LOG%"
dir /b /s "%LOCALAPPDATA%\Programs\Python\python.exe" "C:\Python3*" >> "%LOG%" 2>&1
where python python3 py >> "%LOG%" 2>&1
echo PYEXE=%PYEXE% >> "%LOG%"
echo ---- python >> "%LOG%"
"%PYEXE%" --version >> "%LOG%" 2>&1
if not exist .venv\Scripts\python.exe ("%PYEXE%" -m venv .venv >> "%LOG%" 2>&1)
echo ---- pip >> "%LOG%"
.venv\Scripts\python.exe -m pip install -q -r requirements-dev.txt >> "%LOG%" 2>&1
echo ---- format >> "%LOG%"
.venv\Scripts\python.exe -m ruff check --fix . >> "%LOG%" 2>&1
.venv\Scripts\python.exe -m ruff format . >> "%LOG%" 2>&1
echo ---- lint >> "%LOG%"
.venv\Scripts\python.exe -m ruff check . >> "%LOG%" 2>&1
.venv\Scripts\python.exe -m mypy app >> "%LOG%" 2>&1
echo ---- tests >> "%LOG%"
.venv\Scripts\python.exe -m pytest -p no:cacheprovider --cov=app --cov-report=term >> "%LOG%" 2>&1
echo ---- npm >> "%LOG%"
cd ..\..\apps\web
echo ==== DONE >> "%LOG%"
endlocal
exit
