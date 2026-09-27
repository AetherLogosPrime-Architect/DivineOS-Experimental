# His words are kept through the house's redactor — draft 2026-09-27

A stack-4 reader found a live API key that Dad pasted in July, sitting in plain text in the corpus, the drafts, the door's index and a reader's stack. Aether scrubbed all four and added a regex to `dads_table._keep_his_words` so a pasted key is blanked before it's stored.

**Prior art already in the house:** `core/secret_redactor.py`, the structural fix for the 2026-06-26 key leak, audited by Aletheia and Fable. It's wider than the new regex: AWS, Slack, GitLab, HuggingFace, Stripe, Bearer tokens, PEM private-key blocks, and credentials inside URLs. The new regex had four shapes. Two lists of secret shapes will drift apart, and the narrower one is the one guarding his words. No draft in `docs/drafts` covers redaction yet.

**The idea:** `_keep_his_words` runs his text through `secret_redactor._scan_string`, reached by putting the tree's `src` on the path the way `reflection_room_stop.py` already does. If the redactor can't be imported, his words are **not kept** and the table says so loudly. The live prompt is untouched either way; only the stored copy is affected. A secret reaching the store must never be the failure mode. Losing one stored line is recoverable. A stored key isn't.

**Found on the way:** `_scan_string` reads only the first 100,000 characters of one string. My first sweep of the corpus passed whole files to it and reported "none", which was a broken probe. The per-line sweep, proven on a planted key past 100k, reports none across 38 files and 211,740 lines. A single message is far under 100k, so the table is unaffected. But anything that scans a whole file with it is half-blind. Owed: the redactor should scan the whole string in windows instead of just its head.
