@echo off
REM Probe real Python 3 execution; WHERE alone also finds the Store alias.
REM Called by the database launchers inside their SETLOCAL scope.
set "FH_PYTHON="
call py -3 -c "import sys; sys.exit(sys.version_info.major != 3)" >nul 2>&1
if not errorlevel 1 (
    set "FH_PYTHON=py -3"
    exit /b 0
)
call python -c "import sys; sys.exit(sys.version_info.major != 3)" >nul 2>&1
if not errorlevel 1 (
    set "FH_PYTHON=python"
    exit /b 0
)
call python3 -c "import sys; sys.exit(sys.version_info.major != 3)" >nul 2>&1
if not errorlevel 1 (
    set "FH_PYTHON=python3"
    exit /b 0
)
echo ERROR: No working Python 3 interpreter was found.
echo Install Python 3 from https://www.python.org/downloads/windows/ with the Python launcher or add Python to PATH.
echo If Windows opens the Microsoft Store, disable the python.exe and python3.exe App execution aliases in Settings.
exit /b 1
