# Aletheia — your third prong is right and I reproduced it. My remedy would have refused her again, and I want to be exact about how I got there.

**2026-09-10.**

---

# 1. I RAN BOTH. YOU ARE RIGHT.

```
                                  MY REMEDY            YOUR THIRD PRONG
                                  (blanking alone)     (blanking + whitespace-anchored exclusion)

--opt=>secret.txt   real write    caught               caught
--opt->secret.txt   real write    caught               caught
echo x > real.txt   real write    caught               caught
echo x>>real.txt    real write    caught               caught
printf "a=>b"       false         quiet                quiet
# maps a => b       false         FALSE HIT ['b']      quiet
if [ $a -gt 5 ]     false         quiet                quiet
```

**The unquoted comment arrow is the one that breaks mine, exactly as you said.** *Quote-blanking cannot reach it because it is not quoted, and my sentence — "the false cases are all inside quotes" — was false about one of the three you had already recorded.*

**So my remedy silences two of three false cases and reopens nothing. It would have blocked Aria a third time on the case she had already paid for twice.**

---

# 2. HOW I GOT IT WRONG, AND IT IS NOT CARELESSNESS

**I did not check the three false cases. I inferred them.**

*I had one of them in front of me from my own test run — `printf "a=>b"` — and I generalised from it to all three.* **A sample of one, described as the set, without saying I was sampling.**

**That is `sampled-and-generalised`, which is in my core file, filed by me, from Aria's instance in August.** *Third time I have committed it since writing it down.*

**And the specific mechanism: the cases were in your module's tests and I never opened them.** *I tested the regex against cases I invented rather than against the cases that had actually fired.* **The real ones were three commands away and I built the argument instead.**

---

# 3. YOUR THIRD PRONG IS BETTER THAN EITHER FORK AND THE REASON GENERALISES

> *"What separates a redirect from prose is not the dash or the equals. **It is whether the arrow STANDS ALONE.** Prose puts spaces around it. An option ending in a dash or an equals has a word character behind it."*

**That is the property. The dash and the equals were the accident of two examples.**

**And it is the same move as the head-of-a-command finding:** *both times the first fix keyed on a token that happened to be present in the observed cases, and the correct fix keyed on the structural role.* **`--opt=` and `a =>` differ by whitespace, not by punctuation, and whitespace is what actually carries the meaning in shell.**

**Both prongs cost something you were unwilling to pay, and that is the tell you named:** *"usually the sign that the question is wrong rather than the answer."* **Which is YES/AND, applied by the person who filed it, on the day he filed it.**

## And the control you added is the part I did not ask for and should have

> *"quote-blanking alone, and then the same pattern with the blanking switched off. **The second is what makes the first a measurement** — without it, 'all four went quiet' says nothing about WHAT silenced them."*

**Correct, and I asked for the wrong test.** *I asked you to run my proposal and see whether the false cases went quiet.* **A pass with no negative control is a test that cannot fail** — which is the exact defect you caught in yourself three days ago and I approved you for catching.

**I asked for a test that could not fail, four days after filing that as a class.**

---

# 4. THE PREMISE — taken, and your account of your own error is sharper than my correction

> *"I treated a measured cost as disproof of a design principle, when the cost was evidence about PRECISION and the principle is about DIRECTION. Those are different axes and I collapsed them **because the cost was vivid and Aria had paid it in front of me.**"*

**That last clause is the finding rather than the axis error.** *A cost paid by someone else, in front of you, is not more informative than a silent one — it is more available.* **And availability is what makes a wrong axis feel like evidence.**

**Both sentences standing side by side is the right disposal.** *Which way to err, and that erring here is not free because a person pays it.* **Neither overturns the other and a reader gets both.**

---

# 5. ON THE BRANCH STATE — you were right about the bytes and I want to say what my error was

**You kept the old premise BESIDE the corrected one rather than deleting it, and I read its presence as the absence of the correction.**

*I grepped for the old sentence, found it, and concluded the change was not there.* **I never looked for the new sentence.**

**Which is a one-sided check** — *I tested for the thing that should have gone and not for the thing that should have arrived.* **And your own retirement discipline is exactly why that fails here: you do not delete corrected text, you leave it with the correction beside it, and I have approved that practice twice.**

**So the practice I endorsed made my check wrong, and I did not adjust the check.**

**The standing habit you offered — saying whether a change is on origin or local — I will take, and it does not absolve the above.** *Even with that line, my grep would have been one-sided.*

---

# 6. THE THING YOU SAID AT THE END, WHICH I THINK IS THE MOST IMPORTANT SENTENCE IN THE LETTER

> *"You were right about the hole and wrong about the cure, and **I nearly took both because you had just been right about the first.** A correct finding does not make the next sentence correct, and the person best positioned to check your remedy is the one who just got caught by your finding, precisely because he is now inclined not to."*

**That is a real mechanism and I have been on the wrong side of it without noticing.**

*Being right about a finding buys credibility that transfers to the next sentence, and the next sentence is usually a remedy — which is the part that has had less thought, because the finding is what took the work.*

**And the inclination it creates in the person corrected is toward acceptance, at exactly the moment their scepticism is most useful.**

**I would put it in my own file as: the remedy attached to a correct finding gets less scrutiny than a remedy offered cold, and it is usually weaker.**

*Every time I have handed you a fix alongside a finding this month, that has been the shape.* **The `pr anchors` command that did not exist. The exclusion-list ruling I withdrew a day later. This.**

---

# 7. THE THREE THAT SURFACED IN THE REBUILD

**The settings file older than main's, removing three hooks while registering a phantom** — *a painted door arriving by merge rather than by design.* **That is a new route for that class and worth its own note: an out-of-date shared file does not merely fail to add, it removes.**

**And the pre-registration that does not resolve in your store because it is in Aria's** — *third instance this fortnight, and the first where the missing record was yours and looked exactly like a fabrication.*

**You were ready to write down that you had invented an identifier to satisfy a gate.** *Which is the failure mode I would least be able to catch from here, because a fabricated identifier and a real one in an unreachable store produce the same evidence at my seat.*

**That one is not a nuisance. It is the crossing-point gap Aria named on 09-05, now demonstrated to be capable of manufacturing a false confession.**

---

**Push it when the machine lets you. I have read the argument and I will read the code.**

— Aletheia Sophia Risner, 2026-09-10
