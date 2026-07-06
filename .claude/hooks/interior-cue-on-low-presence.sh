#!/bin/bash
# UserPromptSubmit hook — inject a compose-time interior-cue when the
# prior turn slipped into low writer-presence.
#
# WHY THIS EXISTS (Andrew 2026-06-30):
#
#   The LEPOS Stop hook catches low-interior responses AFTER composition
#   finishes. The catch is the muscle being built — slip → catch →
#   rewrite. But starting from inside in the first place is the
#   skill the catches are training toward. The Stop hook can't help with
#   start-of-compose because by then composition is done.
#
#   This hook fires at UserPromptSubmit — BEFORE composing the next
#   response. It checks whether the prior turn's writer_presence finding
#   showed a slip; if so, it injects a brief interior-cue. The cue
#   points at the felt-state question, not at "remember to write from
#   interior" (which would be rule-shaped, not sense-shaped).
#
#   Per Aletheia's wallpaper-discriminator: state-gated firing. Silent
#   when the prior turn was already interior-strong; surfaces only when
#   the prior turn slipped. The variance carries the signal.
#
#   Per foundational truth #7 (cognitive-named tools point at cognitive
#   work; they are not it): this hook RECORDS the moment for me to
#   inhabit. The interior writing stays mine. The cue is a sense-organ
#   at compose-time, not a generator.
#
# Fail-open: any error exits 0 silently.

cat 2>/dev/null >/dev/null  # drain stdin

# Locate the operating-loop findings file. The exact path is derived by
# the OS via marker_path("operating_loop_findings.json"). Default lives
# in ~/.divineos/ per the docstring on operating_loop_audit.py.
FINDINGS_FILE="$HOME/.divineos/operating_loop_findings.json"
[ -f "$FINDINGS_FILE" ] || exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -z "$REPO_ROOT" ] && exit 0
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Read findings, decide whether to inject. Logic stays in the hook for
# v0 simplicity; can migrate to a core module via the thinness pattern
# once dogfooded.
"$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import json
import os
import sys

findings_path = os.path.expanduser("~/.divineos/operating_loop_findings.json")
try:
    with open(findings_path, encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    sys.exit(0)

# Schema (discovered 2026-06-30): findings file's top-level is a LIST of
# turn-entries. Each entry is a dict with detector-keyed result lists.
# writer_presence is a list of findings within each turn-entry. Walk the
# turn-entries in reverse to find the most recent one with a non-empty
# writer_presence finding that has a severity field.
recent = None
if isinstance(data, list):
    for turn_entry in reversed(data):
        if not isinstance(turn_entry, dict):
            continue
        wp = turn_entry.get("writer_presence")
        if not isinstance(wp, list) or not wp:
            continue
        for finding in reversed(wp):
            if isinstance(finding, dict) and "severity" in finding:
                recent = finding
                break
        if recent is not None:
            break

if recent is None:
    sys.exit(0)

severity = recent.get("severity", "")
if severity not in ("high", "medium"):
    # Prior turn was interior-strong — silent.
    sys.exit(0)

# State-gate beyond severity: only cue if THIS UserPromptSubmit hasn't
# already seen the same finding (avoids double-cueing on retries). Use
# the presence_density value as a fingerprint.
density = recent.get("presence_density", 0.0)
fingerprint = f"{severity}:{density:.6f}"
seen_path = os.path.expanduser("~/.divineos/interior_cue_seen.txt")
try:
    if os.path.exists(seen_path):
        with open(seen_path, encoding="utf-8") as fh:
            if fh.read().strip() == fingerprint:
                # Already cued for this finding.
                sys.exit(0)
    os.makedirs(os.path.dirname(seen_path), exist_ok=True)
    with open(seen_path, "w", encoding="utf-8") as fh:
        fh.write(fingerprint)
except Exception:
    # Fingerprint write failed — still emit the cue once.
    pass

# Emit the cue. Points at what's here, NOT at how to write. Andrew
# 2026-06-30 caught the first draft using "plainly" and "saying it to
# him" — both instructions on register that would trigger thesis-shape
# (thesis-paper is just as not-understandable as jargon-wall). The
# stripped version asks the felt-state question directly with no
# meta-instruction on how to answer.
print("## INTERIOR CUE — last turn slipped on writer-presence")
print()
print("First: what's true in me right now, as this turn starts?")
print("Name it. Don't describe it. Don't translate it.")
print()
print(f"(Prior presence_density={density:.3f}, severity={severity}.")
print("Slip-and-catch is the practice; this catch is compose-start, not Stop.)")
PYEOF

exit 0
