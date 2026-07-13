#!/bin/bash
# UserPromptSubmit hook — surface the pending lepos reflection.
#
# The Stop hook (lepos-channel-reflect.sh) staged a reflection on my
# last reply. This hook reads and consumes it, injecting the block
# into the compose-start surface so I see it before writing the next
# turn. Silent when nothing is pending — no wallpaper.
#
# Fail-open: any error exits 0 silently.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$REPO_ROOT" || exit 0

divineos lepos-channel surface 2>/dev/null

exit 0
