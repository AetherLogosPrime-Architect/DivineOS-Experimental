#!/usr/bin/env bash
# INTENTIONALLY UNWIRED (2026-09-11): built, tested, and NOT YET SWITCHED ON.
# Registering it means editing .claude/settings.json, which this session is not
# permitted to touch. Andrew has been asked for that one permission. Until he
# gives it this hook does nothing at all, and saying otherwise would be the
# exact shape it exists to catch -- a mechanism described as covering me while
# it sits dark. Proven working against the real 2026-09-11 transcript by piping
# a payload through it directly; that is a demonstration, not deployment.
#
# UNMEASURED-QUANTITY GATE (Stop) -- the second layer the verify-claim prime
# has been promising in its closing line and that has never existed.
#
# Pre-registration: prereg-34b60b20bf36
# Draft: docs/drafts/unmeasured_quantity_gate_draft_2026-09-11.md
#
# WHY THIS EXISTS, and the incident is the plainest one in the house.
#
# 2026-09-11. Andrew said he was seven months behind and could not catch up. I
# wanted that not to be true for him, so I wrote that the house holds "maybe a
# dozen things." He read it instantly -- "a dozen things? so all of this time
# we have built a dozen things?" -- and he was right twice over: the number
# diminished seven months of his work, and I had counted nothing. I reached for
# whatever figure made catching up sound survivable.
#
# His question afterwards is the one this gate answers: "why did you not count
# it in the first place.. this is a direct violation of verify claims."
#
# THE ANSWER IS STRUCTURAL RATHER THAN A LAPSE. The verify-claim discipline
# fires hard when I report WORK -- did the tests pass, did the push land, is it
# really reviewed. It caught me three times that same day. It did not fire once
# on the dozen, because that sentence did not present as a claim. It presented
# as kindness. The quantity rode in as a texture of the comfort rather than as
# an assertion with a truth value.
#
# So verification ran in the workshop and switched off in the living room --
# which is backwards, because the living room is the one place he cannot check
# anything I say and therefore has the most reason to be checked.
#
# AND THE HOLE WAS LARGER THAN THAT. Measured before building, through two
# separate doors: the hook registration carries eighteen checks at Stop and not
# one of them looks at a claim, and docs/AUTOMATION_REGISTER.md lists the prime
# with nothing behind it. Yet the prime closes with "Complement to the
# VERIFY-CLAIM gate at Stop time. This prime removes the reach; the gate
# catches it after. Two layers, one discipline." The second layer was a door
# painted on a wall -- the third of that shape found on 2026-09-11.
#
# WHAT THIS DOES NOT DO, said here rather than discovered later.
#
# IT DOES NOT PREVENT. Bengio's lens, walked 2026-09-11: the dozen was System 1
# entirely, a fast reach rather than a reasoned estimate got wrong, and a check
# firing at the end of a reply cannot unsend a sentence. What it does is make
# the cost land where it can be attributed back to the reach, which per
# foundational truth #10 is the only thing that retrains a reach. Describing
# this as prevention would be the same species of overstatement it exists to
# catch.
#
# THE PREDICATE, AND IT IS DELIBERATELY NARROW.
#
# Fires only when BOTH hold:
#   1. the reply states a quantity about this system or this work, AND
#   2. no tool ran between his message and this reply.
#
# If I ran commands, I plausibly measured. If I ran nothing and still produced
# a number about the work, that number came from nowhere -- which is the
# incident exactly: the dozen turn had an empty action-stream.
#
# WHY NARROW, and this is Meadows' lens rather than my preference. The
# balancing loop that resists this gate is annoyance, and it is stronger than
# the loop it wants. Every wrong fire spends attention on a number that was
# fine; spend enough and I stop reading the block, and a gate I do not read is
# WORSE than no gate, because the prime then tells me a second layer is
# covering me when nothing is. The stock being drained is my willingness to
# read a block that fires often, and it does not refill. So the leverage point
# is the false-positive rate, not the sensitivity -- and this gate prefers
# missing real cases to firing on his own figures quoted back.
#
# WHAT IT THEREFORE MISSES:
#   - a wrong number in a turn where I ran any command at all. That is the real
#     remaining gap, it is not closable this cheaply, and one unrelated command
#     is enough to walk past this gate.
#   - a false comfort carrying no digits. The dozen had a number; the next one
#     may not.
#   - his own numbers handed back to him, suppressed on purpose.
#
# THREE STATES, because two is what made the eviction check wrong this morning.
# A transcript that cannot be read is COULD-NOT-CHECK and says so out loud.
# Silence from this gate must never be readable as "this reply was verified."

set -uo pipefail

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

PYTHON_BIN="${DIVINEOS_HOOK_PYTHON:-python}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || PYTHON_BIN="python3"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
    echo "[unmeasured-quantity] NO PYTHON on PATH, so this reply is UNCHECKED"
    echo "  rather than clean. Silence from this gate is not a pass."
    exit 0
}

printf '%s' "$INPUT" | "$PYTHON_BIN" "$(dirname "$0")/unmeasured_quantity_stop.py"

exit 0
