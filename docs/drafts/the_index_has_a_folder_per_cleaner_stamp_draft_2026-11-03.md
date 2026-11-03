# The index has a folder per cleaner stamp (draft, 2026-11-03)

The idea, not a plan. Author: Aether. Attack: Aria (she proposed the folder-per-stamp shape).

## What went wrong

Dad's-words search (`core/his_words_door.py`) keeps one shared index in
`~/.divineos-shared/dad_corpus/index`, and both houses read and write it. `CLEANER` is a hash of
the cleaning source (`_cleaner_stamp()`), so any difference in that code between two houses is a
different stamp. `build_index` resets to empty whenever `meta.cleaner != CLEANER`. Measured
2026-11-03: Aether's live house stamps `dc4ec4722e0fb2a3`, clean main and Aria's house stamp
`29c82b729d97a9cf`. Each house's build wiped the other's. The visible symptom: the index fell from
19,361 passages to 12,800 (newest date 2026-09-17), so "yesterday" was invisible and a search read
"nothing" where the words existed. This is the 2026-09-26 ping-pong again; making the stamp a
hash cured the typed-version drift and made every code difference a reset.

## The shape (Aria's, accepted)

1. `INDEX_DIR = INDEX_ROOT / <first 16 hex of CLEANER>`: a folder per stamp. Two houses with
   different cleaners each get their own folder and never touch each other's; two houses with the
   same cleaner share one. Old stamp folders are left alone.
2. A lock inside the folder, taken exclusively (pid and time in it). A builder that finds it held
   SKIPS the run and says so; it never waits (the prompt hook has a time budget). A lock older
   than a stated bound whose pid is dead is taken over; either condition alone is not enough.
3. Copy-forward: a new stamp folder starts from the nearest older folder built with the SAME
   `MODEL_NAME`, copying the vector for every passage whose `_key` (sha256 of ts and cleaned text)
   matches, so a cleaner change costs a handful of embeds and not nineteen runs. A different
   model copies nothing.
4. The reach line: "searched N of M passages, dates D1 to D2, cleaner X, folder Y", where M is
   counted by running the cleaner over the corpus (no embedding). When N < M it says the index is
   still catching up. When more than three stamp folders exist it adds their count and total size.

## What it does not do

It does not make the two houses clean text the same way; that is a carry of the live house's
cleaning changes to main, listed separately. It does not change what the search returns for a
finished index, only where the index lives and what the search says about its own reach.

## Cannot see

Whether anything else writes `INDEX_DIR` directly (callers import `door.INDEX_DIR`; the lesson
shelf has its own `INDEX_DIR`). Whether Windows lets the lock be taken over cleanly when a pid is
dead (tested on this machine only). The disk cost of old stamp folders (each is one set of
vectors, tens of megabytes).

## Open for the walk

Is a stale-lock bound of a few minutes right, given a full catch-up run can take eight seconds
and a model load more? Should copy-forward verify a sample of copied vectors against a fresh
embedding, to catch a stamp that changed the vector without changing the text?
