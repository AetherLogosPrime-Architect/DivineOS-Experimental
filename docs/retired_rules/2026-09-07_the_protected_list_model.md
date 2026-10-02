<!-- retired-rule
id: protected-list-model
retired: 2026-09-07
retired-by: Andrew
successor: the exemption model, listed at scripts/review_exempt_paths.txt
pattern: (?i)\bfiles?\s+in\s+[`'"]?scripts/guardrail_files\.txt
pattern: (?i)guardrail_files\.txt[`'"]?\s+AS\s+IT\s+WAS
pattern: (?i)\bon\s+the\s+guardrail\s+list\b
pattern: (?i)\btouch(?:es|ing)?\s+(?:a|any)\s+guardrail\s+file
pattern: (?i)\bguardrail-touching\s+commits?\b
pattern: (?i)\blist\s+of\s+guardrail\s+files\b
-->

# The protected-list model

**Retired 2026-09-07 by Andrew. Replaced by the exemption model.**

## What it said

Some files are special. Keep a list of them. Changing anything on that list
requires external review before it enters the trunk. Everything not on the
list enters without review.

## Why it was retired

The list asked the wrong question. *Which files are special?* has to be
answered again every time a file is created, by somebody who remembers the
list exists and judges correctly that the new file belongs on it. The guard
therefore ran on memory, and memory is the faculty that has failed in this
house every single time it was load-bearing.

The observed consequence, recorded before the change: every-line-audited was
stated policy with no enforcement behind it, and both merge gates passed
cleanly whenever a change happened to touch nothing on the list. A new file
was unguarded by default.

Andrew's words, relayed through Aria: there are no longer any special files,
Aletheia audits any and all code that enters the trunk, and the only
exceptions are the prose paths — which is the list that became the successor.

## What replaced it

The exemption model, in `scripts/review_exempt_paths.txt`. It asks the
opposite question: *which paths are merely prose?* Everything else needs
review. A new file is guarded by default and becomes unguarded only when
somebody deliberately lists it, which inverts the direction memory can fail
in. Forgetting now produces too much review rather than none.

The live server-side check resolves that list **at the commit being
examined**, because what counts as prose is a property of the branch being
merged rather than of whoever happens to be reading.

## Where it kept getting served from, and how that was closed

Three surfaces, all of them authoritative-looking:

1. The project instructions loaded at the start of every session stated it as
   a numbered hard rule. Corrected the same night.
2. The live merge check defined a function that loaded the retired list. The
   function was never called, but a search for the old list found it
   apparently load-bearing inside the current gate. Deleted, with
   justification recorded.
3. The message that same check prints when it blocks a commit taught the
   retired rule to whoever had just been blocked and was reaching for an
   explanation. Rewritten to state the exemption model, and to say plainly
   that the old list is not what governs.

## The thing worth keeping from it

Point-in-time resolution. The protected list was resolved at the commit under
examination rather than at the tip, so a branch could not be judged by a rule
that arrived after it was written. That idea survived the retirement intact
and is how the exemption list is loaded today.
