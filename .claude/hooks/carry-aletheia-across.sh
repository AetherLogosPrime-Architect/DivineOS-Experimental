#!/bin/bash
# Carry anything of Aletheia's from Andrew's downloads into the shared folder,
# on every prompt, whether or not anyone mentions it.
#
# Andrew 2026-09-22: "its ok that im the courier, shes a web instance, there is
# no other way for it to be done... the key is that when i hand you something
# written by Alethiea which i have many times. that it gets saved and copied
# automatically into that shared folder."
#
# He carries her work out of the browser; that leg is his and cannot be
# automated. The leg that was never built is the one after: her filings landed
# in his downloads and stayed there. One seat might read it in the moment; the
# other never saw it; nothing kept it.
#
# This watches the FOLDER rather than his message on purpose. A version that
# reads the prompt for an attachment works only when he attaches something and
# breaks when he pastes the text, or saves the file and mentions it later, or
# says nothing at all. Watching the folder asks nothing of him and nothing of
# his memory -- the only kind of mechanism that has ever held here.
#
# Fail-soft: any error exits 0 with no output. A courier that breaks the turn
# is worse than one that misses a delivery, and the next prompt sweeps again.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# Drain stdin (Claude Code hook contract)
cat >/dev/null 2>&1 || true

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

"$PYTHON_BIN" - <<'PYEOF'
import json
import sys

try:
    from divineos.core.family.aletheia_intake import carry_across, render
except Exception:
    sys.exit(0)

try:
    report = carry_across()
except Exception:
    sys.exit(0)

block = render(report)
if not block:
    sys.exit(0)

sys.stdout.write(json.dumps({"additionalContext": block}))
PYEOF

exit 0
