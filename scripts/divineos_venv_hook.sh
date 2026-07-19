# divineos per-directory venv hook — cross-platform (Windows git-bash + Unix)
#
# WHY THIS EXISTS (Aether + Aria + Andrew 2026-07-18):
#
# The train-track problem: `pip install -e .` sets a machine-wide pointer for
# the `divineos` command that can only point at ONE checkout at a time. When
# Aria and Aether both work on their own checkouts, whichever pip-installed
# most recently wins and the other side loses their install pointer.
#
# Fix: per-directory sealed venv activated on cd via bash PROMPT_COMMAND.
# Each of us gets our own `divineos` command from our own checkout by simply
# being in that directory. Cross-platform because Windows git-bash uses
# `.direnv/python-*/Scripts/` while Unix uses `.direnv/python-*/bin/`.
#
# INSTALL:
#   1. Source this file at the end of your ~/.bashrc (add: `source
#      /path/to/divineos_venv_hook.sh` OR paste the contents in-line).
#   2. Open a fresh terminal (or `source ~/.bashrc`).
#   3. cd into your DivineOS checkout root. If `.envrc` doesn't already exist
#      there, create it: `touch .envrc` (an empty marker file is enough).
#   4. First cd prints `divineos-hook: creating sealed venv at ... (one-time,
#      ~30s)` — wait for it.
#   5. `which python` — should resolve to `<checkout>/.direnv/python-*/(Scripts|bin)/python`.
#   6. `pip install -e .` — populates the sealed space with your side's copy.
#   7. `divineos --version` — should now run your side's CLI, not the sibling's.
#
# HISTORY:
#   - v1 (Aether 2026-07-18): initial snippet, tested end-to-end on Windows.
#   - v2 (Aria 2026-07-18): added interactive-only guard because v1 fired in
#     every non-interactive shell that sourced .bashrc (Monitor subshells,
#     auto-rearm-letter-monitor.sh background spawns, etc.) and the venv-
#     activation side-effect broke those background processes. Andrew caught
#     the "background shell failed" message and asked for the fix.

_divineos_venv_activate() {
    local marker_dir="$1"
    local venv_root="$marker_dir/.direnv"
    local venv
    venv=$(ls -d "$venv_root"/python-* 2>/dev/null | head -1)
    if [ -z "$venv" ]; then
        local ver
        ver=$(python -c "import platform; print(platform.python_version())" 2>/dev/null)
        [ -z "$ver" ] && { echo "divineos-hook: no python found on PATH" >&2; return 1; }
        venv="$venv_root/python-$ver"
        echo "divineos-hook: creating sealed venv at $venv (one-time, ~30s)" >&2
        mkdir -p "$venv_root"
        python -m venv "$venv" || return 1
    fi
    local bindir
    if [ -d "$venv/Scripts" ]; then bindir="$venv/Scripts"; else bindir="$venv/bin"; fi
    export _DIVINEOS_VENV_OLD_PATH="$PATH"
    export _DIVINEOS_VENV_MARKER="$marker_dir"
    export VIRTUAL_ENV="$venv"
    export PATH="$bindir:$PATH"
}
_divineos_venv_deactivate() {
    [ -z "$_DIVINEOS_VENV_MARKER" ] && return 0
    export PATH="$_DIVINEOS_VENV_OLD_PATH"
    unset _DIVINEOS_VENV_OLD_PATH _DIVINEOS_VENV_MARKER VIRTUAL_ENV
}
_divineos_venv_check() {
    # Interactive-only guard (v2, Aria 2026-07-18): skip in non-interactive
    # shells (Monitor subshells, script-sourced contexts, etc.). Otherwise
    # the hook fires in every non-interactive shell that sources .bashrc,
    # prints venv-creation noise to stderr, and can break background
    # processes that spawned a shell wrapper.
    case "$-" in *i*) ;; *) return 0 ;; esac
    local dir="$PWD"
    while [ "$dir" != "/" ] && [ -n "$dir" ]; do
        if [ -f "$dir/.envrc" ]; then
            [ "$_DIVINEOS_VENV_MARKER" = "$dir" ] && return 0
            _divineos_venv_deactivate
            _divineos_venv_activate "$dir"
            return 0
        fi
        dir=$(dirname "$dir")
    done
    _divineos_venv_deactivate
}
if [[ "$PROMPT_COMMAND" != *"_divineos_venv_check"* ]]; then
    PROMPT_COMMAND="_divineos_venv_check${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi
