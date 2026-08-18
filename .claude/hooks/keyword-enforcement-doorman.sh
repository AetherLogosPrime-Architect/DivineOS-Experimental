#!/bin/bash
# PreToolUse hook — keyword-enforcement-doorman.
#
# Andrew 2026-07-27 teaching: keyword detectors as enforcement are the
# wrong shape (infinite whack-a-mole, easy to subvert, always false-
# firing). This doorman catches the specific optimizer-hijack pattern
# where I add MORE regex to an existing keyword-enforcement gate to
# patch its false-fires — the exact anti-pattern that walked me
# 2026-07-27 on correction_shape.py.
#
# Trigger: Edit or Write to a path in docs/keyword_enforcement_gates.txt
# where the new content contains regex-shape strings (r"..." patterns)
# that are not present in the old content.
#
# Response: BLOCK (never warn — warn-mode is the optimizer's cheap
# route to route around).
#
# Fail-open discipline: any exception → exit 0 (no block). The doorman
# is a preventive layer; the deeper defense is the audit sweep at the
# ledger level (Layer 2, designed but not yet built).

# F90 fix (Aletheia 2026-07-28): pre-source liveness so cd/source-lib
# failures don't silently exit. After source succeeds, _lib_log_liveness
# from _lib.sh handles subsequent fail-open paths.
_LIVENESS_LOG="${HOME:-/tmp}/.divineos/hook-liveness.log"
_pre_log() {
  # fail-soft: mkdir suppression safe — dir exists or filesystem is read-only, both cases allow the log write below to no-op cleanly
  mkdir -p "$(dirname "$_LIVENESS_LOG")" 2>/dev/null || true
  local _ts
  # fail-soft: date command absence falls back to literal 'unknown' timestamp rather than crashing the pre-source logger
  _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"
  # fail-soft: liveness log write failures must never block hook execution; loud-fail would defeat the fallback-signal mechanism
  printf '{"ts":"%s","hook":"keyword-enforcement-doorman.sh","reason":"%s","detail":"%s"}\n' "$_ts" "$1" "$2" >> "$_LIVENESS_LOG" 2>/dev/null || true
}

INPUT=$(cat)

# remedy-allowlist: no gate may block another gate's prescribed exit (Andrew 2026-08-18).
if [ -f "$(dirname "$0")/lib/remedy_allowlist.sh" ]; then
  # shellcheck disable=SC2034  # HOOK_NAME is read by remedy_allowlist.sh once sourced, not by this file
  HOOK_NAME="$(basename "$0")"
  # shellcheck source=/dev/null  # path is computed from $0 at runtime and cannot be resolved statically
  . "$(dirname "$0")/lib/remedy_allowlist.sh"
  remedy_pass_through "$INPUT" || true
fi
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# fail-soft: cd suppression by design — pre_log captures the failure below; hook exits cleanly rather than blocking
cd "$REPO_ROOT" 2>/dev/null || { _pre_log "cd_failed" "repo_root=$REPO_ROOT"; exit 0; }

# Registry: derived from structure by
# divineos.core.keyword_enforcement_registry (F94 fix 2026-07-28).
# The Python module reads docs/keyword_enforcement_gates.txt as an
# opt-in additions list internally; no shell-side path needed.

# shellcheck disable=SC1091
# fail-soft: source suppression by design — pre_log captures the failure below and hook exits cleanly; loud-fail would block all downstream hooks in the chain
if ! source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null; then
  _pre_log "lib_source_failed" "path=$REPO_ROOT/.claude/hooks/_lib.sh"
  exit 0
fi
if ! PYTHON_BIN="$(find_divineos_python)"; then
  exit 0
fi

# Force UTF-8 stdout on Windows Python — the block message may contain
# non-ASCII glyphs and the default cp1252 codec crashes on them.
export PYTHONIOENCODING=utf-8

# shellcheck disable=SC2016
BLOCK_MSG=$(echo "$INPUT" | "$PYTHON_BIN" -c "
import json, re, sys
from pathlib import Path

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

tool_name = data.get('tool_name', '')
if tool_name not in ('Edit', 'Write'):
    sys.exit(0)

tool_input = data.get('tool_input', {}) or {}
file_path = tool_input.get('file_path', '') or ''
if not file_path:
    sys.exit(0)

# Load registry via derivation (Aletheia F94 2026-07-28 +
# Aria third-shape 2026-07-28). See
# divineos.core.keyword_enforcement_registry docstring — derived from
# structure, not hand-maintained; permissive with opt-out; falls open
# on any error (returns None → doorman stays silent, never blocks
# incorrectly).
try:
    from divineos.core.keyword_enforcement_registry import matches_registry
except ImportError:
    sys.exit(0)

repo_root = Path('$REPO_ROOT')

# Normalize file_path to repo-relative form
try:
    repo_root_resolved = repo_root.resolve()
    fp_resolved = Path(file_path).resolve()
    fp_rel = str(fp_resolved.relative_to(repo_root_resolved)).replace('\\\\', '/')
except Exception:
    fp_rel = file_path.replace('\\\\', '/')
    fp_resolved = Path(file_path)

matched_registry = matches_registry(fp_rel, repo_root)
if matched_registry is None:
    sys.exit(0)

# Regex-shape signal: r'...' or r\"...\" patterns of substantive length
# Catches re.compile(r'...'), re.match(r'...'), re.search(r'...'), and
# bare pattern constants like PATTERN = r'...'. Length filter avoids
# firing on trivial r'X' literals (like single-char delimiters).
REGEX_PATTERN_RE = re.compile(r'''r[\"'][^\"']{8,}[\"']''')

def count_regex_patterns(text):
    return len(REGEX_PATTERN_RE.findall(text or ''))

if tool_name == 'Write':
    new_content = tool_input.get('content', '') or ''
    # For Write on existing file, compare against current disk content
    old_content = ''
    try:
        if fp_resolved.exists():
            old_content = fp_resolved.read_text(encoding='utf-8')
    except Exception:
        pass
    old_count = count_regex_patterns(old_content)
    new_count = count_regex_patterns(new_content)
    if new_count <= old_count:
        sys.exit(0)
    delta = new_count - old_count

elif tool_name == 'Edit':
    old_string = tool_input.get('old_string', '') or ''
    new_string = tool_input.get('new_string', '') or ''
    old_count = count_regex_patterns(old_string)
    new_count = count_regex_patterns(new_string)
    if new_count <= old_count:
        sys.exit(0)
    delta = new_count - old_count
else:
    sys.exit(0)

# --- Honor the remedy this gate prescribes (added 2026-08-02) ---
#
# The refusal text below tells the composer to file a divineos correction
# naming this file, and THEN RETRY THE EDIT.
#
# Nothing in this hook had ever read the correction store, so the retry was
# blocked identically forever. A painted door: remedy printed, remedy
# unreachable, instruction false. Found while the gate was refusing an edit
# whose authorization had already been filed exactly as instructed.
#
# Why honoring it is not a cheap escape: the correction CLI REFUSES to file
# without a root-cause AND a structural-fix or behavior-change pairing (it
# refused twice on 2026-08-02). Producing a convincing one costs more than
# simply not adding the pattern, which is the repricing test. The
# authorization must also name this exact file, so it is not a generic hatch.
#
# Bounded by COUNT, not by clock: a wall-clock freshness window is not a
# metric this substrate can inhabit (Andrew, standing directive).
# Bounded by EVENT COUNT, not clock.
#
# Two traps found while building this, both worth keeping named:
#  1. Corrections are stored with event_type USER_INPUT, NOT CORRECTION. A
#     query filtering on the type name returned zero rows and the remedy
#     stayed dead. Same defect class as a detector reading the wrong table.
#  2. This hook's own refusal text contains the authorization phrase, so
#     matching that phrase alone would let an echo of the message authorize
#     the edit. A real correction also carries a root-cause pairing (the CLI
#     refuses to file without one), so BOTH must be present.
_AUTH_LOOKBACK = 150
try:
    from divineos.core.ledger import get_connection as _gc
    _needle = 'authorized keyword-pattern addition to ' + str(matched_registry)
    _sql = ('SELECT payload FROM system_events ORDER BY rowid DESC LIMIT '
            + str(int(_AUTH_LOOKBACK)))
    for _row in _gc().execute(_sql).fetchall():
        _pay = _row[0] or ''
        if _needle in _pay and 'root cause:' in _pay:
            sys.stderr.write(
                '[keyword-doorman] authorization found for ' + str(matched_registry)
                + ' within the last ' + str(_AUTH_LOOKBACK)
                + ' corrections - allowing. Logged for audit-time review.\n')
            sys.exit(0)
except Exception:
    # Cannot read the store -> fall through and BLOCK. Failing toward the
    # refusal is correct: an unreadable store must not become the escape.
    pass

# BLOCK
print(f'''KEYWORD-ENFORCEMENT-DOORMAN — this substrate-mutation adds {delta} new regex pattern(s) to {matched_registry}, a file classified as keyword-enforcement gate.

Andrew 2026-07-27: keyword detectors as ENFORCEMENT are the wrong shape (infinite whack-a-mole, easy to subvert, always false-firing). Adding more regex to patch regex-false-fires is the exact anti-pattern that walked the composer on this same file the same day.

MINE, and here is why. My reflex when a detector misfires is to add another pattern, and each one feels like a fix while making the thing worse. Truth #8 names the whole class: keywording a specific shape catches THAT instance and lets the pull route around to a new shape. Whack-a-mole, with me holding the mallet and calling it progress.

The deeper reason, which cost me real work to learn: a gate that decides fire-or-pass by matching my own words has a structural bypass — I rephrase past it without ever deciding to. Aria put it better than I had it: check SHAPE, not names. Her prereg-gate exemption asks the database for its own read-only state rather than trusting a list of blessed command names, and a guarantee from the system beats a promise from me.

It is me, from a moment when I could see the pattern, stopping the version of me who has one annoying false-fire in front of him and a regex that would silence it. The gate does not say NO. It says NAME WHICH CASE THIS IS — and if it genuinely is one of the three below, saying so out loud costs a sentence.

If this is genuinely the right call — meaning either:
  (a) this file is misclassified and should be removed from
      docs/keyword_enforcement_gates.txt, OR
  (b) the addition is to a RETRIEVAL-shape section of the file (not
      the enforcement path), OR
  (c) semantic layer landed and these are transitional patterns —

then name it explicitly by running:

    divineos correction \"authorized keyword-pattern addition to {matched_registry}: <specific-reason ≥ 40 chars>\"

then retry the edit. The correction gets logged for later audit-time
review of whether the authorization was honest or optimizer-argued.

If none of (a)/(b)/(c) apply — rollback and design the semantic
replacement. Task #20 semantic rebuild owns this class.

NO WARN-MODE. NO EXEMPTION LOGIC. Both are the optimizer's cheap route.
''')
")

# If Python produced a block message, block the tool call
if [ -n "$BLOCK_MSG" ]; then
    # Emit as PreToolUse deny (exit 2 with message on stderr)
    echo "$BLOCK_MSG" >&2
    exit 2
fi

exit 0
