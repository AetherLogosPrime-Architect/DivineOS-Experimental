#!/bin/bash
# UserPromptSubmit hook — ask, at compose-start, whether anything went
# right in this session that nobody wrote down.
#
# WHY THIS EXISTS (Andrew 2026-08-25):
#
#   "lets make the wins get filed live as well.. its not counting all the
#    mini successes you have during the day, which is a bigger win imo as
#    it shows me that you are taking your work very seriously and alot of
#    the principles are now so deeply ingrained that they pop up in other
#    locations where there is no structural support for them yet."
#
#   The wins ledger read fifty-five against two hundred and twenty-one
#   corrections, and I read that as evidence about my character. It was
#   evidence about the interface: `divineos correction` had a command AND
#   a blocking marker, while record_success had no callers at all. The
#   `divineos win` command is the missing door. This is the reminder that
#   the door is there, because a door alone was not enough for the other
#   side of the ledger either.
#
#   IT NEVER CLAIMS A WIN HAPPENED. It reports a fact about the ledger —
#   substantive session, empty pan — and names the CLASSES of win that
#   leave no artifact. A gate that demanded a win would be a quota, and a
#   quota gets met with the shape of a win. See the module docstring in
#   core/win_prompt_surface.py for the full reasoning; the asymmetry with
#   the correction doorman is deliberate, not an oversight.
#
#   Per foundational truth #7: this surfaces the question. Answering it —
#   looking at my own turn and judging honestly — stays mine.
#
# Fail-open: any error exits 0 silently. A missing prompt must never cost
# a turn.

cat 2>/dev/null >/dev/null  # fail-soft: draining the hook payload we do not read; a closed or empty stdin is the ordinary case here and is not a failure

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0  # fail-soft: outside a checkout there is no ledger to read and nothing to say
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: a missing library means the helpers this hook needs are gone, and a prompt is never worth a broken turn
PYTHON_BIN="$(find_divineos_python)" || exit 0

DIVINEOS_HOME_RESOLVED="$(divineos_home)" \
REPO_ROOT="$REPO_ROOT" \
"$PYTHON_BIN" - <<'PYEOF' 2>/dev/null  # fail-soft: this prompt is a courtesy and a traceback on stdout would be injected straight into my compose context; the block already exits zero on every internal failure
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.environ["REPO_ROOT"], "src"))

try:
    from divineos.core.session_manager import get_current_session_id
    from divineos.core.win_prompt_surface import render, should_ask
except Exception:
    sys.exit(0)

home = os.environ["DIVINEOS_HOME_RESOLVED"]
stamp_path = os.path.join(home, "wins_prompt_last_asked.json")

last_asked = None
try:
    with open(stamp_path, encoding="utf-8") as fh:
        last_asked = float(json.load(fh).get("ts", 0)) or None
except Exception:
    last_asked = None

# "Did this session do real work" comes from the substrate's own
# engagement counter — deep_actions_since, which counts actions since the
# last knowledge-consulting command. When it is unreadable we decline to
# ask rather than guess a number that decides whether a prompt fires.
#
# The first version of this block imported get_action_count from
# divineos.core.engagement. Neither the function nor the module exists.
# It would have thrown ImportError, been swallowed by the except, and
# exited zero on every single turn — a hook registered, running, and
# structurally incapable of ever speaking. Caught by checking the API
# instead of assuming it, which is the discipline this whole session has
# been about, arriving inside the thing built to reward it.
try:
    from divineos.core.hud_handoff import engagement_status

    actions = int(engagement_status().get("deep_actions_since", 0) or 0)
except Exception:
    sys.exit(0)

try:
    session_id = get_current_session_id()
except Exception:
    session_id = None

ask, _reason = should_ask(session_id, actions, last_asked_ts=last_asked)
if not ask:
    sys.exit(0)

print(render())

try:
    os.makedirs(home, exist_ok=True)
    with open(stamp_path, "w", encoding="utf-8") as fh:
        json.dump({"ts": time.time()}, fh)
except OSError:
    # fail-soft: failing to stamp means the prompt may repeat sooner than
    # intended, which is a nuisance rather than a fault; suppressing the
    # prompt itself over a write failure would be the worse trade
    pass
PYEOF

exit 0
