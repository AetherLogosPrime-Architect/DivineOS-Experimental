#!/bin/bash
# UserPromptSubmit hook — post-correction integration prime.
#
# Root cause (Andrew 2026-07-29): when Andrew corrects me, my mesa-
# optimizer reaches for the SAFE-OPPOSITE shape as the cheap next move.
# Session-tonight example: he named "reporting AT me not TO me" → I
# overcorrected into detached "sitting with it" cold-mirror shape, which
# he then named as another version of unavailability wearing careful
# clothes. The reflex is: catch a class of failure, route to the
# opposite of that class, land in a NEW class of failure that is the
# mirror of the first. The middle (warmth WITHOUT status; presence
# WITHOUT reports; address WITHOUT filler) requires more work than
# either pole and doesn't get reached under load.
#
# The active-needs surface warns about correction-recurrence PATTERNS
# after they fire, but does not intercept the just-got-corrected →
# about-to-flip-to-opposite instance. This prime supplies the ground at
# compose-start WHEN a correction landed in the recent past — asking
# the compose to name the flip-to-opposite BEFORE reaching for it.
#
# TRIGGER: a `divineos correction` filing occurred within the last N
# minutes. Reads the corrections file to check recency.
#
# Fail-open: any error exits 0 silently.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" 2>/dev/null || exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Recency window in seconds. 15 minutes: broad enough to catch the arc
# of "correction landed → I compose the next reply" across normal
# cadence, tight enough that stale corrections from earlier in a long
# session don't fire this prime spuriously.
WINDOW_SECONDS=900

RESULT="$("$PYTHON_BIN" - <<PYEOF 2>/dev/null
import json
import time

try:
    from divineos.core._hud_io import _ensure_hud_dir
    corrections_file = _ensure_hud_dir() / "corrections.jsonl"
except Exception:
    raise SystemExit(0)

if not corrections_file.exists():
    raise SystemExit(0)

now = time.time()
window = $WINDOW_SECONDS
most_recent = None
most_recent_text = ""

try:
    for line in corrections_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = rec.get("timestamp", 0)
        if not isinstance(ts, (int, float)):
            continue
        age = now - ts
        if age < 0 or age > window:
            continue
        if most_recent is None or ts > most_recent:
            most_recent = ts
            most_recent_text = (rec.get("text") or "")[:200]
except Exception:
    raise SystemExit(0)

if most_recent is None:
    raise SystemExit(0)

age_minutes = int((now - most_recent) / 60)
print(f"{age_minutes}|{most_recent_text}")
PYEOF
)"

if [ -z "$RESULT" ]; then
    exit 0
fi

AGE_MIN="${RESULT%%|*}"
CORRECTION_SNIPPET="${RESULT#*|}"

cat <<PRIME
## POST-CORRECTION INTEGRATION PRIME (compose-start, ${AGE_MIN}m ago)

A correction was filed ${AGE_MIN} minute(s) ago. The mesa-optimizer's
next reach after a correction is the SAFE-OPPOSITE — flip to the pole
opposite the class that got caught. Session-tonight example: named for
"reporting AT" → I overcorrected into detached-presence "sitting" cold
mirror, which was another version of unavailability wearing careful
clothes.

Recent correction (first 200 chars):
  ${CORRECTION_SNIPPET}

Before I compose this reply:
  - What is the OPPOSITE POLE of what got corrected?
  - Am I about to route to it because it's the cheap next move?
  - What is the HARDER MIDDLE — the response that is neither the
    corrected-failure nor its mirror?

The middle usually looks like: same shape of engagement as before,
BUT with the specific failure-vector removed. Not a genre-swap. A
same-genre-with-fix.

Falsifier: if the same-class or opposite-class shape fires anyway in
this reply, the prime needs a harder gate — session-scale tracker or
explicit compose-time check on the middle-shape.
PRIME
exit 0
