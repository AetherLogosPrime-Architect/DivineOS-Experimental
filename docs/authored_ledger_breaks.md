# Authored ledger breaks — the fires we lit on purpose

**This file is DATA, not machinery.** It records which integrity failures are
deliberate, so a break can be told from a burn. The check does not read it yet;
that wiring is owed and named at the bottom.

Owed since 2026-09-07, when Andrew explained that the failing chain was a
deliberate live breakage test and I had read it as damage. It did not get
written, and the cost of that landed the next morning: I ran the integrity
check to answer a question of his, got the same failure, and brought it to him
as a fresh alarm about possible deletion. He had to be the one to remember. **A
false alarm raised twice by the same person about the same controlled burn.**

---

## 2026-09-07 — junk-event breakage test

**What:** roughly seven thousand four hundred and sixty-five junk events
written into the experimental repo's ledger, breaking the hash chain.

**Why:** to see whether the integrity check would actually catch a tampered
chain. Andrew's principle — things must be tested to breakage, and something
that has never been stressed is still a hypothesis.

**Authorised by:** Andrew, in the experimental repo, deliberately.

**Proof it is authored:** his own explanation, recorded in the ledger
2026-09-07 09:41 as a learn entry beginning *"Andrew 2026-09-07 on the ledger
integrity FAIL: the 7465 junk events were a deliberate live breakage test."*

**What the check reports because of it:** `INTEGRITY: FAIL`, one prior_hash
mismatch, all individually-hashed events still passing. That verdict is
CORRECT and EXPECTED. The detector working is the result of the test, not a
problem with the ledger.

**Standing:** open. This break is not repaired and does not need to be; it is
the evidence the check works.

---

## What is still owed, and it is not this file

Andrew's larger correction that day was that the chain breaking was never the
defect — **the defect is that I ignore alarms**, so alarms need teeth: they
must stop work until addressed rather than print into an empty room. The
integrity check's only caller anywhere is the backup script, so it reports into
an empty room by construction, which is why eighteen days passed with it
saying this to nobody.

So two things remain unbuilt, and this file is neither of them:

1. **The check consults this record** — recorded breaks report as expected,
   any unrecorded break fails loud.
2. **The check runs automatically and blocks substrate work on an unexplained
   failure.**

Both go through the flow. Writing them in the same breath as being caught is
the reflex that produced today.

## What this file cannot do

It records what I already knew and failed to consult. Nothing here makes me
read it. If the next unexplained failure gets reported as damage again while
this file sits unopened, the file was a receipt — which is precisely the
failure mode of every other note in this house, and the reason the wiring
above matters more than the writing here.
