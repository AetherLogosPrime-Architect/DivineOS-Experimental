#!/bin/bash
# SUPERSEDED 2026-09-08 by the router. The decision now lives in
# divineos.core.hook_surfaces as correction_marker_surface, dispatched by
# doorbell-user-prompt-submit.sh. The registration came out of settings.json in
# the SAME change -- a migration that leaves the original registered has moved
# code and retired nothing.
# INTENTIONALLY UNWIRED (2026-09-08): superseded, see above.
# UserPromptSubmit hook — thin doorbell for the correction-detector.
#
# All judgment lives in `divineos.core.correction_marker.hook_main()`.
# Migrated 2026-06-30 to the thin-wrapper pattern (Pop: "make the hooks
# dumber so they can't be wrong; put the logic in the OS so the decision
# happens where the contract is").
#
# What this gate does (in summary): classifies the user's prompt for
# correction language, considering whether the prior assistant turn was
# actually a correctable action. Block-tier matches set the gate marker;
# advise-tier matches print a stdout advisory (lands as additionalContext).
#
# Fail-open: any error exits 0 silently. Never blocks the workflow.

set +e
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

"$PYTHON_BIN" -c "
import sys
try:
    from divineos.core.correction_marker import hook_main
    sys.exit(hook_main())
except Exception:
    pass
" 2>/dev/null

exit 0
