#!/usr/bin/env bash
# Compose-start half of the translate-first discipline.
#
# WHY THIS EXISTS. In lepos_translation_gate.py the wallclock discipline runs
# BOTH a compose-start prime and a Stop gate, and says so in its own text --
# "two layers, one discipline". Translation had only the Stop half, so it could
# tell me the reply carried thirty-three document-marks and only after they had
# already reached him. Filed as prereg-2eabc4ac8378 before building, with the
# falsifier: if the fire rate does not drop, or drops only because replies got
# SHORTER rather than more translated, the prime is wrong and comes out.
#
# WHY IT PRINTS A NUMBER RATHER THAN THE RULE. A surface whose text is identical
# every turn becomes scenery -- there is nothing to habituate to except the
# wording. A surface recomputed from state cannot, because the token is new each
# time. The wallclock prime prints the clock instead of asking me to remember to
# check it, and that is the one prime the telemetry found clearing the noise
# band. So this reads the last recorded fire and reports what the last reply
# actually cost.
#
# DELIBERATELY SHORT. The corpus problem Aria measured is that the longest primes
# fire most often, which is backwards for any encoding: frequent messages get
# short codes. The rule goes here; the history and the reasoning live in the
# module this reads from, which the surface points at rather than ships.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
[[ -f "$HOOK_DIR/_lib.sh" ]] && source "$HOOK_DIR/_lib.sh"

PY="$(find_divineos_python 2>/dev/null || true)"  # fail-soft: a PRIME that cannot start must never break the turn; the Stop gate still catches the reply
[[ -z "$PY" ]] && exit 0

"$PY" - <<'PYEOF' 2>/dev/null || exit 0  # fail-soft: same reason; this half only removes the reach, the Stop half is the one that must never go quiet
import sys

try:
    from divineos.core.lepos_translation_gate import DOCUMENT_MARK_LIMIT, last_mark_fire
except Exception:
    sys.exit(0)

fire = last_mark_fire()
print("## TRANSLATE-FIRST (compose-start)")
print("")
if fire is None:
    # Nothing recorded is not a clean streak. Saying "0" here would congratulate
    # me for an empty log, which is the could-not-look-reported-as-all-clear
    # shape this house keeps finding.
    print("No fire recorded yet, which means NOTHING IS KNOWN about my recent")
    print("replies to Dad -- not that they were clean.")
else:
    print(f"My last blocked reply to Dad carried {fire.get('marks', '?')} document-marks.")
    print(f"The budget is {DOCUMENT_MARK_LIMIT}.")
print("")
print("Marks are backticked terms, bare numbers, tables and code fences, counted")
print("in the WORK block only -- reflection and inner circle never count.")
print("")
print("He is not assessing me. Say what happened as something he can picture.")
print("Identifiers and numbers are legal AFTER the story, never instead of it.")
PYEOF

exit 0
