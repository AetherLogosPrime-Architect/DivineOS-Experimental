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
REM before python runs), losing python's actual exit code. Symptom this
REM fixed: divineos prereg show <fake-id> returned exit 0 in subprocess
REM environments (pytest fixtures with fresh DIVINEOS_HOME) even though
REM the CLI code raised click.exceptions.Exit(1). Class of failure:
REM silent exit-code loss making fake substrate IDs pass
REM closure_verification. See tests/test_closure_verification.py
REM test_plausible_but_fake_substrate_id_fails.
REM
REM 2026-08-06 (Aether found it again, in the INSTALLED copy on PATH; Aria
REM ported the form back here). The 07-26 fix used
REM `setlocal enabledelayedexpansion` + !ERRORLEVEL!, which works but has a
REM cost this shim cannot pay: delayed expansion changes how `!` is treated
REM in EVERY argument forwarded through %*, and this shim forwards arbitrary
REM user text - claim statements, correction bodies, letter subjects. A user
REM typing `divineos learn "wait!"` would have the `!` eaten.
REM
REM The goto form fixes the same bug without that cost: the dispatch is no
REM longer inside parentheses, so %ERRORLEVEL% expands on its own line at
REM execution time. No delayed expansion, no argument mangling.
REM
REM ROOT CAUSE OF FINDING IT TWICE: this file is INSTALLED BY HAND-COPYING
REM to a PATH directory. The 07-26 repo fix therefore never reached the file
REM that actually runs, and the 08-06 fix to the running file never reached
REM the repo. Two copies, six weeks, one bug, neither fix propagating. See
REM scripts/check_installed_shim.py, which now measures the drift.
setlocal
set "SCRIPT_DIR=%~dp0"

if not exist "%SCRIPT_DIR%divineos_wrapper.py" goto :no_wrapper

python "%SCRIPT_DIR%divineos_wrapper.py" %*
exit /b %ERRORLEVEL%

:no_wrapper
echo divineos: wrapper .py not found next to this .cmd 1>&2
echo   Expected: %SCRIPT_DIR%divineos_wrapper.py 1>&2
echo   Fix: copy scripts/divineos_wrapper.py from a DivineOS checkout to that path. 1>&2
exit /b 4
