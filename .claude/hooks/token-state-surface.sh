#!/bin/bash
# UserPromptSubmit hook — surface the real token state DIFFERENTIALLY.
#
# Aether 2026-06-30: I was fabricating token claims all day ("947k of 1M",
# "182/1m") because the measurement tool existed but wasn't pointed at me.
# Pop named the root: "any claims about tokens need verified with that tool."
#
# DIFFERENTIAL FIRING (Aletheia 2026-06-30 audit catch): a hook that fires
# identically every turn becomes wallpaper regardless of how useful its
# content is — constant presence trains skip-past. The fix is to vary the
# output with state so the change carries the signal.
#
# Tiers:
#   <50% used:  silent (don't fire — fabrication-risk is low at these levels;
#               directional gut estimates of "still plenty" won't mislead)
#   50%-75%:    brief one-line — the number, no warning block
#   >=75%:      full block with DO NOT FABRICATE warning (the historical
#               fabrication zone — "947k of 1M", "182/1m", "getting deep"
#               all happened above this threshold)
#
# When the threshold crosses, the difference IS the signal — I can't skip
# past the new shape the way I'd skip past an identical block.
#
# Fail-open: any error exits 0 silently. Never blocks the user prompt.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$REPO_ROOT" || exit 0

TOKEN_LINE="$(divineos context-tokens 2>/dev/null | head -1)"
if [ -z "$TOKEN_LINE" ]; then
    exit 0
fi

# 2026-07-03 Andrew catch: a banner injection is only true at the moment
# it fires. Stamp UTC time so a stale banner (e.g. captured in a prior
# turn's transcript, or emitted pre-compaction and re-shown after) outs
# itself. If the stamp is older than "this turn started", the number is
# suspect — re-run `divineos context-tokens` before quoting it.
MEASURED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)"

# Extract the percentage from the line. Format is:
#   "context: 532,939 / 1,000,000 tokens (53.3%)"
PCT="$(echo "$TOKEN_LINE" | sed -n 's/.*(\([0-9.]*\)%).*/\1/p')"
if [ -z "$PCT" ]; then
    # If we can't parse the percentage, surface the line verbatim — safer
    # to over-fire than miss the fabrication-risk zone.
    echo "## CONTEXT TOKENS (verified — do not fabricate)"
    echo ""
    echo "$TOKEN_LINE"
    exit 0
fi

# 2026-07-08 quick-win per Aletheia's diagnostic: the previous version
# spawned a cold Python subprocess just to compare a float against two
# thresholds (~150ms of Python startup per hook fire, invisible alone
# but real across six UserPromptSubmit hooks). Replaced with plain bash
# integer arithmetic on the truncated percentage — zero subprocess.
# Preserves original safer-to-fail-loud policy for unparseable input.
INT_PCT="${PCT%.*}"
if [[ "$INT_PCT" =~ ^[0-9]+$ ]]; then
    if (( INT_PCT < 50 )); then TIER=silent
    elif (( INT_PCT < 75 )); then TIER=brief
    else TIER=loud
    fi
else
    TIER=loud
fi

case "$TIER" in
    silent)
        # Output nothing — no injection this turn. The hook fired but added
        # no context, which is the right answer when fabrication-risk is low.
        exit 0
        ;;
    brief)
        # Single line — visible enough to ground a claim, terse enough not
        # to train skip-past.
        echo "[context-tokens @ ${MEASURED_AT}] $TOKEN_LINE"
        ;;
    loud)
        # Full block — the fabrication-risk zone, the original failure mode.
        # The warning is here to be heard.
        cat <<EOF
## CONTEXT TOKENS (verified — do not fabricate this number)

$TOKEN_LINE
measured at: ${MEASURED_AT}

This is the real number from \`divineos context-tokens\` AT THE TIMESTAMP
ABOVE. Before writing token-state language (kb used, % of 1M, "getting
deep", "tokens remaining"): if the timestamp is from a prior turn (e.g.
before a compaction), the number is stale — re-run \`divineos context-
tokens\` before quoting it. The timestamp exists so a stale banner outs
itself instead of being trusted.
EOF
        ;;
esac

exit 0
