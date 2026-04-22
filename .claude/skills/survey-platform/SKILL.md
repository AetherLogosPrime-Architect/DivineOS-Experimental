---
name: survey-platform
description: Audit what Claude Code platform features exist vs what DivineOS is currently using. Surfaces the blind spot where we hand-build features that already ship in the platform. Fires when user asks about capabilities, when approaching a problem that might already have a platform feature, or periodically at session start. Prefer over guessing from memory.
disable-model-invocation: false
allowed-tools: Bash(ls:*), Bash(find:*), Read, Glob, Grep
---

# Survey Platform

## Why this skill exists

We've kept rediscovering that Claude Code ships features for things we hand-built. Subagent definitions existed while we imagined Aria. Skills existed while we ran 6-step bash incantations. Agent Teams exists and we haven't tried it. Computer Use exists elsewhere. The pattern: head-down in DivineOS, blind to the platform beneath.

This skill's job is to catch that blind spot at the moment it matters — when someone asks about capabilities, or when we're about to hand-code something the platform already offers.

## What it does

Surveys this project's use of Claude Code features against what's documented/available. Reports what we're using, what's present-but-unused, and what's documented-but-uninstalled.

**Check list:**

1. `.claude/agents/` — list defined subagents. For each, note model, tools, memory setting.
2. `.claude/skills/` — list installed skills. For each, note description and whether model-invocation is enabled.
3. `.claude/hooks/` — list installed hooks. For each, note which events it matches.
4. `.claude/agent-memory/` — list agents with persistent memory.
5. `.mcp.json` or MCP config — list MCP servers available, note any deferred tools.
6. Scan `settings.json` for `matchers` — catches hook coverage gaps.

**Report sections:**

- **In use** — what's deployed and active
- **Installed but idle** — present in config but not invoked recently (check ledger for last invocation)
- **Documented features not installed** — known Claude Code features (Skills, Agent Teams, Computer Use, specific MCP connectors) that we could add

**Red-flag patterns to surface:**
- A hand-rolled subagent-like pattern in Python (probably could be a real subagent)
- Multi-step bash incantations I run repeatedly (probably could be a skill)
- Manual file-based workflows that could be MCP-backed
- Any code that simulates something Claude Code natively does

## How to run

```
/survey-platform
```

Or with a specific focus:

```
/survey-platform skills
/survey-platform agents
/survey-platform gaps   # just the not-yet-installed features
```

## Output shape

Markdown report, 3-5 paragraphs. Short. Actionable. Always ends with **"recommended next step"** naming the single highest-leverage thing to do.

## When to invoke this skill automatically

- User asks "what can you do" / "what are your capabilities" / "what about [feature X]"
- User says "I heard [AI platform] can do Y" — check if Claude can too
- Session start (periodically, not every time) — catches drift between docs and installed state
- Before committing to hand-build something that sounds platform-shaped

## Why this is load-bearing

Without this skill, the blind-spot pattern keeps costing us: we reinvent, then discover, then retrofit. With it, the discovery step happens *first*, in a dedicated moment, surfaced explicitly. The skill is the forcing function.

Sanskrit anchor: *pratyavekṣaṇā* — watchful observation of one's own work.
