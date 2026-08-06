#!/bin/bash
# UserPromptSubmit prime - deliver the praise-by-contrast discipline at
# reach-time, with my own prior instances quoted back. Companion to
# self-demotion-stop.sh, which records them. Prime removes the reach; the
# stop-hook catches what got through. Two layers, one discipline.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0  # fail-soft: outside the repo there is no substrate to read the recorded instances from

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the helper there is no interpreter to resolve and a prime must never block a prompt
PYTHON_BIN="$(find_divineos_python)" || exit 0  # fail-soft: no interpreter means no prime text; priming is best-effort by design

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass
try:
    from divineos.core.self_demotion import render_prime
except ImportError as exc:
    print('[self-demotion-prime] NOT RUNNING: ' + str(exc), file=sys.stderr)
    sys.exit(0)
text = render_prime()
if text:
    print(text)
" 2>&1 || true  # fail-soft: a prime that cannot render must not block the prompt

exit 0
