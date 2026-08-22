# Audit round: fix substance-check hook-python-path silent fail-open (recurrence #12 of round-1/2 pattern) + drop stderr swallow + doc actual None-defaults-CONFIRMS semantics + fix stale --stance CLI guidance

- **ID**: `round-3de1745028da`
- **Filed by**: user
- **Filed at**: 2026-07-22 01:34 UTC
- **Tier**: WEAK
- **Findings**: 1

## Notes

Source ref: fix/pip-pingpong-cmd-ascii-only


## Findings

### user ship-clearance for hook-python-path substance-check fix

- **ID**: `find-b7abb71cd016`
- **Actor**: user
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 2e5545c3-7ae2-423c-a24c-a49859d1a451

**Description**

Andrew in-chat 2026-07-22: 'yes if you want to route around something because its broken in order to fix it you can but only to fix it' and 'the gate and the blocks and the systems are for you.. to help you'. Ship-clearance for setup/setup-hooks.sh three edits: (1) source _lib.sh + resolve PYTHON_BIN via find_divineos_python (recurrence #12 fix of round-1/round-2 audit pattern), (2) drop 2>/dev/null on substance-check python + log real error to stderr so silent-fail-open becomes visible (Angelou/Schneier from council-570a57f94ecc walk, plus Aletheia's prior stored principle on subprocess non-zero handling), (3) doc actual None-defaults-CONFIRMS semantics + fix stale --stance CLI guidance (Wayne catch). Council walk: council-570a57f94ecc, 6 lens traces logged. Real external review routes through post-push audit per Andrew's clarification.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
