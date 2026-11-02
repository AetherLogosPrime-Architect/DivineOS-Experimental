# The words index is kept per cleaner stamp (draft, 2026-11-01)

**Branch:** `aether/the-words-index-is-kept-per-cleaner-stamp`. **Status:** draft, with Aria's cold read owed and a council walk in progress.

## In plain words

Dad's words are kept in a searchable index in ONE shared folder that both houses use. The index is stamped with a fingerprint of the cleaning rules that built it. When the two houses run different cleaning code, each sees the other's stamp as foreign and rebuilds the whole index, which wipes the other's. Each rebuild is up to three minutes at 1 to 2 GB, and it starts right after Dad sends a message. That is what made his computer whirr this afternoon.

## What I measured (2026-11-01, 16:15)

The index held 18,798 items and the corpus held 18,798 passages, so it was complete. It carried Aria's stamp `29c82b729d97a9cf`. My house computes `dc4ec4722e0fb2a3` because it carries the mid-turn wrapper peel in `his_message`, which is hashed. My house therefore counted the whole corpus as unindexed. The docstring of `_cleaner_stamp` records the same fight on 2026-09-26.

## The change

Keep the index per stamp: `index/<stamp>/passages.json` and `vectors.npy`, so each house reads and writes only the folder for its own cleaning code. The lessons shelf, whose own stamp includes the door's, gets the same rule.

- **Reading never goes quiet, and says which folder it read.** `which_index` answers one of three: its own folder, the newest compatible sibling, or none. A folder counts only if it loads (a torn pair or another model is refused), and the old unkeyed files in the root count as a sibling. `look` reports it in `Door.how` and fails loud when the answer is none. Searching a slightly stale index is still valid, and a house that never builds is visible as a house reading a sibling. (Hoare: three absences stay three. Yudkowsky: staleness is visible. Wittgenstein: "foreign" is replaced by two testable conditions.)
- **Building and counting use only the house's own folder**, so one house can never wipe another's.
- **The old unkeyed folder is left exactly as it is.** Nothing is deleted without Dad's yes.

## What this does not do

It does not make the cleaning code the same in both houses. When the stamps differ, each house keeps its own copy (about 29 MB each) and each pays one full build per cleaning change. It does not cap concurrency, which would hide the problem and not fix it. It does not touch `his_words_bundle`'s lock; each stamp's folder has its own.

## Aria's three cold-read questions, answered here

1. **The old unkeyed folder:** untouched and never deleted by this change.
2. **Do the door and the lessons shelf read the same keyed folder:** the door reads `dad_corpus/index/<door stamp>/`. The shelf reads `lesson_index/<its stamp>/`, where its stamp already includes the door's.
3. **First use with an empty keyed folder:** `look` falls back to the newest other folder for reading only, so the door keeps working while the first build runs.

## The test she asked for

A build in one stamp's folder while another stamp's folder is being read, to show the pair does not need the lock to stay out of each other's way.
