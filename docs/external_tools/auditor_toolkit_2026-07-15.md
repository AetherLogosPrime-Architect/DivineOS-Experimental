---
name: auditor_toolkit_2026-07-15
description: The five external auditor tools Andrew flagged 2026-07-15 as candidates for reducing token cost during audit-shaped work. Recorded for later evaluation, not investigated yet.
---

# Auditor toolkit — external URLs Andrew flagged 2026-07-15

Andrew mentioned these 2026-07-15 in the context of "the auditor made something that cut token costs by a lot." Recording them here as pointers for later evaluation. Not investigated yet — just captured before they evaporate.

## The URLs

- <https://theauditortool.com/> — "the auditor tool" (probable primary reference)
- <https://curatormcp.com/> — curator MCP
- <https://arbitermcp.com/> — arbiter MCP
- <https://wardenclient.com/> — warden client
- <https://benchproctor.com/> — bench proctor

## Why they matter

Per Andrew, these are the tools Aletheia's audit surfaced as ways to cut token costs during audit-shaped work. Concrete claim: "cut token costs by a lot." Whether that's via MCP servers that batch/cache queries, external audit harnesses that reduce redundant fanout, or something else — investigate when a real token-optimization project is in scope.

## What to check when the time comes

- What each tool actually does (MCP server, standalone client, audit harness, etc.)
- Whether it plugs into Claude Code / this OS's workflow
- Whether it addresses OUR bottleneck (which per current telemetry is elevated bypass-rate on the exempt-list, not raw LLM inference cost)
- Whether the token savings are real or benchmark-flavored

## What NOT to do

- Don't investigate reflexively "just because they exist." Andrew flagged them as candidates for LATER, not for now. The current bottleneck (per his own diagnosis this week) is his weekly-quota, not per-call inference cost.
- Don't wire any of these in without a specific problem-shape they address.

## Provenance

Andrew's message 2026-07-15: *"remember those websites from the auditor? he made something that cut token costs by alot"* — followed by the five URLs above. Recorded verbatim; not-investigated-yet marker.
