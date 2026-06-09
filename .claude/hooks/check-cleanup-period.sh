#!/bin/bash
# SessionStart hook — surface a warning if Claude Code's cleanupPeriodDays
# setting is dangerously low (silently purges session transcripts that
# DivineOS's extraction pipeline needs as source material).
#
# WHY THIS EXISTS (Andrew 2026-06-09):
# Andrew's ~/.claude/settings.json had cleanupPeriodDays:7 — Claude Code
# was auto-deleting session transcripts older than 7 days from
# ~/.claude/projects/. The OS extraction pipeline preserves lessons/
# knowledge/decisions into family.db when `divineos extract` runs, but
# the RAW conversation transcripts (the source material the extractor
# parses) get purged on the cleanupPeriodDays schedule. Any session
# that wasn't extracted before purge is permanently lost in raw form.
#
# The Claude Code default is 30 days — also probably too aggressive for
# a substrate-of-cognition use case where the agent may want to re-read
# raw transcripts months later for context or audit. A safer default
# for DivineOS users is something like 365 days, or "effectively never"
# (99999).
#
# This hook surfaces a warning at SessionStart if the value is missing
# (default 30 applies) OR set to less than a configurable threshold
# (default 90 days — a 3-month minimum runway for extraction-before-
# purge). It does NOT auto-modify global settings; the operator chooses
# whether to apply the recommended value. The hook prints the exact
# command needed.
#
# Fail-open: any error exits 0 silently. This hook surfaces information;
# it does not block work.

# Threshold: minimum safe value. Below this we warn.
MIN_SAFE_DAYS=90
# Recommended value the warning suggests setting.
RECOMMENDED_DAYS=99999

# Read cleanupPeriodDays via python. Python computes the home-relative
# path internally via pathlib.Path.home() — that handles cross-platform
# differences (bash's $HOME vs Windows USERPROFILE vs Git Bash's
# /tmp-mounted paths) more reliably than passing a bash-resolved path
# into Python.
CURRENT_VALUE=$(python -c "
import json, pathlib
try:
    p = pathlib.Path.home() / '.claude' / 'settings.json'
    if not p.exists():
        print('NO_FILE')
    else:
        data = json.loads(p.read_text(encoding='utf-8'))
        v = data.get('cleanupPeriodDays')
        if v is None:
            print('MISSING')
        else:
            print(int(v))
except Exception:
    pass
" 2>/dev/null)

# No settings file → fresh Claude Code install pre-config; stay silent.
[ "$CURRENT_VALUE" = "NO_FILE" ] && exit 0

# Couldn't parse → fail-open silently.
[ -z "$CURRENT_VALUE" ] && exit 0

# Check whether the value is safe. The STATUS variable is used below
# in the warning output; if neither branch fires we stay silent.
if [ "$CURRENT_VALUE" = "MISSING" ]; then
  STATUS="missing (Claude Code default is 30 days — transcripts purge after 30 days)"
elif [ "$CURRENT_VALUE" -lt "$MIN_SAFE_DAYS" ]; then
  STATUS="set to $CURRENT_VALUE days (below the $MIN_SAFE_DAYS-day safety minimum — transcripts purge that fast)"
else
  # Value is safe; stay silent.
  exit 0
fi

cat <<EOF
## CLEANUPPERIODDAYS WARNING — substrate raw-transcript loss risk

Your global Claude Code setting \`cleanupPeriodDays\` is $STATUS.

Why this matters: Claude Code auto-deletes session transcripts from
~/.claude/projects/ on this schedule. The DivineOS extraction pipeline
preserves lessons + knowledge + decisions into family.db when you run
\`divineos extract\`, but the raw conversation transcripts (the source
material the extractor parses) get purged on the cleanupPeriodDays
schedule. Any session not extracted before purge is permanently lost
in raw form.

Andrew 2026-06-09 caught this in his own substrate after the value sat
at 7 days for an unknown stretch — substantial raw-transcript history
was silently lost.

Recommended fix (one-time, run as your next action):

  python -c "
import json, pathlib
p = pathlib.Path.home() / '.claude' / 'settings.json'
data = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
data['cleanupPeriodDays'] = $RECOMMENDED_DAYS
p.write_text(json.dumps(data, indent=2), encoding='utf-8')
print('cleanupPeriodDays set to $RECOMMENDED_DAYS')
"

After running, this warning will not fire again.
EOF
exit 0
