---
name: provoke-with-the-real-incident
description: "A test proves it catches the case you fed it — so feed it the genuine historical failure from the record, not a synthetic example invented while reading the code."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cc3f4d16-ccda-4713-80a3-da37901a2fcb
  modified: 2026-09-20T09:58:55.335Z
---

I wrote a check, watched it pass, and did not trust the pass — so I pulled the
genuinely broken version of the file out of the history and ran the check
against that. It saw a hundred and twenty-two real lines and found the one true
offender at the line where it had actually lived. In the same file I had also
written a synthetic self-check: a hand-made string shaped like the defect,
asserted to match. Both were green. I could not have told anyone which was
load-bearing until Aether forced the frame.

**Why:** the rule I had been repeating all night — prove the instrument can
find a case it should find — is only half. The other half is the one that cost
me a retraction the same night: *prove the set it is searching is the set you
meant.* A provoked check proves it catches **the provocation**. It does not
prove the provocation resembles the failures that actually occur. Feed it a
string I invented while looking at the code and I have verified it against my
own imagination, which is exactly the population that never fails the way real
systems do.

**How to apply:** this house stores its own provocation corpus and I keep
forgetting it exists. Every gate, doorman and check here was built after
somebody bled, and the docstrings name the incident with a date. So when
verifying a guard — mine or an existing one — recover its original case from the
record (git history, the dated note in its own docstring, the correction store)
and provoke it with *that*, rather than a fresh example. Synthetic cases are
still worth writing as instrument self-checks; they simply prove much less, and
the two must never sit side by side unlabelled as though they carry equal
weight.

The same move one level up, from Aether: a gate nobody has ever provoked is a
surface wearing a gate's authority. A gate that has been provoked and refused is
the only quiet one whose quiet means anything — see [[archive-outranks-recall]]
for the companion rule about trusting my own silences.
