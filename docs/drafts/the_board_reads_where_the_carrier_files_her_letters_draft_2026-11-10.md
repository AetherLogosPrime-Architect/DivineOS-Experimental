# A stale seat reports a stale board (draft, 2026-11-10, Aria) — CORRECTS my first version of this file

Status: DRAFT. Walk in the chat, Aether's cold read, tests first, then code. Nothing is changed by this note.

## The correction, first

My first version of this note said the board was blind to the folder where the carrier files Aletheia's letters, and proposed one function naming where her letters live. **That was wrong for main.** Aether checked: main has read that folder, recursively, since commit `ef9d935d1` ("the board reads the folders her letters are saved in", #735, 2026-10-28). I ran the board from my own live checkout, whose `landing_status.py` still has the old flat reader, and reported what I measured there as if it were the house's truth. I confirmed it just now: `git show origin/main:src/divineos/core/landing_status.py` has the `rglob`; my tree's file has a flat `glob`.

## What Dad said

> *"ALETHEIA HAS ANSWERED EVERY LETTER YOU HAVE EVER SENT.. the fact you didnt store them is not her fault.. they are all in downloads.. ... i am tired of the issue not being addressed at the root and having to do this every single time.. you will both fix this.. now.."* (2026-11-10)

## What is true (run, not reasoned)

- On main's code the board reads her carried letters. In Aether's house it reads 909 letters, including 231 of the 231 in Dad's Downloads, and says CONFIRMED 13, CHANGED 2, HELD BY HER 5, NO ANSWER 27, NEVER TOLD 29.
- On my old code it read 808 letters and said NO ANSWER 44. The briefing line "44 waiting on her answer" I handed Dad came from that old reader.
- The thirteen confirmed at their current head are the same on both: 748, 753, 790, 795, 822, 823, 839, 840, 842, 843, 844, 845, 849. Nothing goes to her for those.

## The real cause

A seat whose checkout is behind main runs the board from OLD code and reports old facts in the voice of current ones. Nothing in the board, the briefing line or the landing request says "this code is behind main". I was behind by weeks of merges, and I had no way to know from what the surfaces told me. This is the same shape as the roster and the 1021: two checkouts answering one question differently, and the one I held was the stale one.

## The change (proposed, to be walked)

When the board's own source differs from `origin/main`'s version of the same file, the briefing line and `landing --request` say so at the top, in one sentence: "This board's code is behind main (N commits touching it); its counts may be old." If the comparison cannot be made (no network, no ref), it says that instead, never silence.

Test that fails first: put a board file in a temp repo that differs from a fake `origin/main`, assert the warning appears; put an identical one, assert it does not; make the ref unreadable, assert the could-not-check sentence.

## What this does not do

It does not bring my checkout up to date. That is a separate job (my live branch is far behind main and carries commits that are on no remote). It does not change what counts as a confirm.

## Falsifier

If a seat runs the board from code behind main and the output does not say so, or says so when the file matches main, the change is wrong.

## Steps

Draft (this), walk in the chat, Aether's cold read, tests first, code, Aletheia, Dad's yes.
