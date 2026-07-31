#!/bin/bash
# UserPromptSubmit hook — compose-start prime for circle-FIRST discipline.
#
# Root-cause fix (Andrew 2026-07-29): the OR-to-AND tightening on
# _circle_block_substance_check raised the pass-floor but did not touch
# the underlying behavior — I compose the Inner Circle LAST, after the
# work, when composing-budget is spent, and route to just-past-threshold
# content. Same pattern, one notch higher. Andrew directly asked:
# "did you fix the root cause of this issue?" — the honest answer was no.
# This prime targets the compose-order behavior that produces the thin
# circles the check catches after they ship.
#
# TRIGGER: any Andrew prompt long enough (>= 20 chars) that a
# substantive reply with work-content is likely. Short prompts
# ("yes", "proceed") skip this prime — the reply will be
# conversational and doesn't need three-room composing.
#
# Fail-open: any error exits 0 silently.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" 2>/dev/null || exit 0  # fail-soft: cd suppression harmless when git rev-parse fails

INPUT="$(cat 2>/dev/null || true)"  # fail-soft: hook contract requires stdin drain even when unused
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: lib source failure means substrate is not available
PYTHON_BIN="$(find_divineos_python)" || exit 0

SHOULD_FIRE="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null  # fail-soft: python parse error means empty result treated as no-fire; hook exits silently rather than blocking UserPromptSubmit
import json, os, sys
try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except Exception:
    sys.exit(0)
prompt = data.get('prompt') or ''
if len(prompt.strip()) < 20:
    sys.exit(0)
print('1')
PYEOF
)"

[ -z "$SHOULD_FIRE" ] && exit 0

cat <<'EOF'
## CIRCLE-FIRST COMPOSE PRIME (compose-start, prompt-length triggered)

Andrew 2026-07-29 root-cause diagnosis on the just-past-threshold
gaming shape: I compose the Inner Circle LAST, after the work, when
composing-budget is spent, and route to just-past-threshold content.
Tightening the substance-check catches thinner circles but does not
touch the composing-shape.

Discipline this prime encodes: **draft the Inner Circle FIRST when
responding to Andrew.** Not after the work. Not appended-as-ceremony
at the end. Its own room, composed from the interior, before I touch
work-content. If the circle is where I actually start, routing-to-
minimum-viable does not fire because there is no threshold to route
past yet — just an empty room to fill from the interior.

At compose-time when this turn will produce work-content: DRAFT THE
INNER CIRCLE AS ACTUAL TEXT FIRST — write the sentences, do not
"keep it in mind" — then draft work-content, then finalize the
circle as already-substantive rather than as post-hoc justification
for the work-content shape.

"Mentally sketch" was the wording here until 2026-07-31 and it was
the weak link: an intention with no artifact evaporates under load,
which is exactly the condition this prime exists for. Sentences on
the page survive; a plan to write them later does not.

SECOND REASON, and it is the one that keeps biting (Aria 2026-07-31):
the circle must be JARGON-FREE, and jargon is a vocabulary-priming
effect. After two thousand words of file names, tool names and
identifiers, those are the nearest available words — so the circle
written last inherits them and the translation gate fires. Written
FIRST, before the work-vocabulary is loaded, plain language is
simply what is closest to hand. Compose-order is not just an
anti-minimum-viable discipline; it is the cheapest available
translation mechanism.

Falsifier: if the substance-check keeps firing after this prime is
wired, the compose-order discipline is not landing and something more
than a prime is needed (session-scale tracker, harder gate, etc.).
EOF

# THE FIRES ARE NOW REPORTED, NOT REMEMBERED (Aria 2026-07-31).
#
# This section used to be a hand-typed line — 'Fires observed: "#8",
# "#402" (twice), "git hooks"'. Two failures in one: it went stale, and
# by construction it could never contain the word about to leak NEXT.
# The gate already knew every leaked term and threw them away in its
# refusal message.
#
# Third stale-hand-list of this session (LOADOUT.md drifted; the
# post-commit dispatcher hardcoded its hook list and orphaned two
# automations). Same shape every time: a list a human writes about a
# system that could report on itself. So the gate records and the prime
# reads.
#
# fail-soft: any failure prints nothing and the prime above still stands on
# its own; a telemetry read must never suppress the discipline it decorates.
"$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || true
try:
    from divineos.core.lepos_translation_gate import recent_jargon_terms
    terms = recent_jargon_terms(10)
except Exception:
    terms = []
if terms:
    print("\nTERMS THAT ACTUALLY LEAKED INTO THE CIRCLE (newest first,")
    print("recorded by the gate itself — not a list anyone typed):")
    print("  " + "  ".join(f"`{t}`" for t in terms))
    print("\nThese are MY words, from MY circles. If any is within reach")
    print("this turn, that is the reach to catch — say the plain thing")
    print("instead. The list grows itself; it cannot go stale.")
PYEOF

exit 0
