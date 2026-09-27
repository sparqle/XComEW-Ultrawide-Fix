@echo off
setlocal
if defined VIRTUAL_ENV (
    "%VIRTUAL_ENV%\Scripts\python.exe" "%~dp0build.py"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0build.py"
) else (
    py -3 "%~dp0build.py"
)
exit /b %errorlevel%
