@echo off
REM Compatibility entry point; see docs/UNATTENDED_PIPELINE.md.
call "%~dp0run_pipeline.bat" weekly --training-args %*
exit /b %errorlevel%
