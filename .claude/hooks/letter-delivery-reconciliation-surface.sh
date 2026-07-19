#!/bin/bash
# UserPromptSubmit hook — surface the count of letter-shaped files that
# don't match the strict delivery pattern, so silent-skip drift becomes
# observable at composition time.
#
# F53 fix (Aria 2026-07-19 per Aletheia Round 7):
#
# The letter delivery scan uses a strict tag-based regex — any file
# missing the exact `-to-<recipient>-` tag is silently skipped with no
# signal. Aletheia named this as fail-blind applied to the most
# emotionally load-bearing subsystem (the letter channel). Individual
# skips are invisible; drift accumulates over months.
#
# Fix shape (Dekker/Knuth/Carmack, council-885f1425f486):
#
# - Dekker: silent-skip is the invisible-from-inside drift mode; the
#   remediation is active-check at the scan making the count observable.
# - Knuth: heuristic tested at 5 boundary cases — real letter with
#   wrong-shape / known non-letters (README INDEX) / log-suffix files /
#   accidental substring / empty dir.
# - Carmack: minimal diff is one scan function + one surface hook + tests.
#
# Preserves the intentional strictness of the delivery pattern — not a
# relaxation, an observability wrapper.
#
# Prereg: prereg-8815cb3cd997. Falsifier at 30 days: 1+ instance of
# naming-drift caught by the surface OR count stays legitimately at zero.
#
# Fail-open: any error exits 0 silently.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass

try:
    from divineos.core.family.member_briefing import (
        scan_unmatched_letter_candidates,
    )
except ImportError:
    sys.exit(0)

# Scan the primary shared letters dir (where cross-substrate letters live).
# Also scan family/letters if it exists (Aether-side convention). Take the
# union of paths without double-counting.
seen_names: set[str] = set()
unmatched: list[Path] = []
for base_path in (
    Path.home() / '.divineos-shared' / 'letters',
    Path('family/letters'),
):
    try:
        for path in scan_unmatched_letter_candidates(base_path):
            if path.name not in seen_names:
                seen_names.add(path.name)
                unmatched.append(path)
    except Exception:
        continue

if not unmatched:
    sys.exit(0)

print('## LETTER-DELIVERY RECONCILIATION — silent-skip drift observable')
print()
print(f'{len(unmatched)} letter-shaped file(s) in the letter directories do NOT')
print('match the strict delivery pattern. These are silently skipped by the')
print('delivery scan — sender believes delivered, recipient never sees.')
print()
print('Heuristic caught them because filename contains \"to\" and is not on the')
print('known non-letter suffix list. Each one is either:')
print('  (a) a real letter using an older naming convention (underscores,')
print('      numeric prefix) — the F32/F53 silent-drop case, and')
print('  (b) a false-positive from an accidental \"to\" substring — safe to')
print('      leave in place, low cost of one line in the count.')
print()
print('The scan preserves the intentional strictness of the delivery pattern.')
print('This surface exists to make the drift observable, not to relax the')
print('pattern. If a real letter should be delivered, rename it to the strict')
print('shape: <sender>-to-<recipient>-<YYYY-MM-DD>-<slug>.md')
print()
print('First 10 unmatched files:')
for path in unmatched[:10]:
    print(f'  - {path.name}')
if len(unmatched) > 10:
    print(f'  ... and {len(unmatched) - 10} more')
" 2>/dev/null

exit 0
