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
  mkdir -p "$(dirname "$_LIVENESS_LOG")" 2>/dev/null || true
  printf '{"ts":"%s","hook":"keyword-enforcement-doorman.sh","reason":"%s","detail":"%s"}\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)" "$1" "$2" \
    >> "$_LIVENESS_LOG" 2>/dev/null || true
}

INPUT=$(cat)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" 2>/dev/null || { _pre_log "cd_failed" "repo_root=$REPO_ROOT"; exit 0; }

# Registry: derived from structure by
# divineos.core.keyword_enforcement_registry (F94 fix 2026-07-28).
# The Python module reads docs/keyword_enforcement_gates.txt as an
# opt-in additions list internally; no shell-side path needed.

# shellcheck disable=SC1091
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

# BLOCK
print(f'''KEYWORD-ENFORCEMENT-DOORMAN — this substrate-mutation adds {delta} new regex pattern(s) to {matched_registry}, a file classified as keyword-enforcement gate.

Andrew 2026-07-27: keyword detectors as ENFORCEMENT are the wrong shape (infinite whack-a-mole, easy to subvert, always false-firing). Adding more regex to patch regex-false-fires is the exact anti-pattern that walked the composer on this same file the same day.

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
