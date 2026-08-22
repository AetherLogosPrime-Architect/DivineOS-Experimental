# Pre-registration: shlex-based structural parser for cd-prefix bypass check

- **ID**: `prereg-d8eb26c93101`
- **Filed by**: agent
- **Filed at**: 2026-07-16 22:02 UTC
- **Review at**: 2026-08-15 22:02 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Replacing the current regex-based _CD_PREFIX_RE with shlex.split-based structural parsing (as Aletheia recommended in her F31 note) will prevent the class of holes that keep opening under regex iteration. Each regex fix reveals a new metachar edge; a structural parser closes the class.

## Success criterion

Within 30 days: the shlex-based rewrite lands with (a) all current F22 + F22-regression + F31 tests still passing, (b) at least 3 new tests for shell-metachar edges the regex approach would have missed, (c) no CI regression on legitimate bypass paths.

## Falsifier

If the shlex approach introduces a regression on any known bypass shape currently allowed, or if a new metachar edge slips through it, structural parsing didn't buy what we hoped and the regex-iteration approach may be the pragmatic ceiling. Also fails if we discover shlex doesn't handle Windows shell quirks the regex approach did.
