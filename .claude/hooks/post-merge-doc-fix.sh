#!/bin/bash
# WIRED VIA .git/hooks/post-merge — installed by setup/setup-hooks.sh,
# which writes a git post-merge that explicitly calls THIS file. So it
# FIRES on every merge (not via .claude/settings.json). Third wiring
# surface beyond Claude Code settings + code-graph (Aletheia cold-audit
# 2026-07-16 finding #2 marker).
#
# Post-merge: auto-fix architecture-tree drift introduced by merge resolution.
#
# Problem (lived through 2026-06-13 on PR #169): a feature branch had its
# semantic_search.py entry correctly added to docs/ARCHITECTURE.md, but
# every time main was merged back in, the merge resolution dropped the
# entry. The next CI run failed on test_real_readme_passes, the branch
# needed a manual re-add, and the cycle repeated on the next rebase.
#
# Root cause: `git merge` resolved a textual conflict by taking main's
# version, which didn't have the entry. The auto-fix in precommit only
# runs at commit time — a merge commit can sneak past it.
#
# Fix: after any merge, re-run `python scripts/check_doc_counts.py --fix`.
# If it adds entries, re-stage and amend the merge commit so the tree
# stays in sync without another commit.
#
# Fail-open: any error exits 0 silently. This hook cannot break workflow.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    exit 0
fi
cd "$REPO_ROOT" || exit 0

# Don't run if the user opted out.
if [ "${DIVINEOS_DOC_COUNT_NO_AUTOFIX:-}" = "1" ]; then
    exit 0
fi

# Only act when the doc check is actually failing — if main was clean,
# the merge resolution didn't drop anything, and we have no work to do.
if python scripts/check_doc_counts.py >/dev/null 2>&1; then
    exit 0
fi

# Run --fix; surface output so Andrew sees what changed.
python scripts/check_doc_counts.py --fix 2>&1 || true

# Re-stage only the docs the fix touches. Avoid `git add -A` — that
# could grab unrelated WIP files that happened to be in the working tree.
git add docs/ARCHITECTURE.md CLAUDE.md README.md src/divineos/seed.json 2>/dev/null || true

# If anything got staged, amend the merge commit so the tree-and-doc
# state ships together. --no-edit keeps the original merge message.
if ! git diff --cached --quiet; then
    git commit --amend --no-edit 2>/dev/null || true
    echo "[post-merge-doc-fix] Architecture tree auto-synced; merge commit amended."
fi

exit 0
