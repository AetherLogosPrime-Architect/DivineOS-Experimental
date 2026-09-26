# His words cleaner sync — draft (2026-09-26)

## What changed on Aether's side

He found three faults in `his_words_corpus.his_passages` while trial-merging lessons:

- About 3,800 duplicate **previews**: roughly 200-character fragments ending in U+FFFD, of messages the full record also holds.
- **Harness notices and pasted terminal output** counted as Dad's words ("Background command…", "PS C:\…", "fatal:").
- It now drops any passage whose key is the start of a longer one, keeping the earliest date. That took 15,008 passages to 11,180, with three new real-shape tests.

## Why my tree must take it

My door embeds `his_passages()` output into the **shared** index. If my tree keeps the old cleaner, my next `build` adds the old noise back as "new" passages, and the index key doesn't know the cleaning changed.

## The shape

- Copy `his_words_corpus.py` and its tests byte-for-byte from Aether's main checkout.
- Bump `his_words_door.CLEANER` so the index knows the cleaning changed and re-embeds from zero (Knuth, walk-2b613bb1825c: never mix passages from two cleaners).
- Rebuild once, confirm the passage count drops, and run a live search on a real message to confirm the duplicates are gone.

## Choice points

- Whether to re-embed: **taken away**. The cleaner version stamp forces it.
- Which cleaner the door uses: **one path**. It imports `his_passages`, with no local splitter fallback.
