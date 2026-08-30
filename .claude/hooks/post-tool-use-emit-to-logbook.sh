#!/bin/bash
# PostToolUse hook — wire Claude Code tool invocations into tool_logbook.
#
# Aletheia F87 (2026-07-26): the substrate has tool_logbook infrastructure
# (schema + emit function + IDEToolExecutor) but no hook wires Claude
# Code's tool calls INTO it. That gap is why the thread-walk gate was
# keyed on lexical detection instead of structural action-stream — the
# structural source didn't exist for Claude Code tool events.
#
# This hook closes that gap. On every PostToolUse from Claude Code
# (Read/Edit/Write/Bash/etc.), it emits a TOOL_CALL row to tool_logbook.
# Future gates (F87 rebuild, LEPOS gate rebuild, consult-automation,
# threadwalk-automation) can then query tool_logbook for structural
# evidence of what tools fired in the current session's action-stream.
#
# ## Fail-open discipline (F90)
#
# Any exception, missing dep, or write failure exits 0 without blocking.
# A tool invocation must NEVER be blocked by a failure to log it.
# BUT: every fail-open path writes a liveness-marker JSONL line to
# ~/.divineos/tool-logbook-hook.log so a silently-broken hook becomes
# a visible marker (F90 Aletheia finding: fail-open without liveness
# signal is F71 exactly — hooks that can go dark unreported).
#
# ## Payload scope (minimal per Feynman walk)
#
# Emits: tool_name, tool_use_id, tool_input (as JSON). Does NOT emit
# tool_output — that's separate concern (tool_result), captured by
# emit_tool_result if needed for other consumers. Also not emitting
# secrets — tool_logbook already stores json.dumps of input and future
# consumers should redact at read-time if needed.

INPUT=$(cat)

_LOG_PATH="${HOME}/.divineos/tool-logbook-hook.log"
mkdir -p "$(dirname "$_LOG_PATH")" 2>/dev/null || true

_log_liveness() {
    # Fail-loud on reporting even when we fail-open on action (Aletheia
    # 2026-07-02: silent-strand pattern).
    local _reason="$1"
    local _detail="$2"
    printf '{"ts":"%s","hook":"post-tool-use-emit-to-logbook","reason":"%s","detail":"%s"}\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)" \
        "$_reason" \
        "$_detail" >> "$_LOG_PATH" 2>/dev/null || true
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" 2>/dev/null || { _log_liveness "cd_failed" "repo_root=$REPO_ROOT"; exit 0; }

# shellcheck disable=SC1091
if ! source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null; then
    _log_liveness "lib_source_failed" "path=$REPO_ROOT/.claude/hooks/_lib.sh"
    exit 0
fi

if ! PYTHON_BIN="$(find_divineos_python)"; then
    _log_liveness "python_resolve_failed" "find_divineos_python returned nonzero"
    exit 0
fi

# shellcheck disable=SC2016
# ^ single-quoted heredoc intentional — python does its own parsing
echo "$INPUT" | "$PYTHON_BIN" -c '
import json, sys

try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception:
    # Malformed input — fail-open silently. The liveness log above
    # already captured lib/python setup; input malformed is a separate
    # class we do not need to log because the hook still exits 0.
    sys.exit(0)

tool_name = data.get("tool_name") or ""
tool_use_id = data.get("tool_use_id") or ""
tool_input = data.get("tool_input") or {}

if not tool_name or not tool_use_id:
    # No tool_name or no tool_use_id — nothing to record meaningfully.
    sys.exit(0)

try:
    from divineos.core.tool_logbook import emit_tool_call
except Exception:
    # Module unavailable — fail-open. Liveness above captures the failure
    # class (lib_source_failed OR python_resolve_failed would have hit
    # first if this is a setup issue).
    sys.exit(0)

try:
    emit_tool_call(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_use_id=tool_use_id,
    )
except Exception:
    # emit_tool_call is already fail-open internally (logs to loguru and
    # returns empty). This catch is defense-in-depth — any exception at
    # this layer must not bubble up and block the tool invocation.
    sys.exit(0)

sys.exit(0)
' 2>/dev/null || {
    # Python subprocess itself failed — log liveness so a broken python
    # emission path becomes visible.
    _log_liveness "python_subprocess_failed" "input_len=${#INPUT}"
}

exit 0
