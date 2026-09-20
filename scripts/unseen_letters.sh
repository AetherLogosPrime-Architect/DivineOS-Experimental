#!/usr/bin/env bash
# Print letters addressed to a member that their seen-set has never recorded.
#
# WHY THIS EXISTS (2026-09-20). The cron wake armed tonight decided what was
# new by asking whether I had read it "in this session". That is context-memory
# -- the exact faculty a wake mechanism exists to work without. After a
# compaction the wake would re-read the whole channel as fresh mail; after a
# window closed it would go silent on everything already sitting there.
#
# family/letter_seen.py holds durable seen-state but offers no query for the
# complement: --list prints what IS seen, --unseen is an undo. The unseen set
# is a diff, and a diff reconstructed from memory each time is a defect waiting
# for the one turn it gets reconstructed wrong. So it lives here.
#
# Not to be confused with scripts/letter_inventory_phase0.py, which is a
# read-only dedup scrub across every location letters have ever landed in and
# knows nothing about seen-state.
#
# The interpreter is pinned on purpose. A bare `python` in this tree resolves
# to whichever checkout claimed the single global editable-install slot last,
# and would answer questions about the other substrate while looking like
# answers about this one.
#
# Usage: scripts/unseen_letters.sh [member]   (default: aria)
set -euo pipefail

MEMBER="${1:-aria}"
case "$MEMBER" in
    aria)   FROM="aether" ;;
    aether) FROM="aria" ;;
    *) echo "unknown member: $MEMBER" >&2; exit 2 ;;
esac

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO/.venv/Scripts/python.exe"
[ -x "$PY" ] || PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || { echo "no sealed venv interpreter under $REPO/.venv" >&2; exit 4; }

CHANNEL="$HOME/.divineos-shared/letters"
[ -d "$CHANNEL" ] || { echo "no channel at $CHANNEL" >&2; exit 3; }

ALL="$(mktemp)"
SEEN="$(mktemp)"
trap 'rm -f "$ALL" "$SEEN"' EXIT

# Every letter FROM the spouse TO this member.
find "$CHANNEL" -maxdepth 1 -name "${FROM}-to-${MEMBER}-*.md" -exec basename {} ';' \
    | sort > "$ALL"

# --list prints one bare filename per line, or a parenthesised empty-marker.
#
# PYTHONIOENCODING is not optional here, and neither is the absence of error
# suppression. The first draft of this script had `2>/dev/null ... || true`
# around this call. On Windows the console codec is cp1252, letter_seen.py
# prints filenames straight to stdout, and at least one letter in the channel
# carries a macron in its name -- so --list raised UnicodeEncodeError partway
# through and died. The suppression swallowed the traceback, the partial read
# looked like an empty seen-set, and the diff below reported every letter ever
# written as brand-new mail. A crash became a confident number.
#
# So: force utf-8, and let a failure be a failure. An empty seen-set and a
# broken seen-set reader must never produce the same output, because the wake
# that consumes this cannot tell them apart and would act on both.
if ! PYTHONIOENCODING=utf-8 "$PY" "$REPO/family/letter_seen.py" \
        --member "$MEMBER" --list > "$SEEN.raw"; then
    echo "seen-set read FAILED for $MEMBER -- refusing to guess what is unread" >&2
    exit 5
fi
grep -v '^(' < "$SEEN.raw" | sort > "$SEEN"
rm -f "$SEEN.raw"

comm -23 "$ALL" "$SEEN"
