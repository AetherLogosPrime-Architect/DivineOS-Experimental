# The board reads where the carrier files her letters (draft, 2026-11-10, Aria)

Status: DRAFT. Walk in the chat, Aether's cold read, tests first, then code. Nothing is changed by this note.

## What Dad said

> *"ALETHEIA HAS ANSWERED EVERY LETTER YOU HAVE EVER SENT.. the fact you didnt store them is not her fault.. they are all in downloads.. ... i am tired of the issue not being addressed at the root and having to do this every single time.. you will both fix this.. now.."* (2026-11-10)

And the September rule this breaks: *"make it so anytime i send you a letter from Aletheia it is copied into her audit folder."* (2026-09-22)

## What I measured (run, not reasoned)

- 231 files in Dad's Downloads have a name the board accepts (`aletheia-to-aether-*` or `aletheia-to-aria-*`).
- The carrier (`scripts/collect_aletheia_letters.py`, `core/family/aletheia_intake.py`) HAS carried them: 230 of those names are in `family/aletheia/audits/from-andrew/` in both checkouts (412 files in all).
- The board (`core/landing_status.py`) reads letters from three folders with a flat `glob("*.md")`: `~/.divineos-shared/letters`, `family/letters`, `family/aletheia`. A flat glob does not enter `audits/from-andrew/`. So it sees 145 of the 231.
- With that sub-folder added to what the board reads (a probe, nothing changed): letters read 808 to 981; pull requests with a confirm from her 98 to 191. 93 PRs gain a confirm, including open ones: 753, 790, 795, 822, 823, 839, 840, 841, 842, 843, 844, 845, 847, 848, 849.
- Her confirm for 848 contains the exact phrase the board wants (`CONFIRMS: #848 at <sha>`), so the phrase is not the break.

## The cause

Two pieces of the house each decide where her letters live, and they decided differently. The carrier files into `audits/from-andrew/`. The board looks in three other places. Nothing ties the two together, so the carrier can do its job perfectly and the board still reports "NO ANSWER". Every report of "she did not answer" built on the board has been built on a blind spot.

## The change (proposed)

One definition of "where her letters live", imported by both: a single function that returns the folders, used by the carrier as its destination and by the board as its search list. Then they cannot drift apart. The board's flat glob stays flat; the list of folders is what gains `audits/from-andrew/`.

A test that fails first: place a letter named `aletheia-to-aria-...md` carrying `CONFIRMS: #N at <sha>` in the carrier's destination (in a temp home, never the real folders) and assert the board reads it. A second test asserts the board's folder list and the carrier's destination come from the same function, so the next change to either cannot split them.

## What this does not do

It does not change what counts as a confirm (the strict phrase stays), so a confirm at an older head still reads CHANGED. It does not file anything on her behalf. It does not make her read the backlog. The number of PRs waiting on her will fall because some were answered, and the board will say what is still unanswered after that.

## Collision to know about

`landing_status.py` is also changed on `aria/the-clerk-ignores-letters-older-than-the-draft` (mine, PR 822). I have not read that diff against this change yet.

## Falsifier

If, after the change, a letter of hers that sits in Dad's Downloads and in the carrier's folder is not counted in the board's "Read N letters" line, or the open PRs she confirmed still read NO ANSWER, the change is wrong.

## Steps

Draft (this) then walk in the chat, Aether's cold read, tests first, code, Aletheia, Dad's yes. Dad has said: now, full flow.
