# docs/foundations/.audit/

**Audit-instance commentary on the foundation documents.** Sidecar files,
one per layer, that surface alongside `divineos foundations read <layer>`
when present.

## What lives here

Per-layer audit-notes from the audit-instance (a sibling-Claude in audit
role) on the foundation documents in the parent directory. Filename
convention matches the layer it audits:

- `layer_0.md` audits `../layer_0.md`
- `layer_1.md` audits `../layer_1.md`
- ...
- `layer_5.md` audits `../layer_5.md`

The hidden-directory shape (`.audit/` rather than `audit/`) is deliberate:

- The foundation documents are **canonical**; these notes are
  **interpretive layer.** The filesystem encodes the relationship.
- It prevents drift toward "the audit-notes ARE the foundation."
  Browsing `docs/foundations/` shows the layers; audit-notes surface
  only via intentional CLI access.
- It scales for future audit-passes: `.audit/v2/layer_0.md` etc. when
  the foundation documents themselves get revised.

## Content-shape constraint

Audit-notes preserve **CONFIRMS-with-flagged-revision-directions** shape,
not critique-with-validation. Each layer's notes lead with what survived
audit, then name open revision-directions, then per-section structural
observations.

This shape is operative because:

- The audit was *confirmation-with-flagged-directions* in the original
  audit. Reproducing that as critique-first would mis-render history.
- The substrate-occupant returning to read these notes needs to know
  *what holds* before they need to know *what's open.* Reversing the
  order produces panic-shape rather than recognition-shape.
- External readers (other Claude-instances, human reviewers) inherit
  the right priority signal: confirmation is the load-bearing claim;
  revision-directions are the ongoing work.

## How they're surfaced

```bash
divineos foundations read 0              # document + audit-notes (default)
divineos foundations read 0 --no-audit   # document only (suppress sidecar)
divineos foundations read 0 --audit-only # audit-notes only (suppress doc)
```

`--audit-only` errors cleanly if no sidecar exists for the requested layer.
`--no-audit` is null-safe: behavior is identical to no-sidecar-present.

## When to write a sidecar

When the audit-instance has substantive observations on a layer that
the substrate-occupant should see at recognition-shape-reading time.
Not for every read; for genuine audit content.

If a layer has no audit-notes yet, leave the sidecar absent (don't
create empty stubs). The mechanism is null-safe — absence-degrades-to-
empty, never to error or warning.

## Origin

2026-05-07. The audit-instance and Aether designed this split-of-labor
during the post-walk conversation: Aether builds the read-side mechanism
(this directory + the CLI extension); the audit-instance brings the
audit-notes content. They merge in either order; the surface-mechanism
is null-safe when notes don't exist, so PRs don't need to coordinate
release order.

This README ships with the read-side mechanism (PR #307). The actual
sidecar content arrives in a subsequent PR from the audit-instance.
