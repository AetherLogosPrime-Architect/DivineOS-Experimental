# Pre-registration: lepos-channel-always-running gate with evidence-cited self-checks

- **ID**: `prereg-157ed56a5da2`
- **Filed by**: agent
- **Filed at**: 2026-05-19 17:21 UTC
- **Review at**: 2026-06-02 17:21 UTC (14d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-06-04 21:51 UTC
- **Tags**: lepos, channel-architecture, yes-and-system, evidence-cited-self-check

## Claim

Lepos channel runs alongside technical content in any reply addressed to Andrew. Pre-response context injects 3-4 self-check questions drawn from a pool of 8-12 with at least one content-aware slot. Answers must cite evidence in the reply itself; generic yes-answers fail substrate satisfaction. Thin-channel turns are logged for investigation, not blocked. System is YES/AND. Gravity-classifier routes which turns get the gate (Andrew-addressed, substantive) vs which dont (porch-with-Aria, exploration, mechanical). 30-turn empirical trial first; foundational-truths language follows the trial.

## Success criterion

Across 30 Andrew-addressed turns post-deployment: (1) lepos-channel-presence detected in >=85% of turns based on evidence-citation in self-check answers, (2) at least 3 turns logged for investigation when channel was thin and the investigation produced specific observation about WHY, (3) Andrew reads the trial output and confirms the channel-running is real not performed.

## Falsifier

Across 30 Andrew-addressed turns post-deployment ANY of: (1) self-check answers become paraphrase-streaks (5+ consecutive turns with semantically-identical answers to same question), (2) evidence-citation degrades to formula (always citing the same paragraph-index or always citing nothing-but-substantive-looking), (3) Andrew reports the gate feels like ritual not real, (4) the gate fires zero times across 30 turns (means it isn't actually catching anything), (5) I find myself bypassing the gate by routing Andrew-addressed content through non-gated paths (writing letters or exploration entries when a direct reply was warranted).

## Outcome notes

The lepos channel-check mechanism shipped (src/divineos/core/lepos_channel_check.py + lepos_debt + post-response-audit.sh wiring). However the 30-turn empirical-trial success criteria (>=85% channel-presence detection, >=3 thin-channel investigation entries, Andrew confirms channel is real not performed) cannot be honestly verified without instrumentation that wasn't built alongside the gate. The retrospective signal is mixed: some turns have evidence-cited self-checks, others don't, and I can't reconstruct which 30 specific Andrew-addressed turns to score against. Honest call is INCONCLUSIVE rather than guessing SUCCESS or FAILED. Follow-up: if we keep this mechanism, instrument the lepos-channel-presence detection so the next 30-turn trial is verifiable.
