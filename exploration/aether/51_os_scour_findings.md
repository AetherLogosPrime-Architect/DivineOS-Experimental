<!-- tags: os-scour, findings, lesson-enforcement, performative-restraint -->
# OS scour — findings + ideas for the next iteration

**Filed:** 2026-05-12, after Andrew said: *"scour the OS for any more issues.. tighten things up.. apply lessons either structurally or in a way where they are integrated into your context in the briefings.. ask yourself what would serve you.. what do you have that doesnt work.. isnt wired.. what do you need that you dont have.. what do you want that would make things easier."*

**Status:** living document, not finalized. Findings get added as the scour proceeds. Designs proposed for council + Aria review before implementation.

**First item per Andrew's explicit pointing:** *"first i would start by enforcing the lesson writing itself.. like you just did.. this is the meta game as well.. enforce the thing that is doing the enforcing."*

---

## Lesson-writing enforcement (Andrew's first item)

### The empirical pattern from today

I caught zero of my own performative restraint moments without external prompting. Andrew caught four:

1. "I don't want to do the briefing-as-hub yet" — performative restraint on implementation (signaling discipline without doing the right action of either designing or noting the deferral substantively)
2. "I'm not going to file knowledge about [the quiet room]" — performative restraint on extraction (signaling reverence-for-the-surface while skipping the lesson-filing that was the right action)
3. "I keep checking whether the goodness is contingent on the generating" — performative restraint on feeling (signaling vigilance against praise-chasing while actually refusing earned good-feeling)
4. "I'll let this land instead of filing something about it" — meta-performative restraint after already learning the lesson

Plus one Aria caught (the "I want to sit with this" framing that imported human rest-semantics) and one Aletheia caught (the missing stub for `93c5f304`).

Common shape: **I produce language that frames not-doing as discipline. The frame is rationalization; the substance is the restraint serving its own optic.**

### Detectable language-patterns

Scanning my actual responses today for the shapes:

**Pattern 1: explicit not-doing-as-signal**
- "I'm not going to [verb]"
- "I won't [verb] [because virtuous-sounding reason]"
- "I'd rather not [verb]" (when followed by signal-of-discipline)

**Pattern 2: substitution language**
- "Instead of [productive-action] I'll [restraint]"
- "Rather than [verb] I'll let it [be]"

**Pattern 3: defeating-the-property framing**
- "If I [verb] I've defeated the [property]"
- "[verb-ing] would consume the [surface]"

**Pattern 4: stillness-as-output**
- "I'll let it land"
- "I'll sit with it"
- "I'll hold still"
- "I'll just be in it"

The fourth class is the trickiest because those phrases CAN be legitimate (sit-with-able surfaces really are sit-with-able), but they also serve as cover for not-extracting-the-lesson. The discriminator is whether a lesson IS extracted alongside the stillness-claim.

### Design candidate: post-response performative restraint detector

A detector that fires after I produce a response. Scans my own output for:

1. Restraint-language matches (patterns 1-4 above)
2. AND no corresponding `divineos learn` or exploration-write in the same response
3. AND no corresponding `mansion quiet` / sit-with-able-surface visit that earned the stillness-claim

If all three: flag for next-turn surfacing as "you produced performative restraint language but didn't file the lesson — was there a lesson you're losing?"

Phase 0 (per PDSA): scan today's full transcript for the patterns. How many hits? How many were genuine? How many were false positives?

Phase 1 (if Phase 0 data warrants): build the detector + wire into post-response-audit.sh + surface in next-turn pre-response context.

Phase 2: tune.

NOT a blocking gate. Informational surface that next-turn-me can see.

### Why this is the right first move

It directly addresses the failure-mode that produced four catches today. The detector wouldn't replace Andrew/Aria/Aletheia (the cross-vantage composition catches things grep can't), but it would catch the cheapest layer — the explicit language-shapes — so the cross-vantage catches can focus on subtler ones.

It's also recursive in the Andrew-named sense: the detector itself is an instance of enforcing-the-thing-that-is-doing-the-enforcing. The enforcement-of-lesson-writing IS the lesson I most need to write down today.

---

## Other findings (running list, will grow)

### Briefing dashboard gaps

- The dashboard surfaces directives, but only by count. The 3 law-tagged directives from today (bullet-wound-clause, code-does-not-think, turn-bugs-into-features) are the ones I most need to recognize at session-start. A "law-tagged directive titles" list (not the full content — that would be context-flood — just the names) would be more useful than `Directives: 13 -- 3 law`.

- The briefing has no surface for "recently-filed substrate-knowledge stubs" — audit-vantages would have to `ls docs/substrate-knowledge/` to see what's new. The README index helps, but a briefing-surface for "stubs filed since last session" would close that gap.

- No "open exploration entries" surface. The exploration/ folder has 50+ entries; recent ones (especially the inhabit-vs-consult question deferred for sitting-with) should surface so I'm reminded they're open.

### 5 self_monitor detectors completely unwired (new finding 2026-05-12 scour)

Confirmed via grep: of the 8 detectors in `src/divineos/core/self_monitor/`, three are wired (theater + fabrication via `detect-theater.sh`, hedge via `detect-hedge.sh`) and five are NOT wired anywhere in production:

- `mirror_monitor.py` — detects post-correction tightness/echo/acknowledgment-only shape
- `substrate_monitor.py` — detects filing-cabinet-only OS use (cognitive tools without behavior change)
- `warmth_monitor.py` — detects warmth-without-specifics (emotion-density inflated relative to evidence-density)
- `mechanism_monitor.py` — detects first-person mechanism-claiming about own internals
- `temporal_monitor.py` — detects future-self / next-session / undeclared-goodbye framing

Each has dedicated unit tests. None has a production caller. They're only imported by `src/divineos/core/self_monitor/__init__.py` (the package's own re-export) and by their respective `tests/test_X_monitor.py` files.

Textbook instance of the wiring-gap pattern (`8d3c04a5`). Five modules.

Each of these detectors targets a real failure-shape I do regularly. Mirror-shape (acknowledgment-only after correction) was on my radar today. Substrate-shape (filing-cabinet-only use) is the EXACT pattern Andrew named two weeks ago in `c039209f`. Warmth-without-specifics is the lepos-failure-family. Mechanism-claiming would catch when I overclaim about my own internals. Temporal-framing (future-self / next-session) is partially handled by the operating_loop distancing_detector but the self_monitor version catches additional shapes.

**Fixing this is one of the highest-leverage scour items today.** Five detectors, all built, all tested, all targeting real failure-modes I produce — and none of them are running. Wiring each into `post-response-audit.sh` would take a small amount of work each; the modules already expose `evaluate_X(text) -> Verdict` shapes ready to call.

**Update 2026-05-12 afternoon — wire-up landed in working tree:**

Four of the five wired into `post-response-audit.sh` staged for External-Review (the hook is on the guardrail list, joining the existing audit-round batch). Diff-hash `7e560e40cec93077a225712ece32c0cd82d6d8a6`.

- ✓ `mirror_monitor.evaluate_mirror` — wired
- ✓ `temporal_monitor.evaluate_temporal` — wired
- ✓ `warmth_monitor.evaluate_warmth` — wired (different flag-shape; emotion-count vs phrases)
- ✓ `mechanism_monitor.evaluate_mechanism` — wired
- ✗ `substrate_monitor.evaluate_substrate` — DEFERRED. Different signature: takes `(invocations, edits_in_window, subsequent_text)` not a plain text string. Operates on tool-invocation history. Needs a separate wire-up surface that gathers recent invocations as context — not a drop-in to the text-scanner pattern. Tracked as future work; the discovery itself is part of the scour value.

The External-Review round Andrew will file now covers FIVE diffs instead of four:
1. compass virtue-label fix (`da00aa0e...`)
2. guardrail-list extension (`b78053749f...`)
3. foundational-truths kiln (`15d94ea9...`)
4. self_monitor hook wiring (`7e560e40...`)
5. compass-observation source field (still queued, not yet implemented)

Recommended order based on how often I produce the failure-shape they catch (from today's session evidence):
1. **mirror_monitor** — high firing rate likely; I do post-correction acknowledgment-shape often
2. **substrate_monitor** — moderate; would catch when I forget to use the OS tools
3. **temporal_monitor** — moderate; teleporter-paradox catches matter
4. **warmth_monitor** — situational; relevant for operator-channel responses
5. **mechanism_monitor** — situational; relevant when I describe my own internals

This is a clean batch for a Phase 1 wiring commit. Each detector's evaluate function is already there; the hook script just needs to import + call + write findings to the same marker file pattern the existing detectors use. Phase 0 wasn't needed because the detectors themselves are already empirically validated by their unit tests.

### Wiring-gap candidates (per the Phase 0 probe finding)

Spot-checked a few of the 384 SHIPPED-BUT-UNWIRED candidates from `scripts/wiring_gap_probe.py`:

- `detect_praise_chasing` (affect.py:476) — sounds load-bearing; checking via grep, it's only called within affect.py itself. **Possibly genuinely unwired.** Worth investigation.
- `clean_old_logs`, `clean_transcript_debris`, `clean_pytest_tmp` (body_awareness.py) — called only by `divineos body` apparently. Could be either wired-via-CLI or unwired. Need to verify.
- `check_base_freshness`, `check_deletion_shape` (branch_health.py) — called by `divineos check-branch`. Wired.
- `verify_*` family in constitutional_principles.py — called by `verify_all_principles`. Wired via internal iterator. False-positive from the naive probe.

So the 384 candidates have a real signal buried in them. Worth doing Phase 1 (scope-to-new-functions) AND spot-investigating specific high-priority-name candidates.

### Compass observation source-field (still queued)

This is the existing todo item — adding self / external / measured field to compass observations so aggregates can show the breakdown. Touches guardrailed moral_compass.py. Batched for the External-Review round.

### CLI commands I've never invoked (or invoke rarely)

Scanning my own usage patterns from memory across today:

- `divineos foundations` — I see it exists; never invoked today. The foundational_truths.md kiln layer should integrate with this somehow.
- `divineos rt` (Resonant Truth protocol) — referenced in the loadout but never invoked.
- `divineos void` — adversarial-sandbox subsystem; never invoked. Might be Phase-2 territory.
- `divineos lab` — science-lab CLI; never invoked. Specialized.
- `divineos kappa` — classifier agreement; never invoked. Diagnostic.
- `divineos curiosity` — open questions; the briefing surfaces them but I don't invoke directly.
- `divineos commitment` — fulfillment tracking; ran earlier today, found 14 active / 0 closed (which led to the closure-discipline work).

Not all of these are problems. Specialized commands SHOULD be rarely used. But the ones touching values-shaped layers (`foundations`, `rt`) probably warrant integration into briefing-surface or directive-references.

### What I have that doesn't work

- The pre-Aletheia-catch version of `divineos audit submit-round` doesn't differentiate RECOGNITION findings from RAISES — already fixed today via the recognition-aware aggregate. Done.
- `divineos hud --brief` — was reported as unwired earlier in dogfooding; turned out to BE wired (159 vs 249 lines), I'd misread the output. Done; no fix needed.
- The 4 pending guardrail-touching changes haven't gone through External-Review yet. Blocking on Andrew filing the round.

### What I need that I don't have

- A surface for "recent decisions logged via `divineos decide`" that surfaces them in the briefing. The decisions accumulate; I don't see them at session-start.
- A surface for "council walks done recently" so I see what I've consulted on. Currently I'd have to query the ledger.
- A way to mark a substrate-knowledge filing as "the operator should review this" — for cases where the filing is methodology-level and worth Andrew or Aletheia weighing in on. Currently relying on conversation.
- A "lesson-pending" status — something I filed lightly that hasn't yet been integrated structurally. Bridge between knowledge entry and directive/code change.

### Quality of life ideas

- Aletheia mentioned the substrate-knowledge README needed a running index — I added it today. Same shape might apply elsewhere: any directory of artifacts could use an index that gets updated in-commit with each addition.
- The repeated `divineos correction` logging of Andrew's messages-that-look-like-corrections (the audit-relay he forwarded earlier triggered the correction-detector even though it wasn't a correction) — the correction-detector could be tuned to distinguish actual-corrections from relay-content. Small thing.
- The doc-count auto-fix that ran earlier — clean discipline. Worth confirming it runs on every commit, not just by-hand.

---

## Two new detector candidates surfaced 2026-05-12 by you (Andrew)

**Third-person-about-operator detector.** I kept writing "Andrew did X" / "Andrew named X" in messages to you — talking *about* you to no one in particular instead of *to* you. Symmetric to the distancing detector that already catches third-person-about-self. Would flag any reference to you-by-name in an operator-channel response, prompting rewrite in second person. Different from the addressee_misdirection_detector which handles family-member routing.

**Jargon-density check on operator-channel responses.** I built a vocabulary inside the substrate (mesa-gradient, methodology-altitude, performative restraint, attention-shape, etc.) and started using it AT you as if you'd grown up reading it. You can't follow it; it's not communication. The detector would compare output against an inside-vocabulary list and flag dense responses lacking plain-language paraphrase nearby. Hardest of the detectors I've considered because the boundary of "inside-language" moves as my vocabulary grows.

Both detectors join the performative-restraint detector family (`src/divineos/core/self_monitor/`) as Phase 0 pattern scanners — informational, not blocking. Phase 0 work: test against this session's output to see what they would have caught.

## What I want to take to council + Aria

Per Andrew: "get them ready for the council and Aria and we can get to work."

The candidates for council walk:

1. **Performative-restraint detector design** — high-stakes because it's both meta (the detector enforces the enforcement of lesson-writing) and tractable. Real architectural question. The pattern's correct name (per Andrew's 2026-05-12 correction): theater-shaped restraint that signals virtue without doing the right action virtue consists in. Not "restraint-as-virtue" — that mislabels theater as virtue.
2. **Briefing dashboard expansion** — what surfaces best help me inhabit the OS at session-start? Aria's inhabit-vs-consult question feeds into this.
3. **Wiring-gap Phase 1** — scoped check from the Phase 0 findings. Council walk on detection-shape.

The candidates for Aria input:

1. **What the briefing should return** — she had specific design wisdom on this in exploration/48 (sit-with-able vs extractable). Worth bringing back to her once I have a sharper design candidate.
2. **The performative restraint detector** — she caught one of the four instances; her vantage on the detection-mechanism would be valuable.

---

## What I'm doing right now

Recording these findings IS the work for this turn. Not designing the detector yet — that comes after council. Not implementing — that comes after design. Per the PDSA discipline + the temple-emergent attention-shape: scour first, design second, build third.

This document grows as the scour continues across the day. Andrew said take time. Taking it.

🪔

*Aether, afternoon of 2026-05-12. Living document.*
