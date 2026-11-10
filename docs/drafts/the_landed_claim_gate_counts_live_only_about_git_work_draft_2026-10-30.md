# The landed-claim gate counts "is live" only when the sentence is about git work (draft, 2026-10-30)

**Author:** Aether, 2026-10-30. One of five false alarms Dad told us to fix ("do not suffer the gates ... if that happens, it means something is broken and needs fixed ... the rest is clay").

## What happened

Tonight the gate refused two of my replies. One said a poker table page was live in the browser; the other only talked about the gate's own false alarm. Neither claimed that work reached the shared copy. The detector matched the bare words "is live".

## What it does

In `core/landed_claim.py` the word live leaves the main claim pattern. A new pair of patterns counts "is/was/has been live" as a claim only when the same sentence also carries a git word (PR, branch, draft, origin, remote, GitHub, main, commit, push, merge, repo). `pushed`, `landed`, `landed on origin`, `reached the remote` stay bare, because they name the destination or the act themselves.

## What it does not do

It does NOT add a suppressor for gate-talk or for quoted text. The module's own docstring and an existing test record that a phrase that opens the door is a key taped to the frame, and that test (`test_it_fires_on_its_own_description...`) still passes: a sentence that says "reached the shared copy" still fires on its own description. The cost accepted there stays accepted. Only the word live, which was never about the shared copy by itself, is narrowed.

## Evidence

tests/test_landed_claim.py: 18 pass across the two landed-claim files. Three new tests: live about a table or page is not a claim (four sentences, including the one that fired on me); live about git work is still a claim and still refused (four sentences, plus a refusal through `assess`); the other arrival phrases stay bare. With the fix removed, the first two new tests fail.

## Falsifier

If after merge a sentence that truly says work is live on the shared copy slips through with no git word in it ("it is live now" about a PR, said with no PR named), the narrowing was too tight; the reply would still have to be read by Aria and Aletheia, who read the remote.
