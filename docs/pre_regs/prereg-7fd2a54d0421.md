# Pre-registration: test_cli_linkage_check

- **ID**: `prereg-7fd2a54d0421`
- **Filed by**: agent
- **Filed at**: 2026-05-05 23:11 UTC
- **Review at**: 2026-06-04 23:11 UTC (30d window)
- **Outcome**: **OPEN**
- **Tags**: failure-mode-prevention, audit-2026-05-05

## Claim

scripts/check_test_cli_linkage.py prevents the PR #264 failure mode (test references CLI command that does not register)

## Success criterion

in the next 30 days a test_*.py file in this repo references an unregistered command, AND precommit blocks the commit before push

## Falsifier

in the next 30 days a PR is merged where a test references an unregistered command (mirrors #264 shape) and the linkage check did NOT block it
