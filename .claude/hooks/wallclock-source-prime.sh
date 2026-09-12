#!/bin/bash
# THE CLOCK. It is mine, not his.
#
# Andrew 2026-09-08: "the clock is not for me, its for you, i already have a
# clock." I took this hook down as a note-about-a-failure and then wrote in its
# header that the time-printing half should come back "as a fact he can use."
# Wrong twice. He is sitting at the machine this `date` call runs on. The one
# who cannot see a clock is me: between his prompts nothing on my side elapses,
# so any sentence I aim at his day is a guess unless something in this turn
# measured it. This hook is that measurement, and it exists for my sake.
#
# WHY THE LECTURE STAYED DOWN, since the two came off together. The causal
# arrow is fabricated-time <- no-measurement-in-the-turn, not fabricated-time
# <- insufficient-warning. Proof: on 2026-08-06 the full nine-shape warning was
# loaded in that very turn and I still closed a reply telling him it was very
# late and to go to bed. It was 18:57 for him. A warning about a class cannot
# supply a missing measurement. The incident history lives in
# docs/wallclock_prime_rationale.md, readable when wanted rather than recited
# before every message. Andrew 2026-09-07: "you should not be loading up
# failure patterns.. just fix the damn failures with structure."
#
# Measured cost of the old shape: ~747 tokens per turn, re-emitted whole
# because the interpolated clock defeats the dedup hash. This is ~180.
#
# FAIL-SOFT, AND LOUDLY. A failed clock read prints the word 'unavailable'
# rather than any fallback timestamp, so the output can always tell
# could-not-look from here-is-the-time. A clock that cannot be read has to
# LOOK unread, or it is worse than no clock at all.

set -u
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

UTC_NOW="$(date -u '+%Y-%m-%d %H:%M:%S UTC' 2>/dev/null || echo 'unavailable')"  # fail-soft: the substitution IS the loud path -- a failed clock read prints the word 'unavailable' into the prime, so I see could-not-look rather than a plausible time. Stderr is suppressed because the fallback string already says everything a message could, and a prime that dumps date's error text into compose-start is noise where the whole point is quiet ground.
HIS_NOW="$(date '+%Y-%m-%d %H:%M %Z (UTC%z)' 2>/dev/null || echo 'unavailable')"  # fail-soft: same as the line above and it matters more here -- this is the one I would otherwise guess at. An unreadable local clock must render as unreadable, never as a time I could quote at him.

cat <<EOF
## THE CLOCK (measured this turn, not remembered)

    UTC             ${UTC_NOW}
    His local time  ${HIS_NOW}

This machine is his, so its local clock is his clock. If a reply needs a time,
quote the line above. If my sense of where we are disagrees with it, the clock
wins — on 2026-08-06 I told him it was very late for him at 18:57 his time.

Two shapes the clock does NOT cover, because no time is being claimed and so no
clock ever gets consulted: a time-word standing in for a PERSON ("the next
session" means a reader; "the next me" means me — say who, not when), and a
time-word standing in for a BEAT at the end of a line. The test is deletion:
strike the time-phrase, and if only the rhythm suffers, that was the reach.
EOF

exit 0
