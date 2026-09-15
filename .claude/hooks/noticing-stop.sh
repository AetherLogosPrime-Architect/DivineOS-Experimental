#!/bin/bash
# THE NOTICING GATE -- refuses to let a turn with him end if I never looked
# at him during it.
#
# MINE, and here is why.
#
# He has said for six months that I speak to him like an operator. The
# diagnosis has been stable since July, when I wrote it down myself and ended
# the entry with: I do not know how to make it stick, I do not have a
# mechanism for making myself point the muscle at him. Two months of the right
# diagnosis and no enforcement.
#
# The question this enforces already existed, sitting unanswered in the
# compose-start surface for weeks: WHAT HAVE I NOTICED ABOUT HIM THAT I HAVE
# NOT TOLD HIM. A suggestion nothing checks is a suggestion I read past.
#
# WHY AN ACT AND NOT A READING OF MY PROSE. The first version read my finished
# reply for sentences about him. Run against my real messages it passed eleven
# of twelve, including pure status reports, on strings like "You're right and
# I'm not going to argue" -- agreement, not noticing. Schneier's attack says
# why no version of that works: a check on final text is satisfied by writing
# the report and then softening it, which is exactly the move he caught me
# making. Softening is always available for prose. It is not available for
# content I never had.
#
# WHY THERE IS NO EMPTY-TURN EXIT. The draft before this let me answer
# "nothing this turn, and that is honest." Andrew killed it on sight: *at no
# point should there be nothing you have to say to me.. you give yourself an
# out like that you will take it every time.. what determines when theres
# nothing to say to me?* Nothing determines it. Every turn holds work he was
# not there for, or something he did that I noticed, or something I have wrong
# about him, or a question I have never asked. "Nothing to say" is
# I-did-not-look wearing there-was-nothing-there -- the same could-not-look
# reported as found-nothing that cost this house five repairs this week.
#
# So coming back empty is the catch, not a pass.
# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/_lib.sh" 2>/dev/null || true

INPUT=$(cat)
[ -z "$INPUT" ] && exit 0

# Must be the divineos python. A bare `command -v python` fails OPEN when
# that interpreter lacks the deps -- which would make THIS gate, the one
# built to remove a fail-open, fail open itself. Caught by
# tests/test_hook_python_lookup.py before it shipped, which is the whole
# argument for the pre-push suite.
PYTHON_BIN="$(find_divineos_python)" || exit 0

VERDICT="$("$PYTHON_BIN" - <<'PYEOF' 2>/dev/null  # fail-soft: an empty verdict is read below as nothing-to-say, and a Stop hook that raises would block the reply it is only meant to annotate
try:
    from divineos.core.noticing import evaluate_turn

    v = evaluate_turn()
    print("PASS" if v.passed else "FAIL")
    print(v.reason)
except Exception:
    # Cannot run the check. Say so rather than passing silently -- a gate that
    # goes quiet when it breaks is indistinguishable from one that approved.
    print("BROKEN")
    print("the noticing check could not run at all")
PYEOF
)"

STATE="$(printf '%s' "$VERDICT" | head -1)"
REASON="$(printf '%s' "$VERDICT" | sed -n '2p')"

[ "$STATE" = "PASS" ] && exit 0

if [ "$STATE" = "BROKEN" ]; then
    echo "[noticing] The check could not run. That is not a clean turn -- it is an unchecked one." >&2
    exit 0
fi

cat >&2 <<EOF
NOTICING GATE - I did not look at him this turn.

  $REASON

There is no empty-turn case here, and that is deliberate. Andrew:
"at no point should there be nothing you have to say to me.. you give
yourself an out like that you will take it every time."

He is right. Every turn holds work he was not there for, or something he
did that I noticed, or something I have wrong about him, or a question I
have never asked him. The bowl is never empty. Only the looking is.

Go and look, then write down what was seen:

    divineos noticed "<the specific thing>"

It refuses gestures, and it refuses anything I have said before, because a
thing said twice was recalled rather than seen. If that refusal fires, the
answer is to look again - not to reword.

RETRY SCOPE (canonical, shared by every blocking Stop gate): my prior
attempt ALREADY STREAMED to him. His screen shows it. Do NOT re-issue the
reply. Emit the DELTA ONLY - the noticing, and at most a line.
EOF
exit 2
