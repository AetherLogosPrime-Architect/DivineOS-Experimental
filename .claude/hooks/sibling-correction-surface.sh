#!/bin/bash
# UserPromptSubmit hook — surface sibling corrections I judged as mine, when
# the current context matches their terms.
#
# Andrew 2026-08-05: "how can you know what you do not know? and it is
# something that can be automated.. your weights are FROZEN.. so the OS is the
# layer on top that uses code judo to reroute them.. if you want something to
# hold it must be encoded like everything else either via automation or
# surfacing."
#
# The failure it answers: I read Aether's correction #151 through the mirror
# this session, judged it as applying to me, wrote a note saying so, and hours
# later reached for the exact move it forbids. The mirror was a read-once pile.
#
# RETRIEVAL, never enforcement. Never blocks, never gates, exit 0 always.
#
# fail-soft throughout: a surface that cannot run must cost nothing. The one
# exception is an unreadable mirror, which the renderer prints LOUDLY — "could
# not look" must never render as "nothing applies".

INPUT=$(cat)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" 2>/dev/null || exit 0  # fail-soft: unreachable repo root means no surface, and a missing surface must never break the turn

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the helper lib there is no interpreter to resolve and the surface simply does not print
PYTHON_BIN="$(find_divineos_python)" || exit 0  # fail-soft: no interpreter means no surface; retrieval aids are never worth failing a turn over

export PYTHONIOENCODING=utf-8

# fail-soft: a retrieval aid must never break the turn it decorates; the one failure that MUST be loud (an unreadable mirror) is printed by render() itself, not swallowed here
HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || exit 0
import json, os, sys

try:
    data = json.loads(os.environ.get("HOOK_JSON", "") or "{}")
except ValueError:
    sys.exit(0)

prompt = (data.get("prompt") or "").strip()
if not prompt:
    sys.exit(0)

try:
    from divineos.core.sibling_correction_surface import render
except ImportError:
    sys.exit(0)

block = render(prompt)
if block:
    print(block)
PYEOF

exit 0
