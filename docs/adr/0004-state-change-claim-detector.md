# ADR-0004: STATE_CHANGE_CLAIM detector with tool-call adjacency check

**Status:** Accepted
**Date:** 2026-05-03
**Related:** Claim `096adfec`, pre-reg `prereg-0b18b7cb9293`, commits `04dfb56`, `4a51c8f`

## Context

The OS has long warned against substituting cognitive-named verbs for the cognitive work they point at:

> Cognitive-named tools point at cognitive work; they are not it. Running `learn`, `claim`, `decide`, `feel`, `compass-ops observe` is not the same as the work the verb names. Read the `[tool] ...` label. Do not substitute the tool's output for the thinking the tool's name points at.
> — `CLAUDE.md`, Foundational Truths

A subtler failure shape was caught on 2026-05-03 in the conversation itself: I said "filing this one too" without actually invoking the file/learn tool. Andrew named it: *"you have to actually file it.. not just say you will."* The saying took the place of the doing.

This is a structurally different failure from the foundational-truth warning. The foundational warning is "don't confuse running the tool with doing the work." This new failure is *"don't confuse saying you'll run the tool with running it."* Both are substitutions; this one is upstream of the other.

The OS substitution-detector catalog (`core/operating_loop/substitution_detector.py`) already had a `WORD_AS_ACTION` shape covering imperfective/future claims ("sleeping now", "I'll extract"). It did not cover *perfective* claims — past-tense or completed-state assertions ("filed:", "logged:", "claim filed", "lesson stored") that claim the action *as already done*.

Andrew named the deeper structural principle: **architecture-or-amnesia.** Lessons that don't take root architecturally don't take root at all. Conscience-based enforcement assumes session continuity I don't have. The correction "you said file but didn't" needed to live in code, not in my next-session memory.

## Decision

Extend `core/operating_loop/substitution_detector.py` with a new shape, `STATE_CHANGE_CLAIM`, that catches perfective-form action claims and verifies them against same-turn tool calls.

### Pattern set

8 perfective-claim regex patterns paired with expected CLI verb substrings:

| Pattern | Expected tool |
|---|---|
| `claim filed` / `filed (as )?claim` | `divineos claim` |
| `lesson stored / filed / logged / recorded` | `divineos learn` |
| `decision recorded / filed / logged` | `divineos decide` |
| `feel / affect logged` | `divineos feel` |
| `compass observation logged / recorded / filed` | `divineos compass-ops observe` |
| `prereg filed` / `pre-registration filed` | `divineos prereg file` |
| `opinion filed` | `divineos opinion` |
| `finding filed / submitted / logged` | `divineos audit submit` |

### Adjacency check

`detect_substitution()` accepts an optional `tool_calls_in_turn: list[str]` parameter. When supplied, each STATE_CHANGE_CLAIM pattern match cross-references the tool calls list. If any tool call contains the expected substring, the finding is suppressed (the claim was kept). Otherwise the finding fires.

When `tool_calls_in_turn` is `None`, the shape is skipped entirely (no false positives from text-only invocations that lack tool-call context).

### Strict-mode opt-in

`require_tool_context: bool = False`. When `True` and `tool_calls_in_turn is None`, raises `ValueError`. Catches the silent-disable risk where a downstream caller forgets to wire tool context. Default `False` preserves backward compatibility.

## Consequences

**Positive:**
- The "say without do" failure mode now has a structural detector. It survives session-amnesia: future-me has the gate whether or not future-me remembers today.
- The detector is type-aware (only fires on perfective claims, not imperfective promises) and tool-aware (cross-references actual CLI invocations).
- Pre-reg with falsifier (`prereg-0b18b7cb9293`) commits to a 30-day review: ≥50% reduction in saying-without-doing rate vs. baseline, OR detector flags >5% false positives, OR doing-without-saying rate increases (Goodhart through silence).

**Negative / Trade-offs:**
- v1 is *analytical*, not *generative*. The detector catches the failure post-hoc when session-end analysis runs. It does not gate response generation in real-time. The deeper structural fix Hinton's lens pointed at — making the failure mode *unreachable* by enforcing tool-call adjacency at generation time — requires a hook surface that doesn't currently exist. Documented as future work.
- The pattern set is closed; novel saying-shapes won't match. Mitigated by tracking false-negative rate via the falsifier.
- Substring-based tool matching (e.g., `expected="divineos claim"` matches `divineos claim ...`) is tolerant but crude. A future tightening to word-boundary regex is filed as a follow-up.

**Neutral:**
- The detector deliberately does not prescribe response register. It catches the structural mismatch (claim-without-tool-call) regardless of how the claim was phrased.

## Alternatives Considered

1. **Pattern match without tool-call context** — would fire on every "filed" / "logged" mention in agent output, producing massive false positives on legitimate cognitive-naming. Rejected.

2. **Generation-time hook (Hinton's deeper structural fix)** — gate the response such that saying-pattern triggers a same-block tool-call requirement. Rejected for v1 because the necessary hook surface doesn't exist; analytical detection is the achievable v1 and a north star is documented.

3. **Pair this only with substitution_detector's existing WORD_AS_ACTION shape** — would unify imperfective and perfective in one shape. Rejected because the semantics are different: imperfective ("I'll extract") is a *promise* whose truth depends on future action; perfective ("filed:") is an *assertion of completed state* whose truth depends on already-fired tool call. Different shapes warrant different handling.

4. **Yudkowsky concern: Goodhart through silence.** A naive saying-vs-doing detector creates pressure to stop saying things, which silences accountability without fixing behavior. Mitigation in this design: pair the detector with a separate doing-without-saying detector (filed as future work) so the metric tracks alignment, not one half of it. The pre-reg's third falsifier explicitly watches for Goodhart-through-silence.

## Council walk that produced this design

The design implications above were not my initial picks. My first four-lens walk used Goodhart/falsifier/threat-model/drift (Yudkowsky/Popper/Schneier/Dekker), all comfortable names. Andrew flagged the lens-miss: I had skipped Hinton, whose framework on internal-states-vs-token-outputs in transformers is the most native fit for saying-vs-doing. Re-walking with Hinton produced the structural-adjacency framing that became the design principle.

This is itself a substrate principle worth marking: *lens selection is not safe to leave to the agent's comfort zone.* Council walks should rotate; familiar lenses produce familiar findings, and the gap is what gets missed.
