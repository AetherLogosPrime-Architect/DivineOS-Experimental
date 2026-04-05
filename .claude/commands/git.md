---
name: Git Commit
description: Generate professional git commit message for review.
---

List ALL files you have edited or created in this session.

For each file, briefly note what changed (1 line max).

Then generate a git commit message following this format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Requirements:**
- Type: feat|fix|refactor|docs|test|chore|perf
- Subject: imperative mood, no period, max 50 chars
- Body: Explain WHY and HOW, not just WHAT. Write as if onboarding someone reading this commit 6 months from now. Include context that isn't obvious from the diff.
- Footer: Breaking changes, related issues, or dependencies

**Forbidden:**
- NO "Co-authored-by: Claude" or any AI attribution
- NO generic phrases like "various improvements" or "code cleanup"
- NO listing every single line changed - summarize intelligently
- DONT COMMIT YOURSELF EVER!!

**Example quality:**
```
refactor(pipeline): replace JSON aggregation with database query

The final status was reporting "[CLEAN]" despite 226 critical findings
because pipelines.py:1694 read from non-existent findings.json instead
of the actual patterns.json. Rather than fix the filename, switched to
querying findings_consolidated directly (database is source of truth).

Key changes:
- Add _get_findings_from_db() helper with SECURITY_TOOLS filter
- Remove 3 try/except blocks that violated ZERO FALLBACK policy
- Security tools (patterns,taint,terraform,cdk) now drive exit code
- Quality tools (ruff,eslint,mypy) excluded from security status

Breaking: None (return dict structure unchanged)
```

Present the commit message for my review. Do NOT commit automatically.
