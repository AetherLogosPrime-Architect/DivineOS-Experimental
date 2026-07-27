@echo off
REM divineos wrapper shim - Windows cmd/PowerShell entry point.
REM ASCII-only: cmd.exe mis-parses em-dash and non-ASCII chars in .cmd files.
REM Dispatches to divineos_wrapper.py which finds the CWD sealed venv and
REM execs its divineos CLI. Fails loud if no sealed venv is found -
REM deliberately does not fall back to a system install (that would
REM reintroduce the pip ping-pong bug at the wrapper layer).
REM
REM Install: copy this file to a directory on PATH before Python Scripts:
REM   %USERPROFILE%\.local\bin\divineos.cmd  (or wherever)
REM Also copy divineos_wrapper.py to the same directory (adjacent-install).
REM
REM See docs/pip_pingpong_wrapper_design.md for the full design.

REM ERRORLEVEL propagation bug fix 2026-07-26: %ERRORLEVEL% inside a
REM parenthesized block is PARSE-time expanded (captures ERRORLEVEL=0
REM before python runs), losing python's actual exit code. Delayed
REM expansion !ERRORLEVEL! is RUNTIME-evaluated per line. Symptom
REM this fixed: divineos prereg show <fake-id> returned exit 0 in
REM subprocess environments (pytest fixtures with fresh DIVINEOS_HOME)
REM even though the CLI code raised click.exceptions.Exit(1). Class
REM of failure: silent exit-code loss making fake substrate IDs pass
REM closure_verification. See tests/test_closure_verification.py
REM test_plausible_but_fake_substrate_id_fails.
setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"

if exist "%SCRIPT_DIR%divineos_wrapper.py" (
    python "%SCRIPT_DIR%divineos_wrapper.py" %*
    exit /b !ERRORLEVEL!
)

echo divineos: wrapper .py not found next to this .cmd 1>&2
echo   Expected: %SCRIPT_DIR%divineos_wrapper.py 1>&2
echo   Fix: copy scripts/divineos_wrapper.py from a DivineOS checkout to that path. 1>&2
exit /b 4
