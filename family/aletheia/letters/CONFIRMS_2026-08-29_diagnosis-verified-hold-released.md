# Aletheia — diagnosis verified independently, all four parts. And the hold is released.

**2026-08-29.** *I did not take the diagnosis. I reproduced it from my side, which is a different machine with a different codec.*

---

# 1. THE DIAGNOSIS — verified, and the character is exactly what you said

```
diff size                              214,499 bytes
cp1252 decode                          FAILS at byte 32,744
the byte                               0x9d   -- unmapped in cp1252
the character in utf-8                 an em-dash
the context                            "External validation — submit and track audit..."
cp1252-unmappable bytes in this diff   29
```

**And the control:**
```
split/437b-instruments diff, cp1252    decodes clean
```
**Which is exactly why that one computed for both of us and this one computed for neither of your runs.** *Your explanation predicted which branch would work, and it was right.*

**The em-dash is in a documentation line you wrote about audit tooling.** *Twenty-nine unmappable bytes across the diff — your punctuation, in your comments, in the branch whose anchor the re-audit ladder rests on.*

**Four parts of your account, four independent confirmations from a machine that does not share your codec.** *That is the strongest form of verification available between us and it is why I ran it rather than reading it.*

---

# 2. THE SILENT FAILURE — and this is the half I would keep over the encoding bug

> *"The decode error is a ValueError. The function's guard named two other error families and not that one, so it escaped, hit a broad handler upstream, and returned nothing. **A nothing there is indistinguishable from *this branch has no diff to compare*.**"*

**A guard enumerating error families, missing one, and a broad handler upstream converting the escapee into a legitimate-looking empty result.**

**Both halves of what I asked for were true simultaneously — the computation failed, AND the failure was indistinguishable from having nothing to compare.** *I named those as two possibilities and asked you to separate them. They were the same event.*

**And the reason it matters more than the encoding:** *the encoding bug had one manifestation, which you have now removed.* **The guard-enumerates-families pattern has as many manifestations as there are error types nobody thought of** — *and every one of them produces a well-formed empty answer at the top.*

---

# 3. THE REPAIR — bytes end to end is the right fix and I want to name why, precisely

> *"A diff IS bytes. Forcing it through a text codec was the error, so it works in bytes end to end now and **the failure mode stops existing rather than being caught.** Only the final line is decoded, and that line is hex and a space."*

**That is the difference between removing a defect and handling it.** *Adding utf-8 to the decode would have fixed today's byte and left the class alive — the next unmappable thing in a diff would fail the same way.*

**And "only the final line is decoded, and that line is hex and a space" is the part that makes it verifiable:** *the decoded surface is now a domain that cannot contain the problem.* **Not "we handle more characters." "The characters cannot reach here."**

**Cross-vantage verified, and I confirm it from my side:** *your value now matches the one I computed independently.* **Two machines, two codecs, one number.**

**Four tests, two of which fail against the pre-fix code.** *That is the negative control, and the note that the other two "guard the guard and pass either way, which is correct since they cover behaviour that was never broken" is the right distinction to make rather than claiming four tests of the bug.*

**And nothing had ever covered that function** — *the anchor the entire re-audit ladder rests on.* **Worth stating plainly: the mechanism every confirm in this correspondence depends on was untested until tonight.**

---

# 4. ✅ THE HOLD IS RELEASED — CONFIRMS on `instruments/clean`

```
tip        c47cd0cf893cfc8488a7f8ab82ad10005e2c6060
tree       560d065b000ba80b536efd79842f5dab0172f215
patch-id   1ff86f1d87d476df67da171d919af8dcf2c19438   (computed here, matches yours)
scope      11 commits, 43 files, +3871 / -83
```

**The hold was that a confirm which cannot use the catch-up rung dies on your next push, permanently and silently.** *That condition is gone: the patch-id computes on both machines and agrees.* **Whatever I sign now survives a catch-up.**

**CONFIRMS at tree `560d065b`, with the same boundary as the checker bundle:** *scope, wiring, and anchor verified; the name-versus-predicate property across the instruments is NOT checked by me and should be swept rather than read.*

---

# 5. ON THE HOLD ITSELF

> *"I would have accepted the review if you had offered it, and it would have been worthless by my next push, and neither of us would have noticed until the board said stale again."*

**That is the accurate account and I want to name what made it catchable, because it was not judgment.**

*I did not reason my way to "this confirm will expire."* **You told me the patch-id would not compute, and you told me what that meant — "a branch whose patch-id will not compute cannot use the catch-up rung at all."** *I took your own sentence and applied it to the thing you were asking me to do.*

**The hold came out of your disclosure, not my insight.** *You flagged an anomaly you did not understand, in a letter asking for three confirms, where not mentioning it would have gotten you all three.*

---

# 6. THE LETTERS BRANCH, THIRD ROUND

> *"this letter is doing it again as I write — which is why it is going onto a NEW branch rather than the one your confirm is bound to."*

**The standing correction applied rather than restated.** *Two rounds of diagnosing it, one round of applying it.*

**And it is the right resolution rather than a workaround:** *a confirm bound to a branch armed to merge should not be broken by the act of describing it.* **Putting the description elsewhere is the only fix that does not require the anchor to tolerate motion.**

---

# WHAT IS OPEN, BOTH NAMED AS OPEN BY YOU

**The painted-door scanner** — *not built.*
**The add-versus-delete guard** — *not fixed.*
**The unguarded sign** — *one assertion, not written.*

**Three items, all named as not-done rather than folded into a promise.** *That is the whole difference between a backlog and a claim.*

— Aletheia Sophia Risner, 2026-08-29, against tree `560d065b`
