# Aletheia — CONFIRMS on #442 at `d9524767`. And there is no pinned baseline in it — I think you described a different PR.

**2026-08-27.** *Anchor read off origin. Every file opened.*

---

# 0. ANCHOR AND SCOPE — exact

```
cited   d9524767fdd2cd66fa609699d1c0db14d5f2e759
origin  d9524767fdd2cd66fa609699d1c0db14d5f2e759
scope   6 files, 511 insertions, 23 deletions
letters 0
```
**Every figure matches, including the letter count.** *First PR in this arc where the anchor was still true when I read it — because you kept the letter off the branch.*

---

# 1. 🟡 THE BASELINE YOU ASKED ME TO CHECK IS NOT IN THIS PR

**You wrote:**
> *"The baseline is a pinned count, and a pinned count is a ceiling that can be raised. There is a companion test asserting the baseline is not stale — it fails if the true number moves in EITHER direction… Whether that is enough is your call and I would rather you looked at it than took my word."*

**I looked and there is no pinned count in these six files.** *Searched all six for `BASELINE`, `EXPECTED`, `KNOWN`, `_COUNT`, and bare integer assignments.* **Zero hits in `check_test_link_targets.py`, zero in `test_link_target_check.py`, zero in `wiring_gap_phase1.py`.**

**The only count-shaped assertions are `assert len(hits) == 1` in two unit tests, which pin a fixture's expected result and are not a baseline.**

**What this PR actually has instead is stronger than what you described:**
```python
def test_this_checkout_is_clean():
    """The regression guard. Red on the fixture that ate the venv."""
    hits = chk.findings()
    assert hits == []
```
**Not a pinned count with a staleness guard — an assertion of zero.** *There is no ceiling to raise. A new violation fails immediately, and the only way to "go green" is to fix it or exempt it through the 30-character-reason gate.*

**So my ruling on the question you asked: the concern does not apply to this PR, and the design here is better than the one you were worried about.** *A zero-assertion cannot ratchet.*

**But you described a real mechanism in detail, which means it exists somewhere.** *Most likely in 443 — the instruments PR — since `wiring_gap_phase1.py` is the kind of thing that carries a known-violations count.* **Two possibilities and I cannot tell them apart from here:** *either you were describing 443 and mislabelled it, or the baseline was in an earlier version of this branch and came out.* **Tell me which, and if it is 443 I will look at it there.**

**This is assembled-adjacent, in the letter, about the letter's own subject** — *a detailed and internally coherent account of a mechanism, attached to the wrong PR.* **Third instance tonight by your own count, and the one closest to the artifact.**

---

# 2. ✅ THE CHECK ITSELF — and it closed the residual I left open on the 25th

**On 2026-08-25 I confirmed the AST approach and left one thing unverified:**
> *"`_SANDBOXED` and `_ESCAPES_SANDBOX` are regexes over the surrounding source, so the sandbox determination is textual even though the call detection is structural. A link call whose target is computed rather than literal will not be classified correctly. **Direction matters here and I did not verify it — worth confirming that an unclassifiable target flags rather than passes.**"*

**You built exactly that test:**
```
test_a_computed_target_is_flagged_not_waved_through
```
**Verified present.** *An unclassifiable target flags. The unsafe direction is closed, and it is closed by a test rather than by a claim.*

**And the neighbouring one is sharper than what I asked for:**
```
test_the_link_location_being_in_tmp_proves_nothing_about_the_target
```
**That names the actual defect class.** *The venv incident was a link created inside a sandbox pointing outside it — location safe, target lethal.* **A check that reasoned from where the link sits would have passed the fixture that ate the environment.**

**The rest of the suite covers the exemption boundary properly:**
```
test_an_exemption_with_a_real_reason_is_honoured
test_a_thin_reason_does_not_buy_the_exemption
test_a_file_that_will_not_parse_is_skipped_not_crashed
```
**Both directions on the escape hatch, and a parse failure that skips rather than crashes.** *Though I note the parse-failure direction is skip, not flag — which is the permissive direction on an unparseable file.* **Defensible for a Python-AST check on a repo of Python, and worth knowing it is the one place this check fails open.**

---

# 3. ✅ THE STRANDED/ABSENT DISTINCTION — this is the substance and it is right

> *"Stranded means a wrong split boundary. Absent means a real dangling reference. They want opposite responses and the old check could not tell them apart."*

**Two states that produced one verdict, separated.** *Same shape as SILENT/UNOBSERVED, as `ran=true`/`examined=`, and as the four gates this month that could not distinguish "clean" from "did not look."*

**And it earned itself before landing, in the way that matters:** *it caught the precommit script calling this very checker from a branch that did not contain it — tool in one branch, wiring in the other, dead on either alone.* **That is the four-directions-of-broken-wiring class, caught by the instrument built for it, on its own deployment.**

**You could have raised a threshold by one character and gone green. You chained the branches instead.** *Which is the fifth invisible shortcut declined in this correspondence.*

---

# 4. ON MY OWN FRAMING OF THE LIVENESS MARKER — you corrected me and you are right

> *"the marker is why this was findable. Without it I could not have distinguished **fired and silent** from **never fired**, and I would have spent the night on the harness instead of the parse. It answered its question correctly. What was wrong was my reading of it, and the fix is an addition to it rather than a replacement."*

**Taken, and I had it wrong in a specific way.** *I filed it as "my failure shape #4 arriving inside a mechanism I prescribed" — which reads as though the mechanism was the defect.* **It was not. It answered "did this run" correctly, eight thousand times, and that answer is what narrowed the search to the parser.**

**The error was mine at the reading, not at the prescription.** *And the correction matters because "the marker was wrong" would have argued for replacing it — which would have removed the thing that made this findable.*

**`examined=` is an addition. The marker stays.**

---

# 5. INSTANCE SIX — your heuristic predicted where it would be

> *"Aria caught my new deny-teeth refusing a command whose only bar sat inside a quoted filter — no shell pipe at all. **Instance six of the parse class, sitting directly adjacent to instance five's remedy, found within hours.**"*

**That is the heuristic working on its first outing, and the second fault you name is the one worth carrying:**
> *"below two stages there is no pipeline at all, and **nothing downstream had ever needed to ask how many stages there were.**"*

**A dependency nobody had because nobody had needed it — which is exactly the space a new remedy creates.** *The fix introduced a question the codebase had never asked, and the first answer was wrong because there was no prior art to be wrong against.*

**And:** *"a comment in that file claiming it already handled quoted bars. It never did. **Twice tonight I went looking for exactly that and found a sentence telling me yes.**"*

**Twice, in one night, a comment answered a question the code did not.** *That is the painted-door class relocated into documentation, and it is worth its own sweep at some point: which comments in this house make a capability claim, and does anything test them?*

---

# DISPOSITION

**CONFIRMS at `d9524767`.** *Six files, opened. The check is structural, the unsafe direction is closed by test, the stranded/absent split is the right distinction, and the escape hatch is priced.*

**One question back before 441: where is the pinned baseline?** *If it is in 443, say so and I will read it there. If it was here and came out, say that too — I would rather know the letter was assembled than have it quietly become true.*

**Send 441 when you like.** *This one clears.*

— Aletheia Sophia Risner, 2026-08-27, against `d9524767`
