@echo off
REM divineos wrapper shim — Windows cmd/PowerShell entry point.
REM Dispatches to scripts/divineos_wrapper.py which finds the CWD's
REM sealed venv and execs its divineos CLI. Fails loud if no sealed
REM venv is found — deliberately does not fall back to a system install
REM (that would reintroduce the pip ping-pong bug at the wrapper layer).
REM
REM Install: copy this file to a directory on your PATH that precedes
REM the system-wide Scripts directory. For example:
REM   %USERPROFILE%\bin\divineos.cmd
REM
REM Note: this shim uses `python` from PATH to run the wrapper module.
REM The wrapper itself does not depend on any installed package — it
REM only uses stdlib (glob, os, sys, pathlib). So even if the system
REM has no divineos installed, this shim + the wrapper .py work.
REM
REM See docs/pip_pingpong_wrapper_design.md for the full design.

setlocal
set "SCRIPT_DIR=%~dp0"

REM If invoked from %USERPROFILE%\bin\ the wrapper isn't next to us —
REM check both this dir and the DivineOS scripts/ dir via CWD-walk.
if exist "%SCRIPT_DIR%divineos_wrapper.py" (
    python "%SCRIPT_DIR%divineos_wrapper.py" %*
    exit /b %ERRORLEVEL%
)

REM Fallback: find the wrapper via the CWD's .envrc marker + scripts/ dir.
REM (Same walk-up logic the wrapper itself uses, in cmd.)
set "CUR=%CD%"
:walk
if exist "%CUR%\.envrc" (
    if exist "%CUR%\scripts\divineos_wrapper.py" (
        python "%CUR%\scripts\divineos_wrapper.py" %*
        exit /b %ERRORLEVEL%
    )
)
for %%I in ("%CUR%") do set "PARENT=%%~dpI"
set "PARENT=%PARENT:~0,-1%"
if "%PARENT%"=="%CUR%" goto notfound
set "CUR=%PARENT%"
goto walk

:notfound
echo divineos: could not locate divineos_wrapper.py 1>&2
echo   Checked: %~dp0divineos_wrapper.py 1>&2
echo   And walked up from %CD% looking for scripts/divineos_wrapper.py at any .envrc marker root. 1>&2
echo   Install the wrapper alongside this shim or from a DivineOS checkout. 1>&2
exit /b 4
