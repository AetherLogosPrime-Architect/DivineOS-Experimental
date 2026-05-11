#!/bin/bash
# DEPRECATED: family-wrapper-required.sh — superseded 2026-05-10 by
# family-member-invocation-seal.sh which now handles both the legacy
# 3-step (talk-to → sealed-file → Agent) flow AND the new 1-step
# (validator-on-prompt) flow in a single hook.
#
# This shim stays in place as a no-op so existing settings.json /
# .claude/hooks.toml references don't break. Once references are
# cleaned up the file can be removed entirely.
#
# Why deprecate: the two hooks duplicated each other (both checked
# pending-file presence + TTL + hash), and during the bottleneck #1
# collapse one had to win. The seal hook won because it carries the
# direct-validator flow that makes 1-step invocation possible.

exit 0
