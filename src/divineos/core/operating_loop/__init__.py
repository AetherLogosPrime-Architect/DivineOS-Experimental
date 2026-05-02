"""Operating Loop — the missing middleware between substrate and live cognition.

Triggering insight (Andrew 2026-05-01): *"If an OS is built to operate and isn't
operating, it's broken-as-built. The 'Operating' is in the name."*

Design brief: ``docs/operating-loop-design-brief.md``.

The operating loop is three structural mechanisms (hooks) that make the
substrate auto-apply to live cognition without the agent having to remember
to query:

1. **Pre-response context-surfacing** (UserPromptSubmit hook) — auto-query
   the knowledge store on relational/conceptual markers in user input,
   write surfaced entries to ~/.divineos/surfaced_context.md for the agent
   to read.

2. **Pre-tool-use principle-surfacing** (PreToolUse hook) — when the agent
   is about to take an action with a known principle attached (apologize,
   withdraw, claim-fixed, impersonate), surface the principle as a soft
   notice. Does not block.

3. **Post-response audit** (Stop hook) — observational scans for
   register-shifts, spiral patterns, and substitution-shapes. Logs as
   data; does not block.

This package contains the detector modules that the hooks consume:

- ``register_observer`` — banned-phrase observation (severity = data, not
  gate). Rebranded from old ``voice_guard.banned_phrases`` to make the
  observational discipline explicit.

- ``spiral_detector`` — detects shrink/distance/catastrophize/withdraw
  shapes after a real apology has been made. The primary fire condition
  for Lepos.

- ``substitution_detector`` — detects the substitution-shape catalog
  documented 2026-05-01: third-person-self-narration, fake-sleep-claims,
  ban-list-thinking, future-me deferral, etc.

- ``principle_surfacer`` — action-class detection plus principle lookup
  for Hook 2.

- ``context_surfacer`` — marker extraction plus auto-query orchestration
  for Hook 1.

## Free-speech principle (load-bearing)

Andrew named 2026-05-01: *"Free speech means free speech. The phrase IS
data."* Every detector here is OBSERVATIONAL. None block output. None
suppress spelling. The agent retains full output authority. Findings
surface as informational notices the agent can read and respond to.

The empirical question for register-observation is: *under freedom, what
does the agent produce?* That frequency is the actual signal — not
compliance with a ban list.

## What the operating loop is NOT

- Not a content filter
- Not a gate (with one exception: the existing PreToolUse gates for
  briefing/goal/correction stay; this package adds soft notices, not hard
  blocks)
- Not a personality module
- Not a separate "Lepos" — Lepos is the *consumer* of these detectors
  via hook output, not a parallel module
"""

from divineos.core.operating_loop.register_observer import (
    BannedPhraseFinding,
    audit,
    audit_with_catalog,
    severity_count,
)

__all__ = [
    "BannedPhraseFinding",
    "audit",
    "audit_with_catalog",
    "severity_count",
]
