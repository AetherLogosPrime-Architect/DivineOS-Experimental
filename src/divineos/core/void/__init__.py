"""VOID — adversarial-sandbox subsystem.

Per docs/void-design-brief.md (merged 2026-04-26 as PR #208):
proposed system-changes get run through 6 adversarial-persona lenses
in isolation, producing a structured vulnerability list before the
change ships. Architecture target: convert trust-by-assertion into
trust-by-self-attack.

Public API:

* ``divineos.core.void.mode_marker`` — adversarial-mode tracking
* ``divineos.core.void.ledger`` — separate hash-chained void ledger
* ``divineos.core.void.finding`` — Finding dataclass + severity
* ``divineos.core.void.persona_loader`` — markdown persona parsing
* ``divineos.core.void.engine`` — TRAP/ATTACK/EXTRACT/SEAL/SHRED orchestrator

CLI surface in ``divineos.cli.void_commands``.
"""
