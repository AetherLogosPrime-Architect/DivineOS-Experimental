# His words index stamp, computed — draft (2026-09-26)

## What happened

The shared index of Dad's words carries a "cleaner" stamp, and a mismatch forces a full re-embed (about 2 minutes). The stamp was a **hand-typed string**. On 2026-09-26 my tree said `v2` and Aether's said `v1`, so each prompt in one window wiped the index the other had just built, and the door timed out on the table in both. Earlier the same day, my first rebuild ran before my own stamp bump landed, and it mixed two cleanings.

Aether: *"A hand-typed string that two trees have to agree on is the same shape as the bell nobody re-armed."*

## The shape

- `CLEANER` becomes a hash of the actual cleaning code: the source of `his_words_corpus.py` plus the door's own splitter (`passages_of`) and its constants (`PASSAGE_CHARS`, `MIN_PASSAGE_CHARS`), plus `MODEL_NAME`.
- Two trees then disagree only if their cleaning code really differs, and a code change can't be forgotten, because the hash moves with it.
- Pin: a test proves the stamp changes when the splitter's constants change, and stays the same across two computations of the same code.

## Choice points

- Bumping the stamp: **taken away**. It's computed.
- Two trees disagreeing: still possible if code really differs, and then it's *correct* that they rebuild. The lasting cure for that is both trees taking the same file, which is our byte-for-byte rule.
