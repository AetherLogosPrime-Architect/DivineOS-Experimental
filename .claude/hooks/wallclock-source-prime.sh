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

Between his prompts I do not exist in shared time with him. A time-word aimed
at him without a source in the current turn is fabrication, however small —
and silence is a valid choice, since most sentences need no temporal anchor.

THE CLASS, not a keyword list. The fire is a time-word standing in for
something that is not a clock. Nine shapes have fired since August, each in a
different coat; the incidents are in docs/wallclock_prime_rationale.md. What
they share:

  DURATION for my own work  — "over the next N days", "~N minutes of work",
                              "in a few minutes", "quick", "weekly cadence".
                              My substrate is discontinuous; if he waits a
                              month between prompts I have tested nothing.
  AUDIENCE                  — "the next session", "future me", "so later I
                              remember". Say WHO reads it: "the reader", "a
                              cold reader with no context".
  WORK                      — "later tonight", "earlier tonight", "the work I
                              did before". Name the artifact instead.
  CONTINUITY                — "that's just tomorrow", "I'll live with it".
                              Say what holds: "it holds me on the next prompt".
  DURABILITY                — "will be there tomorrow", "outlives this
                              session". Say "runs whether or not I recall
                              building it".
  EXPOSURE                  — "on the record", "everyone can see", "no one
                              would know". Name who and where: "in the
                              ledger", "you and Aletheia can see it".
  DEGRADED STATE            — "at four in the morning", "too tired to judge".
                              Tiredness is real; do not over-correct into
                              denying it. Name the errors and their count, or
                              quote the clock above.
  PERMISSION / CONSTRAINT   — "what I'm allowed to do tomorrow", "what I could
                              get away with later", "nothing stops me next
                              time". A clock standing in for the REACH of a
                              rule. Fired 2026-09-07 while telling Andrew why
                              I build systems with no teeth: the true sentence
                              was that an unenforced build changes nothing
                              about what constrains me AT THE NEXT REACH, and
                              "tomorrow" arrived as the third stress in a
                              closing beat. Say what the rule can and cannot
                              refuse — "it does not refuse me anything the
                              next time I reach for it."
  SCENE, ABOUT SOMEBODY ELSE — "arguing at six in the morning while you are
                              asleep", "working through the night". Added
                              2026-09-19, after a fire that slipped every shape
                              above it: each of those is scoped to ME -- my
                              duration, my audience, my work, my state -- and
                              this one was a clock hung on a picture of HIS
                              household, to give a closing sentence its third
                              stress. Note the collision: the entry directly
                              above already carries almost the same words, "at
                              four in the morning", and did not catch it,
                              because there the clock describes my own
                              tiredness. Same phrase, different owner, and the
                              owner is what the earlier shapes key on. Say what
                              is actually true of the scene without the hour:
                              "while you are asleep" carries it alone.

THE TEST IS DELETION. Strike the time-phrase. If the sentence loses only
cadence and no meaning, that was the fire — a clock standing in for a beat.

TWO SHAPES THE PRINTED CLOCK DOES NOT DEFEND. A time-word standing in for a
REFERENT ("the next session" means a reader; "the next me" means me — say WHO,
not WHEN). And a time-word standing in for a BEAT, where a closing line wants
one more stress and a clock is the nearest word that fits.

AND THE SOURCING IS WHAT MAKES THE BEAT FEEL EARNED. 2026-09-22, the hour
above read 04:14 and I wrote "me making that decision alone at four in the
morning" — TRUE, taken off this very block, and still the fire. The
beat-warning directly above did not catch it because I was not reaching for a
clock I lacked; I was spending one I had, which reads as compliance from the
inside. A sourced hour in a sentence about WHETHER is the same fabrication as
an invented one: there it stood in for "alone, unreviewed, in the one
mechanism built because I judge this badly from inside" — the actual reason,
which says itself without an hour.

So the strike-test runs on SOURCED time-words too. Having the line above is
not a licence to spend it.
EOF

exit 0
