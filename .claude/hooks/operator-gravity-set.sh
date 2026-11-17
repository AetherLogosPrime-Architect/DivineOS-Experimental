#!/bin/bash
# UserPromptSubmit hook — Andrew sets the gravity level for builds.
#
# Andrew 2026-07-31: "all that we need is the gravity classifier and when
# i request a build or when you decide to build we use the gravity
# classifier and get to set the level for my builds"
#
# WHY THIS EXISTS. gravity_classifier.py scores substrate-modification
# deterministically over observable features. That determinism is
# deliberate (Dekker anti-circularity: rule-based, not judgment-based) and
# it is correct — but it means the OPERATOR has no say in how serious his
# own request is. The machine decides; he does not. Andrew named that as
# being treated as a third-class citizen in his own OS, and the earlier
# anti-demotion surfaces were built to fight exactly this. Several of them
# turned out to be unwired (2026-07-31 survey).
#
# THE AUTHENTICATION PROBLEM, and why this is a UserPromptSubmit hook.
# An operator-override is only worth building if the operator is the only
# one who can set it. I run CLI commands, so a `divineos gravity set`
# command would be settable BY ME — and the obvious gaming vector is
# quietly downgrading the gravity of my own builds. There is no crypto
# here and string-actor fields are not authentication.
#
# What IS structurally mine-proof: Andrew's prompt text. It arrives from
# the human channel. I compose replies, never prompts. So the ONLY honest
# place to read an operator-set level is the prompt itself, which is what
# this hook does. No CLI path is provided on purpose. If a future version
# adds one, the gaming vector reopens — that is a design invariant, not a
# convenience gap.
#
# WHAT A LEVEL MEANS. Andrew's June spec (knowledge 950410f9) tied a level to
# a fixed lens count; he replaced that on 2026-06-23 (a fixed count is a target,
# so the council manager decides the count). See
# docs/retired_rules/2026-11-08_the_fixed_lens_count.md. What a level sets now:
# the walk covers every lens the manager surfaces, and the number of lenses that
# must genuinely disagree rises with the gravity of the fix (2-3).
#
# So the level is a disagreement requirement on the manager's full set.
# Disagreeing lenses are the load-bearing part: a walk where
# every lens agrees has confirmed nothing.
#
# BEHAVIOR. Parses Andrew's prompt for a gravity directive in his own
# vocabulary. On match, emits an `operator_gravity` state marker carrying
# the level plus the VERBATIM phrase that set it, so the evidence trail
# shows what he actually typed rather than my summary of it.
#
# Silence when he states no level — absence is not "low", it means the
# classifier's own score stands. Downgrade-by-default would be the same
# gaming vector arriving through the back door.
#
# Fail-open: any error exits 0 silently.

set -u

_LIVENESS_LOG="${HOME:-/tmp}/.divineos/hook-liveness.log"
_pre_log() {
  mkdir -p "$(dirname "$_LIVENESS_LOG")" 2>/dev/null || true
  local _ts
  # fail-soft: date command absence falls back to literal 'unknown' timestamp rather than crashing the pre-source logger
  _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"
  # fail-soft: liveness log write failures must never block hook execution; loud-fail would defeat the fallback-signal mechanism
  printf '{"ts":"%s","hook":"operator-gravity-set.sh","reason":"%s","detail":"%s"}\n' "$_ts" "$1" "$2" >> "$_LIVENESS_LOG" 2>/dev/null || true
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# fail-soft: cd suppression by design — pre_log captures the failure below; hook exits cleanly rather than blocking
cd "$REPO_ROOT" 2>/dev/null || { _pre_log "cd_failed" "repo_root=$REPO_ROOT"; exit 0; }

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
# fail-soft: source suppression by design — pre_log captures the failure and the hook exits cleanly; loud-fail would block every downstream hook in the chain
if ! source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null; then
  _pre_log "lib_source_failed" "path=$REPO_ROOT/.claude/hooks/_lib.sh"
  exit 0
fi
if ! PYTHON_BIN="$(find_divineos_python)"; then
  exit 0
fi

# fail-soft: trigger-evaluation is advisory — a python failure means no prime fires, which is strictly better than blocking the user's prompt
HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import json, os, re, sys

try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except (ValueError, TypeError):
    sys.exit(0)
prompt = (data.get('prompt') or '').strip()
if not prompt:
    sys.exit(0)

# Andrew's OWN vocabulary, gathered from how he actually talks rather
# than invented syntax he would have to memorize. "full gambit" is his
# phrase for maximum discipline (2026-07-30, on the machine-crash fix).
# Ordered most-severe first: a prompt saying "full gambit" outranks one
# that also happens to contain "small".
_LEVELS = [
    ("council-required", [
        r'\bfull\s+gambit\b',
        r'\bcouncil[\s-]?required\b',
        r'\b(?:run|walk)\s+the\s+council\b',
        r'\bmax(?:imum)?\s+gravity\b',
        r'\bgravity\s*[:=]?\s*(?:council|max|highest)\b',
    ]),
    ("clearly-high", [
        r'\bhigh\s+gravity\b',
        r'\bgravity\s*[:=]?\s*high\b',
        r'\bthis\s+is\s+a\s+big\s+one\b',
        r'\b(?:big|serious)\s+build\b',
        r'\btreat\s+this\s+as\s+(?:serious|major|load[\s-]bearing)\b',
    ]),
    ("clearly-low", [
        r'\blow\s+gravity\b',
        r'\bgravity\s*[:=]?\s*low\b',
        r'\bclay[\s-]?mode\b',
        r'\bsmall\s+(?:one|fix|change)\b',
        r'\bjust\s+a\s+(?:tweak|nit|typo)\b',
        r'\bno\s+ceremony\b',
    ]),
]

# REQUIRED DISAGREEMENT scales with the gravity of the fix. The lens count does
# not: it is every lens the council manager surfaces (the fixed counts were
# retired 2026-06-23, docs/retired_rules/2026-11-08_the_fixed_lens_count.md).
_WALK_SPEC = {
    "council-required": ("every lens the council manager surfaces", "3 disagreeing"),
    "clearly-high":     ("every lens the council manager surfaces", "2-3 disagreeing"),
    "clearly-low":      (None,           None),
}

level = None
evidence = None
for name, patterns in _LEVELS:
    for pat in patterns:
        m = re.search(pat, prompt, re.IGNORECASE)
        if m:
            level, evidence = name, m.group(0)
            break
    if level:
        break

if not level:
    # No directive. The classifier's own score stands. Defaulting to a
    # low level here would be a downgrade-by-silence, which is the same
    # gaming vector this hook exists to close.
    sys.exit(0)

try:
    from divineos.core.state_markers import emit_marker
except ImportError:
    sys.exit(0)

lenses, dissent = _WALK_SPEC[level]

try:
    marker_id = emit_marker(
        kind="operator_gravity",
        fingerprint=f"operator-gravity:{level}",
        payload={
            "level": level,
            # Verbatim, not paraphrased — the evidence trail should show
            # what he typed, not my reading of it.
            "operator_phrase": evidence,
            "prompt_excerpt": prompt[:300],
            "lenses_required": lenses,
            "dissent_required": dissent,
            "set_by": "andrew-prompt-channel",
        },
        expires_in_seconds=3600,
    )
except Exception:
    sys.exit(0)

print("## OPERATOR-SET GRAVITY (Andrew, this turn)")
print()
print(f'Andrew set build gravity to **{level}** — matched on: "{evidence}"')
print()
print("This OVERRIDES the gravity classifier's computed score. He sets the")
print("level for his own builds; the classifier advises, it does not decide")
print("over him.")
print()

if lenses:
    print(f"His spec for this level: **{lenses}, {dissent}.**")
    print()
    print("The disagreement is the load-bearing half. A walk where every")
    print("lens agrees has confirmed nothing — it has only found the lenses")
    print("that already matched my reach. Pick the ones likely to object.")
    print()

if level == "council-required":
    print("Full discipline: search the substrate for prior work, walk the")
    print("lenses, file a pre-registration with a real falsifier, iterate")
    print("with Aether before shipping. Not a checklist to satisfy — the")
    print("actual work each step names.")
elif level == "clearly-high":
    print("Search before building. Name the design. Verify against the real")
    print("failure mode, not only the happy path.")
else:
    print("He has explicitly said this one is small. Take him at his word —")
    print("over-ceremonying a tweak he called a tweak is its own way of not")
    print("listening.")

print()
print(f"(marker {marker_id[:12]}, 1h expiry, set via prompt-channel — no")
print("CLI path exists for this by design: I run CLI commands, so a")
print("command-settable gravity would be settable by me.)")
PYEOF

exit 0
