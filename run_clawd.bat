@echo off
rem Double-click this to start Clawd with no console window.
rem Tries pythonw, then the py launcher's windowed/normal variants.
cd /d "%~dp0"

where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw "clawd.pyw"
    exit /b
)

where pyw >nul 2>&1
if %errorlevel%==0 (
    start "" pyw "clawd.pyw"
    exit /b
)

where py >nul 2>&1
if %errorlevel%==0 (
    start "" py "clawd.pyw"
    exit /b
)

echo.
echo Python was not found on PATH.
echo Install it from python.org and tick "Add python.exe to PATH",
echo or start Clawd manually with:   py clawd.pyw
echo.
pause
