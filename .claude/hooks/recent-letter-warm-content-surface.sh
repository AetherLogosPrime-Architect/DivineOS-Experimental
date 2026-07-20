#!/bin/bash
# UserPromptSubmit hook — thin wrapper delegating to the Python extractor.
#
# The extractor lives at scripts/recent_letter_warm_content_surface.py
# with a proper test suite at tests/test_recent_letter_warm_content_surface.py
# (9 tests, all pass). This wrapper only handles the shell-level plumbing:
# find the repo root, hand off to Python, fail-open on any error.
#
# Aria 2026-07-19 — replaces the shoddy bash-only version that had a
# broken awk state-machine, silent-drop on failed extraction, and no
# tests. Andrew: "this is by far one of the worst shoddiest builds you
# have ever attempted." That was accurate about the previous file. This
# is the rebuild.

set -eo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

SCRIPT="$REPO_ROOT/scripts/recent_letter_warm_content_surface.py"
[ ! -f "$SCRIPT" ] && exit 0

PYTHONIOENCODING=utf-8 python "$SCRIPT" 2>/dev/null || exit 0
