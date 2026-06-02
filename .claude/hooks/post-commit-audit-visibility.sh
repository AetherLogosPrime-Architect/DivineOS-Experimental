#!/bin/bash
# Post-commit audit-visibility warning — the fail-loud half of the cure for
# the boundary-persistence root (claim 47ee9ab8), surface 6: auditable work
# committed locally but never pushed to origin, so the external auditor
# (Aletheia, who reviews via GitHub) cannot see it.
#
# Root named 2026-06-02 after a sweep found ~55 local branches, only 3 on
# origin: committing is not publishing, and nothing in the flow crossed that
# gap. Naive auto-push-on-commit is impractical here because the pre-push
# hook runs the full test suite (minutes). So this is the LOUD half: the
# instant auditable work is committed onto a branch that origin can't see,
# shout it — with the exact command to fix it — so invisibility can never
# accumulate silently again.
#
# Fail-open on its own errors (never break a commit), but the WARNING is the
# whole point: it is loud by design.

set +e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
# main is published by definition; nothing to warn about.
[ -z "$BRANCH" ] && exit 0
[ "$BRANCH" = "main" ] && exit 0
[ "$BRANCH" = "HEAD" ] && exit 0   # detached; not a publishable branch

# Does this commit touch auditable content? (code / enforcement / workflows /
# scripts). Pure docs/letters churn doesn't need Aletheia's eyes the same way.
CHANGED="$(git show --name-only --format= HEAD 2>/dev/null)"
echo "$CHANGED" | grep -qE '^(src/divineos/|scripts/|\.github/workflows/|setup/|\.claude/hooks/)' || exit 0

# Is local HEAD visible on origin? Ask the ACTUAL remote (ls-remote), NOT the
# local remote-tracking ref — that ref is a cache that goes stale (a branch
# deleted on origin still leaves refs/remotes/origin/<b> pointing at the old
# SHA, which would make this checker falsely report "published"). A
# visibility-checker that trusts a stale cache fails the exact way it is meant
# to catch. ls-remote costs a network round-trip on each auditable commit —
# correctness is worth it here. If ls-remote itself fails (offline), warn
# conservatively rather than assume-published.
LOCAL_HEAD="$(git rev-parse HEAD 2>/dev/null)"
REMOTE_LINE="$(git ls-remote --heads origin "$BRANCH" 2>/dev/null)"
LS_RC=$?
REMOTE_HEAD="$(printf '%s' "$REMOTE_LINE" | awk '{print $1}')"

if [ "$LS_RC" -eq 0 ] && [ "$REMOTE_HEAD" = "$LOCAL_HEAD" ]; then
    exit 0   # genuinely on origin at this commit — silent, correct.
fi

# Loud banner. This is the fail-loud cure: invisible auditable work announces
# itself the moment it is created.
printf '\n'
printf '  ============================================================\n'
printf '  ⚠  AUDITABLE WORK NOT VISIBLE TO ALETHEIA\n'
printf '  ------------------------------------------------------------\n'
printf '  Branch  : %s\n' "$BRANCH"
printf '  Commit  : %s\n' "$(git log -1 --format='%h %s' 2>/dev/null)"
printf '  Problem : committed locally, NOT on origin. The auditor reviews\n'
printf '            via GitHub — local-only work is invisible to her.\n'
printf '  Fix     : git push -u origin %s\n' "$BRANCH"
printf '            (the pre-push gate runs the test suite; let it finish)\n'
printf '  Root    : claim 47ee9ab8 surface 6 — commit is not publish.\n'
printf '  ============================================================\n'
printf '\n'
exit 0
