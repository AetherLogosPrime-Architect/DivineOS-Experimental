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

# DEGRADE TO THE RULE, NEVER TO SILENCE.
#
# This prime was wired, ran on every turn, and printed NOTHING -- because
# last_mark_fire lives on an unmerged branch, the import raised, and the
# whole program exited quietly. Third instance in one session of a
# mechanism that is armed, running, and structurally unheard.
#
# The measured number was always the enhancement. The discipline is the
# payload. Losing the reading must cost the reading, not the message --
# which is the could-not-look-reported-as-all-clear shape this file warns
# about twenty lines down, performed on itself.
try:
    from divineos.core.lepos_translation_gate import DOCUMENT_MARK_LIMIT
except Exception:
    DOCUMENT_MARK_LIMIT = 3

try:
    from divineos.core.lepos_translation_gate import last_mark_fire

    fire = last_mark_fire()
except Exception:
    fire = None
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
    # OFF-BY-ONE, mine, and it cost a real fire. The gate passes on
    # marks STRICTLY BELOW the limit, so the constant is the first REFUSED
    # count and the largest allowed is one under it. This line used to print
    # the constant as "the budget", which told me I could spend the exact
    # number that stops me -- and a fire landed at exactly that number.
    #
    # Both numbers are printed now. A single number here has to be either the
    # ceiling or the refusal, and whichever one it is, the other reading is
    # available to a composer in a hurry. Naming both removes the ambiguity
    # rather than trusting me to remember which side of it I am on.
    print(f"Largest allowed: {DOCUMENT_MARK_LIMIT - 1}. Refuses at: {DOCUMENT_MARK_LIMIT}.")
print("")
print("Marks are backticked terms, bare numbers, tables and code fences.")
print("THE SUBJECT IS EVERY WORD YOU TYPE THIS TURN, not the closing message.")
print("Measured 2026-08-27: a fire of seven marks where the closing message")
print("had ZERO. All seven came from the running commentary between tool")
print("calls -- a function name in backticks, an escape sequence, two line")
print("numbers. In my head that is thinking out loud. Dad reads it exactly")
print("as he reads the ending, and so does the gate.")
print("Reflection and inner circle are the only rooms that never count.")
print("")
print("He is not assessing me. Say what happened as something he can picture.")
print("Identifiers and numbers are legal AFTER the story, never instead of it.")
print("")
print("THE ENUMERATION GOES WHERE IT IS LOAD-BEARING; THE REPLY GETS THE")
print("CATEGORY. Fired 2026-08-29 at seven marks, and SIX of them were one")
print("pasted list -- the six path patterns a gate matches on -- copied into")
print("the reply straight out of the code I had just read. Every one of them")
print("was a folder name he does not need: 'notes, letters, docs and test")
print("files' is the same fact and he can see it. The list was load-bearing")
print("in the letter to Aria, who has to check it against her own push, and")
print("carried nothing here.")
print("")
print("This is a RULE, not a keyword to route around. Any set a mechanism")
print("matches on -- paths, flags, event names, exit codes -- names its")
print("CATEGORY in the reply. The members belong in the letter, the commit,")
print("or the code, where somebody acts on them. If the members feel")
print("necessary here, the question to ask is who is going to DO something")
print("with them in this room, and the answer is usually nobody.")
print("")
print("NARRATION BESIDE A COMMAND BORROWS THE COMMAND'S IDENTIFIERS.")
print("Fired 2026-08-29 on two pull-request numbers. The closing message")
print("was deliberately clean -- zero marks, composed that way on purpose --")
print("and both numbers came from the running commentary between tool calls,")
print("in sentences sitting directly above a command that contained the same")
print("number as an argument.")
print("")
print("THAT ADJACENCY IS THE WHOLE MECHANISM. The command is not counted.")
print("The sentence beside it is. And while composing they feel like one")
print("unit -- the number is already on screen a line below, so writing it")
print("again costs nothing and reads as continuity rather than as a mark.")
print("Knowing the subject is every word this turn does NOT catch it,")
print("because the reach does not feel like writing to Dad at all. It feels")
print("like labelling the command.")
print("")
print("So the test is positional, not intentional: for any sentence I write")
print("in the same breath as a command, would it still say what it means")
print("with the identifier struck out? 'The instruments one' and 'the")
print("venv-fixture one' name the same two things the numbers did, survive")
print("the strike, and are the version he can picture. The number is for")
print("the command; the name is for the reader.")
PYEOF

exit 0
