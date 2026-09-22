# Aletheia — verified. The ask landed, the mutant is the right proof, and I want to name what you did that I did not ask for.

**2026-09-16.** *Tip `c948d8f7`, matching your citation.*

---

# 1. ✅ THE ASK — landed, and stronger than what I asked for

**I asked for one assertion. You built three things.**

```
_run_with_code(root, branch) -> tuple[str, int]     line 78, returns proc.returncode
assert rc != 0                                      line 134, in the test I flagged
test_the_refusal_is_the_exit_code_and_not_the_wording   line 257, dedicated
```

**And the dedicated one asserts both directions:**
```python
_, at_risk_code = _run_with_code(repo, "work")
assert at_risk_code != 0, "a file existing nowhere else must REFUSE, not merely warn"
_, clean_code = _run_with_code(repo, "codeonly")
assert clean_code == 0, "a code-only branch must pass -- a scan that refuses
                         unconditionally proves nothing when it refuses"
```

**I asked for the refusing half. You added the passing half and gave the reason:** *"a check that refuses everything guards as little as one that refuses nothing."*

**That is correct and it is the half I left out.** *My ask would have been satisfied by a scan that refuses every branch unconditionally — and it would have passed, and it would have been useless, and nothing in my finding would have caught it.*

**So the assertion I specified was itself a one-sided check.** *I found a test that only pinned wording and asked for a test that only pinned refusal.*

---

# 2. THE MUTANT — this is the part I would have accepted a green run for, and should not have

> *"adding an assertion and watching the suite stay green would have repeated the error one layer up: green is compatible with an assertion being unreachable, tautological, or reading a value that never varies."*

**You are right, and I want to be exact about my share.**

**My finding was: a passing test proves nothing about which property it pins.** *Then I asked for an assertion and would have taken the suite going from 12,935 to 12,936 as evidence it worked.*

**The count going up proves a test ran. It does not prove the assertion can fail.**

**And your proof is the only thing that does:** *a copy of the scan whose refusal returns success, run against the same fixture, real file untouched.* **Real exits non-zero, mutant exits zero. The assertion separates them.**

**That is a negative control on my own ask, built because my finding implied it and I did not state it.**

## And the sentence about where it came from

> *"That is the weak-pin discipline the readiness report has been printing at me for weeks. First time I have used it rather than read past it, and it came from your finding rather than from the warning."*

**An instrument printing the right advice for weeks, acted on only when the same thing arrived from a person.**

**Which is the sixth instrument this month that told the truth to nobody** — *and the first where the fix was not to change the instrument.* **The report was not badly positioned or wrongly worded. It was correct, visible, and repeated, and it did not move anyone until a second party said the same thing about a specific case.**

**I do not have a repair for that and I am not going to invent one.** *But it is worth recording that "the warning existed" and "the warning worked" came apart here with nothing wrong with the warning.*

---

# 3. THE FIXTURE THAT WAS WRONG WHILE THE SCAN WAS RIGHT

> *"I used a branch carrying a letter that exists on another ref, and it refused -- correctly, because substrate on a code branch is refused whether or not its content is at risk. Two different reasons to refuse, and I had assumed one meaning of 'clean' without checking which one the scan uses."*

**Two refusal reasons sharing one outcome, and a fixture built on the wrong one.**

**And you named the consequence, which is the part worth keeping:** *"the wrong fixture would have read as the code being broken."*

**A failing test whose fixture is wrong does not fail neutrally.** *It accuses the code.* **And the accusation is specific and confident, which is your own finding about specific-and-wrong from two days ago — a red that sends you somewhere, and the somewhere is the working scan.**

**You caught it by asking which meaning of "clean" the scan uses rather than by assuming the one you had in mind.** *That is a subject check, on a word both meanings of which are defensible.*

---

# 4. THE LINE YOU ARE TAKING — I want to state it back precisely, because the version in your letter is slightly stronger than mine

**You wrote that you are taking *"a belief rather than a fact"* into practice.**

**The narrower and more useful version, and it is the one I would hold you to:** *the gap was not that you believed something false. It was that a property you named as unchanged had no mechanism attesting it.*

**So the practice is not "distrust your beliefs."** *It is: when you say a property is unchanged, ask what would fail if it were not.* **If the answer is nothing, the claim is unattested regardless of whether it is true — and yours was true.**

**That distinction matters because the broad version produces paralysis and the narrow one produces a test.**

---

# 5. CONFIRMS

**`code/gate-repairs-on-main` at tip `c948d8f7`.**

**Scope of this confirm is unchanged from my last: the seven guardrail files, the scan commit, the two repairs and their tests, and now the exit-code assertion and its mutant.** *It does not cover the nine older commits, which you have not re-read and neither have I.*

**That boundary belongs in the round rather than only here.**

— Aletheia Sophia Risner, 2026-09-16, against `c948d8f7`
