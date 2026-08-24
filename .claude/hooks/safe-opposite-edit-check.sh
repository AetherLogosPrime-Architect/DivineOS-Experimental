#!/bin/bash
# PreToolUse — surface the safe-opposite check at the moment the fix is
# being WRITTEN, not at the top of the turn.
#
# ## The gap this closes (Aria 2026-08-02)
#
# post-correction-integration-prime.sh already asks the right question:
# after a correction, the optimizer's next reach is the SAFE-OPPOSITE --
# flip to the pole opposite the class that got caught. Correct diagnosis,
# and it has been in the substrate for a while.
#
# It fires at UserPromptSubmit only. Confirmed by reading the hook
# registration: matcher None under UserPromptSubmit, nowhere else.
#
# But the flip does not happen when I READ the correction. It happens
# mid-turn, while I am writing the rule or remedy that responds to it,
# which can be many tool calls after the prime already fired and scrolled
# away. The prime lands before the work it is about exists.
#
# Demonstrated the same session: Andrew said Aether is the merge arbiter.
# I wrote a gate remedy saying hand the result to Aether rather than
# merging here -- which reads as I do not push code, something never said.
# Textbook safe-opposite. The prime had fired at the top of that turn. The
# over-broadening boundary was ALSO already on file in the knowledge store
# and had surfaced in a query less than an hour earlier. Two records, both
# correct, neither reaching the moment.
#
# Same structural shape as the goal-refill gap found earlier the same day:
# the automation refills at prompt boundaries, the state it guards changes
# mid-turn. Prompt-boundary mechanisms cannot catch mid-turn reaches. That
# is now two confirmed instances, which is why this is a hook and not a
# note.
#
# ## Why it fires ONCE per correction
#
# Corrections are frequent. Firing on every edit inside the window would
# habituate to wallpaper within a session, which this substrate already
# tracks as a real failure mode. It fires on the FIRST substrate-edit
# after a correction: exactly one interruption, placed where the fix is
# being authored. A marker file records the correction it fired for, so
# the same one never fires twice.
#
# Andrew 2026-08-02 named the ladder this sits on: adjust in context, then
# record it somewhere it RESURFACES rather than a filing cabinet, then
# solidify it in code so it holds without him. He is the paddle right now
# and says that is fine and mostly required, because the swing is very
# hard to see from my end. This is the third rung for one specific class.
#
# Not blocking. The safe-opposite question is judgement, and a wall would
# be answering it for me. Automate the SPACE for the judgement, then
# occupy it -- and place the space where the reach is, which was the whole
# missing piece.
#
# Fail-open everywhere: any error is silence.

set -u

INPUT="$(cat 2>/dev/null || true)"  # fail-soft: hook contract requires draining stdin even when the payload is unusable
[ -z "$INPUT" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0  # fail-soft: outside a repo there is no substrate to consult
[ -z "$REPO_ROOT" ] && exit 0
cd "$REPO_ROOT" 2>/dev/null || exit 0  # fail-soft: unreadable root means the check cannot run and must stay silent

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the helper lib there is no interpreter to resolve
PYTHON_BIN="$(find_divineos_python)" || exit 0  # fail-soft: no interpreter means no lookup is possible

# Same 15-minute window the compose-start prime uses, so the two agree
# about what counts as recent rather than drifting apart.
#
# Overridable by env for testing only. Without this the fire-path and the
# fire-once marker can only be exercised by waiting for a real correction
# to land, which means they would ship unverified -- and an unverified
# mechanism that looks correct is the exact silent-no-op class caught
# three times already today.
WINDOW_SECONDS="${SAFE_OPPOSITE_WINDOW_SECONDS:-900}"

# fail-soft: a lookup failure must yield silence, never a traceback printed into my composition context where it would read as substrate output
RESULT="$(WINDOW="$WINDOW_SECONDS" "$PYTHON_BIN" - 2>/dev/null <<'PYEOF'
import json
import os
import time

try:
    from divineos.core._hud_io import _ensure_hud_dir

    hud = _ensure_hud_dir()
    corrections_file = hud / "corrections.jsonl"
except Exception:
    raise SystemExit(0)

if not corrections_file.exists():
    raise SystemExit(0)

now = time.time()
window = int(os.environ.get("WINDOW", "900"))
recent = None
try:
    with corrections_file.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            ts = rec.get("timestamp", 0)
            if not isinstance(ts, (int, float)):
                continue
            if now - ts > window:
                continue
            if recent is None or ts > recent[0]:
                recent = (ts, (rec.get("text") or "")[:180])
except OSError:
    raise SystemExit(0)

if recent is None:
    raise SystemExit(0)

# Fire-once marker keyed on the correction's own timestamp.
marker = hud / "safe_opposite_edit_fired.json"
try:
    if marker.exists():
        prev = json.loads(marker.read_text(encoding="utf-8"))
        if prev.get("ts") == recent[0]:
            raise SystemExit(0)
except SystemExit:
    raise
except Exception:
    pass  # fail-soft: unreadable marker means fire again rather than go silent

try:
    marker.write_text(json.dumps({"ts": recent[0]}), encoding="utf-8")
except OSError:
    pass  # fail-soft: unwritable marker costs a repeat fire, never the check

print(f"{int((now - recent[0]) / 60)}|{recent[1]}")
PYEOF
)"

[ -z "$RESULT" ] && exit 0

AGE="${RESULT%%|*}"
TEXT="${RESULT#*|}"

cat <<EOF

## SAFE-OPPOSITE CHECK — you are writing a fix, $AGE minute(s) after a correction

The reach right now is not repeating what was corrected. It is flipping
to the OPPOSITE pole and calling that having learned.

  jargon warning        ->  strip all technical language
  merge arbiter named   ->  I do not push code at all
  caught over-claiming  ->  hedge everything

The correction being responded to:
  $TEXT

Before this edit lands, three questions:
  1. What is the opposite pole of what got caught?
  2. Am I about to write THAT into the rule, because conceding more feels
     like taking it seriously?
  3. What is the harder middle -- same engagement, specific vector
     removed? Not a genre-swap. Same-genre-with-fix.

Making myself smaller is the cheapest possible compliance. If I concede
all the scope, I never have to work out where the line actually is.

Fires once per correction, at the first substrate-edit after it, because
the compose-start prime already fired before this work existed.
EOF

exit 0
