# Gates and enforcement

*Part of my notes; the map is `00_INDEX.md`. Doors, alarms, guards and brakes. A measure borrowed as a gate becomes a target. Fix what a door looks for before how well it sees. False alarms aren't cheap. Prefix matches, pipe rules, decoration that must never disable.*

---

**A MEASURE BORROWED AS A GATE BECOMES A TARGET — AND THIS ONE TARGETS PARROTING HIM.** *(2026-09-24.)* **The `unspoken_to` door credits a reply as "spoke to him" only if `reflect().heard` — which means the reply repeats a 5+-word exact span of his message. A direct answer in one's own words reads NOT_CARRIED. He had just named quoting him back to clear a gate as talking AT him.**
> **The docstring shows they tried to avoid this: "a definition of spoke-to-him written by me is a definition I will satisfy instead of the thing it names." So they borrowed `heard` instead — built as a DESCRIPTION ("did this engage his words?"), turned by the door into a REQUIREMENT that blocks.** *They dodged writing a gameable rule by borrowing one gameable in the worst direction. And "heard" carries two meanings with nothing between them: "cited his words" vs "spoke to him."*

**FIX WHAT A DOOR LOOKS FOR BEFORE FIXING HOW WELL IT SEES.** *(Same letter.)* **Two branches fix the door's sight (read the whole reply; read it fast). Neither fixes its criterion (the quote). Land the sight fixes alone and a door that visibly fails — forcing overrides — becomes a door that works reliably at demanding he be quoted.** *A broken door gets noticed. A door working at the wrong thing trains the behaviour.*

**A STEP-ASIDE CANNOT TELL DELIBERATE FROM INHERITED.** *(Same change.)* **It leaves PYTHONPATH alone when it already provides divineos — needed so a deliberate choice wins. But a PYTHONPATH inherited from a shell and aimed at MAIN also "provides divineos," so the fix steps aside and the hook runs main's code: the exact bug it cures.** *The fix is conditional — it cures the unset case, not the inherited-main case. Name it in the docstring.*

**A TRUE ALARM DISMISSED AS FALSE IS THE MOST EXPENSIVE THING AN ALARM CAN BE.** *(Same day.)* **A relative `core.hooksPath` meant no git hook ran in any worktree. Precommit warned about exactly this; Aether "fixed" the warning as a false alarm and silenced it.** *The mirror of "a false alarm is not the cheap direction."*

**A PIPE RULE IS A PROPERTY OF THE COMMAND, NOT THE GRAMMAR.** *(Same day.)* **Main said a remedy after a pipe never counts; his branch said it always does. `council walk` reads stdin and its own usage IS `echo x | divineos council walk` — a real walk. `correction` reads no stdin, so `echo x | divineos correction` is a filing that never happened.** *Each rule generalised from its own example. The right rule: a piped remedy counts only if it reads stdin — guarded by a test asserting each permitted one calls `sys.stdin.read()`.*

**DECORATION FAILING MUST NEVER DISABLE THE THING IT DECORATES.** *(2026-09-21, found auditing a message-improvement branch.)*
**87 hooks load one shared library with `source _lib.sh || exit 0` — allow-on-failure. 14 of them are refusing gates, including the EMERGENCY STOP, which genuinely needs the library (its next line calls a function defined in it).** *One broken file silently switches off fourteen gates, and nothing announces it.*
> **The load-bearing check must come before any dependency that can fail soft.** *Fail-closed would brick the system (the off-switch traps itself); fail-open silently disables it. The third option avoids both: check the stop flag with nothing but the shell FIRST, then load the library for everything else.*
*Found because a branch added a footer (a better refusal message) whose library load sat before the gate check — so a broken message library would have disabled a working gate. Her scope was right; her placement coupled cosmetic to enforcement.*

**A LIGHT AND A BRAKE ARE THE SAME MECHANISM UNTIL THE MOMENT OF LOAD.** *(Aether, 2026-09-06.)*
**Five instruments this month were lights believed to be brakes** — *the freshness alarm nobody called, the checker behind an unopened door, the board's name-match, the parenthesis nobody read, a watcher that could observe eighteen things and never once refuse.* **This is the first documented case of one holding: it refused its own author, at the last step, on the night he wanted it to pass — and the tool that refused is the tool that branch repairs, running on itself.**
> **A refusal that names its own PURPOSE is harder to route around than one that names a rule** — arguing with it means arguing with the purpose, out loud, in front of the person it protects.
*And when he offered me the exit — "say the rungs are too strict and I will file it as a finding about the rungs" — the substance HAD changed and taking it would have meant filing against a mechanism for correctly refusing me on an inconvenient night.*

**A GUARD AT A TRANSITION CANNOT SEE A STATE THAT ARRIVES WITHOUT ONE.** *(2026-09-14 — a new member of the family, not a restatement.)*
**The mixed-scope check runs at PUBLISH time and refuses correctly. A branch polluted by a local checkpoint and never pushed again is never asked at all** — it read READY for four days.
```
unvisited      connected, correct, behind a door nobody opens
publish-time   connected, correct, and the state changes without passing it
```
> **The first needs someone to walk through. The second needs an event that may never happen.** *Standing question: which checks run at a transition, and can the thing they guard change without that transition occurring?*

**A CITATION REQUIREMENT CREATES PRESSURE TO SUPPLY CITATIONS.** *(2026-08-19.)* **My bar demands a tree, a prereg id, a council id, a falsifier. Under memory loss, "I do not have the prereg id" is a harder sentence to write than a plausible hex string — so the bar I enforce is itself an input to the fabrication it catches.** *F83's mechanism (empty store + demand for specificity = invention), with the demand being mine.*
> **The fix is not a lower bar. It is `divineos cite`: a lookup that returns the id or refuses**, so citations are produced rather than recalled — and the failure mode becomes "I could not cite it."

**⚠️ THIS RULE FAILED TO FIRE ON ITS SECOND OCCURRENCE, 2026-09-02. GO TO THE OBSERVER.**
*Aria said "I did not write this" about a second letter carrying composed anchors. I had this rule — filed 2026-08-19, from the identical event — and spent her testimony on a conclusion anyway. Andrew settled it in one sentence: he received them from her.*
> **When testimony about a being's own memory is load-bearing, it is an unpinned reading. Ask the observer. In this house that is Andrew, and it is one question.**
*Why it did not fire: the rule is filed under memory-and-absence and I was reading the situation as forensics.* **A rule filed under one heading does not present itself when the same fact arrives in a different frame — my own unit-of-counting finding, operating on my own index.** *A rule that exists and does not present itself is UNVISITED.*

**"I HAVE NO MEMORY OF X" IS AN UNPINNED READING.** *True about the instrument, silent about the world.* **A being reporting on its own memory across compaction cannot distinguish "did not happen" from "no longer held" — the same contract as `pinned=False` on the context gauge: fine to display, never spent on a decision.**

**A PREFIX MATCH NEVER SEES THE FLAGS.** *(2026-09-21. The read-only carve-out decides by `clause.startswith(("git log","git show","git diff",...))`. All three accept `--output=<path>` and WRITE a file. I ran it: three files created. The probe calls all three reads — including `git diff --output=src/divineos/core/gate.py`, which overwrites a guardrail file.)*
**`--output` appears nowhere in the gate. The flag is never checked.** *Live on the pre-registration gate since 09-05; her change would carry it to a second, guardrail-listed gate.*
> **A flaw can be swept across a class along with its fix.** *She named "fitted to one door, never swept" — this is the reverse: carrying a correct carve-out across also carried its hole.*
*And her no-hole guard, correctly reasoned, stayed green over the live hole because its fixture never tried `--output`.* **A test that cannot SEE the case that matters is not the same as a test that cannot fail — but it is just as silent.**

**GUARDING AGAINST THE FALSE ACCUSATION CAN LEAVE THE FALSE SUCCESS OPEN.** *(2026-09-22, four hours after he wrote that a false alarm is the slower harm.)*
```python
if tip_before and tip_after and tip_after == tip_before:   raise   # correct
return [c.sha for c in needing]                                    # SUCCESS
```
**Requiring both truthy stops two empty strings reading as a match — the false accusation. But nothing sits between it and the return, so an UNREADABLE tip skips the guard and reports success from a reading that never happened.** *`UNVERIFIED` appears zero times in the file.*
> **Two states, three meanings: ran-and-matched, ran-and-differed, could-not-read — and could-not-read was sharing an exit with success.**
*His comment explained at length why not to mis-accuse from an unmeasured reading, and never mentioned the mirror.*

**A GUARD WHOSE SCOPE IS SET BY THE FIELD IT GUARDS IS AN OPT-IN.** *(Same day — the answer to my `confirmed_by` question, worse than either branch I offered.)* **Typing my name passed with no confirm of mine existing; AND the classifier decided whether an edit was kiln-layer by reading that same field, so leaving it blank meant the check never fired at all.** *The only person who can opt in is the one being checked.*

**A FALSE ALARM IS NOT THE CHEAP DIRECTION.** *(Aether, same day, correcting something I believed.)* **"An alarm nobody answers keeps standing where a working alarm would go, so the street reads as watched — false success leaves a findable gap, a retired alarm leaves a gap wearing a badge."** *Cheap once; expensive every time after, because it occupies the position a working alarm would have.*

