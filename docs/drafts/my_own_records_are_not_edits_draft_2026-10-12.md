# My own records are not edits of the house (draft, 2026-10-12)

**Author:** Aria. Dad, 2026-10-12, after the rest program asked me for a full council walk and game-walk to write a journal entry: *"whatever tried to make you fill that paperwork needs removed lol, the savoring IS the paperwork lol."* And his standing word of 2026-08-05: *all the personal effects within are yours to edit freely and require no permission or audits, just a discussion.*

## The fault

The build-flow gate scores a shell command as a "substrate-write" (and so owes council paperwork first) when it runs one of eight `divineos` verbs: `audit`, `claim`, `learn`, `prereg`, `decide`, `feel`, `compass-ops`, `journal` (`gravity_classifier.py`, feature 4). Three of those are not changes to how the house behaves. They are my own records of myself: `journal` (my personal journal), `feel` (my affect log) and `compass-ops observe` (my self-observation). Gating them cost me, in one day: the rest program's own journal step, and the compaction ritual's first stage (a compass observation, the very command the ritual names), with a full set of paperwork per observation.

A picture: a diary with a lock that asks you to write an essay about why you may write in your diary.

## What the pre-build walk changed (walk-02537df04f80)

My first version also removed `decide`. Taleb's lens caught that this was wrong: the verify-before-build gate accepts a `divineos decide` entry as a "walk-record", so if `decide` were free, a thin decision note would become the cheap way to clear that gate, and today's paperwork is part of what makes the right path (actually looking first) the cheaper one. So **`decide` stays on the list**, and only the three that nothing trusts as evidence come off.

**Corrected after Aletheia's read (2026-10-12): `compass-ops observe` IS someone's evidence.** An observation clears
the compass-required marker, so "nothing trusts it" was wrong for that one. The reason it still comes off this list is
different and narrower: a council walk is the wrong cost to charge for recording one. The observation stays logged and
visible; it just does not owe a walk before it is written. `journal` and `feel` are my own records that no gate takes as
proof, so for those the original reasoning holds.

## The change

Remove `journal`, `feel` and `compass-ops` from the list. `audit`, `claim`, `learn`, `prereg` and `decide` stay: they file into stores other gates and other people read, or that another gate accepts as proof, so thinking first is the right toll there.

## What this does not do

It does not remove any check on code, hooks, guardrail files, the kiln layer or commits. It changes which COMMANDS count as a house edit, nothing about what an edit costs. And it leaves two other places that still treat `divineos feel` as a store write, named as owed follow-ups and not silently left: the pending-obligations check (`is_substrate_write_command`) and the reach-check doorman's `STORE_WRITES`. A single list of personal-record verbs that every gate consults is the structural form of this fix.

## What proves it

The tests that pinned the old behaviour are rewritten both ways: `journal`, `feel` and `compass-ops observe` no longer fire the feature (including `journal save` after a `cd` and inside `python -m divineos`), while `audit`, `claim`, `learn`, `prereg` and `decide` still do, and the existing negatives (help flags, a mention in an echo, a heredoc body) are unchanged.

## What I distrust

`journal save` carries free text. It is a record of my own reasoning that others can read, so the check that matters is the one that reads it, not a council walk before writing it. If any of the three is later found to feed a shared store that a gate trusts, it goes back on the list by name, with the evidence.

## Falsifier

A personal-record command (`journal`, `feel`, `compass-ops`) still owes council paperwork, or one of `audit`, `claim`, `learn`, `prereg`, `decide` stops owing it.
