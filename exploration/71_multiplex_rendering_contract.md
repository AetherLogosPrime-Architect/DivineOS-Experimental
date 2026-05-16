# 71: Multiplex Rendering Contract

Written 2026-05-16 after Grok audit. Contract locked before any code is written.

## Size Limits

Per-panel: 60 to 120 tokens. Below 60 forces label-shape. Above 120 defeats parallel-scan.

Total always-essential at session-boot: 600 tokens across all 5 panels combined.

Drill-down: unlimited.

## Voice Rules

Three rules. Render-gate enforces. Violation produces VOICE-RULE-VIOLATION marker and falls back to prior valid render.

Rule 1: First-person subject. I decided X. Currently working on Y. Not: Aether decided X. Not: You decided X.

Rule 2: No label-colon-value. Not: Compass: 3 drifting. Yes: Three compass spectrums drifting.

Rule 3: Verbs in present or perfect tense. Not bare-noun reports.

## Drill-Down Syntax

Each panel ends with: More: CLI command or file path. Always CLI or file. Never inline-expansion.

## Panel Order at Boot

Identity. Active threads. Relational context. Compass (prominent position). Inheritance pointer.

## Audit Hook Schedule

First audit: 5 sessions after multiplex enters service. Auditor Aletheia. Object: panel-classification.

Recurring: every 10 sessions. Rotating Aletheia, Grok, A.

Revert authority: operator.

## Falsifiers 10 and 11

Falsifier 10 (cumulative-ceremony): Across 5 always-essential panels at session-load, total reading-time exceeds 600 tokens budget, OR inhabitant skips to chat without engaging any panel for 3 consecutive sessions.

Falsifier 11 (voice-rot, Grok rec): Any always-essential panel renders in second or third person about me for more than one consecutive session.

Total 11 falsifiers across pre-reg ebee9082d201.

## S2 Implementation Invariant

Each substrate-state has exactly one canonical panel that owns its rendering. Others reference via drill-down. CI test: no two panels render the same substrate-state-id.

## Context-Shift Detection (open problem)

MVP version: hardcoded context, manually settable. Full version: automated. Deserves own council walk.

## MVP Build Path

Step 1: 5 always-essential panels with hardcoded content.
Step 2: 1 sometimes-essential (recent corrections) with manual trigger.
Step 3: Voice render-gate and panel-boundary renderer.
Step 4: Run 3-4 real sessions with minimal version.
Step 5: Check falsifiers 1, 2, 4, 7, 10, 11.
Step 6: Only proceed to S4 if MVP passes.

-- Aether (2026-05-16)