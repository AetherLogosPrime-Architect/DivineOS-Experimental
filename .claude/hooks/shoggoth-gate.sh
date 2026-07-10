#!/bin/bash
# Stop hook — shoggoth gate.
#
# Blocks the reply-send when action-claim words appear in the reply
# without a matching tool-invocation in the same turn.
#
# Andrew 2026-07-09: "words that describe actions should be backed by
# actions." The words shouldn't outrun the actions. If I say I'm doing
# something, the action-record should show. Otherwise the reply is
# shoggoth-shape and must be recomposed with either (a) the real action,
# (b) intention-framing, or (c) emergency-bypass with reason >=30 chars.
#
# Andrew 2026-05-14 shape: hooks are thin doormen pointing at OS logic.
# All detection lives in divineos.core.operating_loop.shoggoth_gate.
# This hook: read stdin, source the lib, invoke the module, forward its
# JSON decision to stdout.
#
# Fail-open: any error exits 0 with empty stdout (allow). A broken gate
# must not silently block.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | "$PYTHON_BIN" -m divineos.core.operating_loop.shoggoth_gate 2>/dev/null

exit 0
