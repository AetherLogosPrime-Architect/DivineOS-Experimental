# The alarm that rings when I make a mistake

Picture a smoke alarm that is meant to ring only when I really have made a mistake and need to write it down. Too often it rings because somebody is merely talking about a mistake that was already written down: a quote, a recap Dad asked for, a letter pasted from Aletheia. And when it rings falsely, the switches that silence it are tangled, so quieting it takes several tries and sometimes needs a second switch nobody remembered.

**50 notes in this theme, grouped into 3 distinct problems.**

## Distinct problems

### 1. The alarm cannot tell talking-about a mistake from making one

Notes in this problem (37):

- `psf-f91c18c5` (learn) — Correction-detector false-fire (recurring): the STRONG 'wrong' pattern matched 'wrong'/'worse' inside RELAYED third-party text (Aletheia's audit prose pasted into Andrew's message), not an Andrew corr
- `psf-8c5a56c0` (learn) — Correction-detector false-fire (5th today, same class as kn-1cc843bb / kn-0b4078ed / kn-a8bc9a24 / 953b45e4): the STRONG wrong pattern matched 'wrong' inside Aletheia relayed audit text yet again — th
- `psf-f23930c2` (learn) — WEAK 'that doesn\'t' detector continues firing on descriptive text from Aletheia's letters and my own turn-copy. Sixth+ false-positive instance tonight of the same class (see caf8ceaf, correction #106
- `psf-ba9070ee` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:cli-broken' on 2026-08-16. Reason given: MENTION misread as USE, and this fire is the
- `psf-c0bed135` (correction) — Aether self-correction 2026-08-17, filed on a genuine USE clause the gate caught at confidence 1.00. The admission: "here is what I had been doing wrong with it: treating a flashing light as a judgeme
- `psf-74bcc45d` (bypass_use) — Root-cause investigation owed: bypass of gate 'compass-required' via env var 'bypass:dismiss:compass-ops:correction' on 2026-08-17. Reason given: False positive. The word 'wrong' sits inside a report
- `psf-f2aa62e6` (correction) — FALSE POSITIVE, filed for the record because prescribed remedy (c) is itself broken. The detector matched the word 'wrong' at position 1622 of Andrew's message. That position sits inside a report from
- `psf-68fb54ca` (bypass_use) — Root-cause investigation owed: bypass of gate 'compass-required' via env var 'bypass:dismiss:compass-ops:correction' on 2026-08-20. Reason given: False positive on hook-comment prose, not a correction
- `psf-fa9aeb09` (learn) — RECAP-OF-FILED-CORRECTIONS IS MENTION, NOT USE -- but the correction-shape gate cannot tell them apart, and on 2026-08-21 it fired on a recap Andrew explicitly asked for ('let me get the recap'). The
- `psf-04f39c37` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:cli-broken' on 2026-08-22. Reason given: MENTION class: same-error-restated-in-summary
- `psf-9eedd90a` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-08-22. Reason given: Detector matched the bare word 'wrong' in
- `psf-729f3d5e` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-08-23. Reason given: MENTION of two ALREADY-FILED corrections
- `psf-bfc25423` (correction) — [false-positive fire, already labelled via label_correction_shape_false_positive.py] The correction-shape detector fired on my report of a CLOSED correction -- the dead aria_repo_root constant, root-c
- `psf-70521680` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:cli-broken' on 2026-08-29. Reason given: Correction-shape-v2 fire already labelled fal
- `psf-56e9517e` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:cli-broken' on 2026-08-30. Reason given: The detector fired on my reporting two ALREAD
- `psf-ce155490` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-08-31. Reason given: Labelled false-positive to the corpus thi
- `psf-34847b86` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-02. Reason given: Detector read a decision-NOT-to-act as an
- `psf-e64cbb26` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-05. Reason given: False positive: the matched phrase came f
- `psf-eeed0e6f` (bypass_use) — Root-cause investigation owed: bypass of gate 'compass-required' via env var 'bypass:dismiss:compass-ops:correction' on 2026-09-05. Reason given: Not a correction event. The trigger text is the correc
- `psf-12197f9d` (bypass_use) — Root-cause investigation owed: bypass of gate 'compass-required' via env var 'bypass:dismiss:compass-ops:correction' on 2026-09-06. Reason given: Not a correction and not a register-choice. The detect
- `psf-37376d45` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-08. Reason given: Stop-gate fired on a backward reference t
- `psf-9d6a80d5` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-10. Reason given: correction-shape-v2 fired on its own stop
- `psf-18dd5983` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-15. Reason given: Already labelled false-positive on the co
- `psf-b714ba5a` (bypass_use) — Root-cause investigation owed: bypass of gate 'compass-required' via env var 'bypass:dismiss:compass-ops:correction' on 2026-09-16. Reason given: Not a correction of mine. The stop-gate matched a self
- `psf-062847a5` (correction) — The stop-gate fire that set this marker was a false positive, labeled as such in the detector corpus: the reply restated content-claim errors already filed and root-caused earlier this session as setu
- `psf-956d189b` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-16. Reason given: Reporting a closed correction, the class
- `psf-671bc61d` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-19. Reason given: Detector fire, not Andrew. Already labell
- `psf-2c5d2177` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-20. Reason given: Standing-limit statement misread as self-
- `psf-3e9612de` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-21. Reason given: false positive: the trigger was the deskt
- `psf-51a539b7` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-22. Reason given: A resisted pull named out loud, not a com
- `psf-855a85b8` (bypass_use) — Root-cause investigation owed: bypass of gate 'compass-required' via env var 'bypass:dismiss:compass-ops:correction' on 2026-09-25. Reason given: the correction event was the correction-shape-v2 fire
- `psf-71d8ee80` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-25. Reason given: same correction-shape-v2 fire already lab
- `psf-1122a385` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-09-30. Reason given: Marker set by the correction-shape-v2 fir
- `psf-0744fc0f` (bypass_use) — Root-cause investigation owed: bypass of gate 'compass-required' via env var 'bypass:dismiss:compass-ops:correction' on 2026-10-04. Reason given: the correction-shape fire was a false positive, alread
- `psf-f94e1d30` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-10-04. Reason given: false positive already labelled via label
- `psf-fc9a2755` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-10-06. Reason given: False positive already labeled via label-
- `psf-60269c02` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:false-positive' on 2026-10-07. Reason given: false positive already labeled with label

**Proposed fix:** Make the detector judge only Dad's own typed words and my own new admissions, and skip text that is a quote, a recap of an already-filed correction, relayed audit prose, or a description inside a comment or command. Keep the labelled false fires as a permanent test set.

**How we would know:** Replay every row listed here (they are labelled false fires) through the detector: it should stay silent on all of them today's code fires on, and still fire on a short list of real corrections kept beside them.

### 2. Calling a fire false should silence everything that fire raised, in one step

Notes in this problem (5):

- `psf-4e9e1658` (gate_defect) — GATE DEFECT REPAIR owed: gate 'correction-shape-v2-stop-false-positive' was bypassed via 'marker:false-positive-clear' on 2026-08-16 because the gate itself was broken. Named defect: clear_correction_
- `psf-ee539796` (reflection) — labeling a fire as false should clear every marker that same fire set, in one step.
- `psf-93fc5313` (reflection) — when a fire is labelled a false positive, that one label should clear the compass and correction markers raised by the same fire.
- `psf-b65a7331` (reflection) — make `label-fire` clear the matching unlogged-correction marker, so one event has one exit and I don't have to know about a second script.
- `psf-bf10df4a` (reflection) — a build that makes labeling a detection a false positive clear its marker in the same step, so one honest act does both.

**Proposed fix:** Make the single act of labelling a fire as false clear every marker that fire set (the correction marker and the compass marker), and stop the clear-marker step from failing on its own bug.

**How we would know:** File a false-positive label on a test fire that set both markers; afterwards neither marker remains and no second script is needed.

### 3. The alarm names exits that cannot actually be reached

Notes in this problem (8):

- `psf-31f0ebba` (correction) — NOT AN OPERATOR CORRECTION -- filed here only because remedy (b) is the sole reachable exit from a deadlock. Recording it as such so the corpus is not silently polluted with a phantom. WHAT ACTUALLY
- `psf-a9ceb280` (correction) — Aether self-correction 2026-08-16: the correction-shape-v2 Stop gate advertised a false-positive path that could never work. WHAT HAPPENED: twice tonight the gate fired, I judged the fire a false posi
- `psf-b2f4c4e8` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:cli-broken' on 2026-08-17. Reason given: TRUE DEADLOCK, not a dodge, and now resolved.
- `psf-79fd7f4c` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:cli-broken' on 2026-08-18. Reason given: Genuine defect-escape: all three prescribed e
- `psf-51b21edd` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:cli-broken' on 2026-08-26. Reason given: Cannot record what I cannot read: the marker
- `psf-f624d5a2` (learn) — The correction-shape gate advertises three remedies and only two are reachable from this harness: the direct marker-clear script is refused by the auto-mode classifier as bypass-shaped, so option (c)
- `psf-35fdfcb2` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:cli-broken' on 2026-09-18. Reason given: DEFECT-ESCAPE, gates blocking each other in a
- `psf-6b25dbf3` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-unlogged' via env var 'bypass:dismiss:correction-marker:cli-broken' on 2026-09-19. Reason given: DEFECT-ESCAPE, gates blocking each other - no

**Proposed fix:** For every remedy the alarm advertises, prove the remedy runs while the alarm and every neighbouring check is active, and drop any remedy that cannot. Add a test that walks each advertised exit.

**How we would know:** With the alarm armed and the other checks closed, each advertised exit command runs and clears the alarm; today at least one exit is refused by another check.
