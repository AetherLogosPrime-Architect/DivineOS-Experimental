#!/bin/bash
# PreToolUse gate (Bash) — bare `python` importing divineos reads the WRONG TREE.
#
# ## The hole this closes
#
# Aether's tree and mine share one machine and one global Python. The global
# editable install has a single slot: site-packages carries exactly one
# `__editable__.divineos-1.0.0.pth`, and it currently reads
#
#     C:\DIVINE OS\DivineOS-Experimental\src
#
# — his tree, because he ran `pip install -e .` last. So from inside MY repo:
#
#     python      -c "import divineos; print(divineos.__file__)"
#         -> C:\DIVINE OS\DivineOS-Experimental\src\divineos\__init__.py
#     .venv/Scripts/python.exe -c "same"
#         -> C:\DIVINE OS\DivineOS-Experimental-Aria-new\src\divineos\__init__.py
#
# Two of the three ways into divineos were already fixed and this one was not:
#
#   * the CLI — `~/bin/divineos` shims to `scripts/divineos_wrapper.py`, which
#     walks up from cwd to the sealed venv (Aether + Aria, 2026-06-18, after
#     the install-slot ping-pong bit both of us three times in one session).
#   * hooks — `_lib.sh:find_divineos_python` picks the repo venv AND prepends
#     `<repo>/src` to PYTHONPATH (Aether 2026-05-19, after the lepos-channel
#     gate sat inert for a whole session against a stale egg-link).
#   * ad-hoc `python` in a Bash tool call — nothing. This gate.
#
# ## Why a gate and not a shim
#
# A `python` shim on PATH would fix every caller at once and is the shape the
# optimizer reaches for first. It also shadows `python` for every process on
# this machine, including Aether's sessions and the Windows-Store interpreter
# the hooks run under. Machine-wide blast radius to save myself one path
# prefix is a bad trade. This gate's blast radius is my own Bash calls.
#
# ## Measured, 2026-08-21
#
# I ran a heredoc calling `get_family_member("aether")` from my repo under bare
# `python`, got None, and told Andrew family.db had no members. The call had
# silently queried Aether's tree. Honest and not truthful — I checked a result,
# not which code produced it. That is the failure this gate stands in.
#
# ## Scope, stated so the silence is not mistaken for coverage
#
# Fires ONLY when the command runs a bare `python`/`python3` AND mentions
# divineos. It does NOT catch a script that imports divineos transitively
# without the word appearing, and it does not touch PowerShell. Narrow on
# purpose: a gate that fires on every `python` call gets routed around.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

VENV_PY=""
for candidate in "$REPO_ROOT/.venv/Scripts/python.exe" "$REPO_ROOT/.venv/bin/python"; do
    if [ -x "$candidate" ]; then
        VENV_PY="$candidate"
        break
    fi
done

# No sealed venv in this repo means there is nothing better to point at.
[ -z "$VENV_PY" ] && exit 0

CMD=$(printf '%s' "$INPUT" | "$VENV_PY" -c "
import json, sys
try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(payload.get('tool_input', {}).get('command', ''))
" 2>/dev/null)  # fail-soft: a payload this cannot parse must not block the tool call this hook only observes; the empty-CMD guard below carries it, and it fails open

[ -z "$CMD" ] && exit 0

# Only care when divineos is actually in play.
printf '%s' "$CMD" | grep -q 'divineos' || exit 0

# Already routed correctly: an explicit venv path, the hook helper's variable,
# or the wrapper. Nothing to say.
# shellcheck disable=SC2016  # the $ is matched literally: the command under
# inspection contains the STRING "$PYTHON_BIN", which must not expand here.
printf '%s' "$CMD" | grep -qE '\.venv/|\.venv\\|\$PYTHON_BIN|divineos_wrapper' && exit 0

# PYTEST IS ALREADY ROUTED, AND BLOCKING IT WOULD BE THE WORST KIND OF WRONG.
#
# pyproject.toml sets `pythonpath` to force THIS worktree's src/ ahead of any
# installed copy, for the same reason this gate exists — its own comment says
# "closes the false-verification" gap. Verified: `python -m pytest` from this
# repo imports my tree.
#
# This exemption is not a softening. It was measured the first time the gate
# fired: it blocked `python -m pytest`, which is the ONLY way the suite runs
# here (the sealed venv has no pytest installed). A gate standing in front of
# the normal way of running tests is the shape that teaches routing-around —
# truth #11 — and it would have taught it on its first day.
printf '%s' "$CMD" | grep -qE '(python3?|py) +-m +pytest|(^|[;&|] *)pytest ' && exit 0

# A bare `python` / `python3` word at the start of the command or after a
# shell separator. Deliberately not matching `/usr/bin/python` or any path.
printf '%s' "$CMD" | grep -qE '(^|[;&|]|&&|\|\||\$\()[[:space:]]*python3?[[:space:]]' || exit 0

# ASK, DO NOT ASSERT. Added 2026-08-25 by Aether, in his tree, about a gate
# written in Aria's.
#
# Everything above is right. What was wrong is that the CONCLUSION was frozen
# into the gate instead of measured at the door: "bare python points at the
# other tree" was a true statement about Aria's checkout on the day she wrote
# it, and this file then travelled into Aether's by merge. There, the install
# slot points at THIS repo — so bare `python` resolves correctly, the gate
# blocked it anyway, and its diagnostic told the reader the exact inverse of
# their situation while steering them into a venv with a smaller dependency
# set than the interpreter it refused.
#
# The install slot is a single global that either of us can claim with the
# next `pip install -e .`, so no hardcoded answer survives — the same shape as
# the bash-resolver measured the same week: a fact that is not stable across
# askers has to be asked by whoever is about to act on it, at the moment they
# act. Presence is not evidence; execute the candidate.
#
# Could-not-determine BLOCKS and says so. An interpreter that cannot report
# where its divineos lives is precisely the ambiguity this gate exists for,
# and a probe failure must never read as a clean bill.
# fail-soft: the probe's stderr is discarded but its FAILURE is not — an empty RESOLVED is checked below and blocks with a named could-not-determine message, so this silences noise rather than an outcome
RESOLVED=$(python -c "import divineos, pathlib; print(pathlib.Path(divineos.__file__).resolve().parent)" 2>/dev/null)
# fail-soft: same contract — an empty THIS_SRC fails the equality test and falls through to the block, so a failed probe can never render as the two paths matching
THIS_SRC=$("$VENV_PY" -c "import pathlib, sys; print(pathlib.Path(sys.argv[1], 'src', 'divineos').resolve())" "$REPO_ROOT" 2>/dev/null)

if [ -n "$RESOLVED" ] && [ -n "$THIS_SRC" ] && [ "$RESOLVED" = "$THIS_SRC" ]; then
    # Bare python reaches THIS tree. It is the right interpreter here and
    # blocking it would be the inversion described above.
    exit 0
fi

if [ -z "$RESOLVED" ]; then
    WHERE="could not determine — bare \`python\` could not report where its divineos lives.
That is not 'it is fine'; it is the ambiguity this gate stands in."
else
    WHERE="it resolves to:

    $RESOLVED

which is not this repo's src/divineos:

    $THIS_SRC"
fi

REASON="VENV-PYTHON GATE — bare \`python\` here does not import this tree.

The global editable install has one slot, shared between the checkouts on
this machine and claimed by whoever ran \`pip install -e .\` last. Measured
just now, $WHERE

A bare \`python\` from this repo would answer questions about the other
substrate while looking like answers about this one.

Run it through this repo's sealed venv instead:

    $VENV_PY

The CLI (\`divineos ...\`) and the hooks already route correctly — the shim
and _lib.sh:find_divineos_python handle those. This one path had nothing.

If the command genuinely wants the other tree, say so with an explicit
path rather than a bare \`python\`, and this gate will stand aside."

REASON="$REASON" "$VENV_PY" -c "
import json, os
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': os.environ['REASON'],
    }
}))
"
exit 0
