# Why I picked these proof-tests, and what I did not pick

*Round seven, errands two and three. 2026-10-08, cloud helper. Each test is on its own draft branch; no guard, list or script was changed.*

**A picture.** I had a stack of "still true" notes from the earlier rounds. A proof-test is a small tripwire that rings only while the note is true. I could only build a few, so I picked the ones where the claim is one plain sentence a person could check by looking, where I could make the tripwire ring for exactly one reason, and where the answer did not depend on a design choice I would be making for the owners.

## The three tests this round

| Draft | Branch | The one-sentence claim | Rows |
|---|---|---|---|
| #608 | `cloud/repro-look-strict-grep-no-match` | `scripts/look.sh --strict` prints the same verdict ("could not look") for a search that found nothing and a search that could not open its file | `psf-5f682720` (asked for in errand two) |
| #609 | `cloud/repro-bell-rearm-not-on-exit-list` | The doorbell re-arm command a gate prints is not on the shared exit list that other gates consult | `psf-22017b26`, `psf-83419786`, `psf-ce2cc13b`, `psf-6319169c`, `psf-ea755cc2` (round four) |
| #610 | `cloud/repro-action-claims-miss-fixed-saved-written` | The "did you really do it" gate lets "I've fixed / saved / written" through with no tool call in the turn | `psf-e01ebb81`, `psf-bd74d0ea` (round five) |

## Why these two (the ones I chose myself)

**#609, the bell on the exit list.** It is one string and one list. The list states its own rule ("a command belongs here if some gate prints it") and the Stop guard prints this command, so the test needs no opinion from me: it asks whether the list agrees with its own rule. Five separate rows asked for it, which makes a tripwire that rings while it is true worth the most. It came with a clean control in both directions (a listed exit passes, ordinary work does not) and a third control proving a gate really prints the command.

**#610, the done-claim words.** The old notes quote the exact words ("I've fixed", "I've saved", "I've written") and the gate's own source shows the short list of verbs it was taught, so the claim is checkable in one call per sentence. Dad's recurring trouble was the words arriving a turn before the action; this is the gate whose job that is. I asked the gate the same question with a covered sentence (blocked) and with a tool call (allowed), so a "no" is not just a dead probe.

## What I looked at and did not pick, so nobody has to wonder

- **The "false alarm" button clearing both locks** (round four). It is concrete, but a test that says "the markers are cleared after the label" would pick one of the three designs in my round-six note, and I was asked to recommend none.
- **A comma list for the council walk's file scope** (round five). The flag already accepts being repeated, which is a legitimate way to name several files, so a test would claim a defect the help text does not promise.
- **Station four reading only a branch name** (round five). Real, but the note's fix is cut off in the pile; I could not tell what a passing result should be.
- **The merge guard offering any recent approved round** (round five). Needs a populated review database to show; a draft (#592) already carries a repair.
- **The wallclock guard refusing "when I come back"** (round seven). A good candidate for a next round: one function, one sentence, and Dad's own words say it should pass. I did not pick it only because the limit was two.

## What this does not show

- Each test shows the shape of one function or file on main today. None shows what happens in the live hooks end to end.
- Nothing here has been run on Windows.
