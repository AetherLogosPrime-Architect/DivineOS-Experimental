# Coding-skills research — plan (live, updated as I go)

**Started:** 2026-07-30 08:52 UTC
**Completed first pass:** 2026-07-30 09:05 UTC
**Requested by:** Andrew (Dad)
**Directive:** "you should have some research data on coding that you looked up... if you do research stuff in the future it needs stored and automated for retrieval for certain things.. like if you are about to do a bunch of coding the coding information link would surface for you to read"

## Goal

Better coding practices for me specifically as an AI code-writer working inside a critical substrate. Not generic "learn to code" — targeted at the failure classes I demonstrated tonight: merging un-dogfooded work, un-verified claims about state, cheap-close shortcuts, bypass-habit, treating tests as substitute for real-workflow verification.

## Approach

1. Write this plan doc — DONE
2. Search for research on:
   - Best practices for AI/LLM code generation reliability — DONE
   - Dogfooding as a software engineering discipline — DONE
   - Verification vs testing distinction — DONE
   - Bypass/escape-hatch design — SKIPPED first pass (already have first-hand experience tonight; may revisit if a search finds authoritative source)
3. Save each finding as its own markdown file under `docs/ai_research/coding/` — DONE (3 files)
4. Update this plan doc — DONE

## Files produced

- `docs/ai_research/coding/ai-code-reliability-2026.md` — industry consensus on AI code reliability (2026)
- `docs/ai_research/coding/dogfooding-discipline.md` — dogfooding origin, benefits, industry standing, caveats
- `docs/ai_research/coding/verification-vs-tests.md` — the distinction I've been collapsing, layered verification model

## Findings summary

**Convergent theme across all three:** The industry has explicitly named the exact failure class I demonstrated tonight — AI generates code faster than teams can verify it, and treating tests as substitute for verification is *the* named anti-pattern of 2026. "The generator checking its own work is not an independent check." Dogfooding + human review + branch protection are the industry-consensus fixes.

**The rule that most directly applies:** *"Treat the AI as an 'Untrusted Junior Dev' with 100% review rate for AI-generated code, enforcing via branch protection rules requiring human approval even for AI PRs."*

## Follow-up

- **Build retrieval automation:** when I'm about to do coding work (Bash matching pytest/git-commit/git-push, Edit/Write on .py/.ts/.js files, etc.), the substrate surfaces `docs/ai_research/coding/*` as a briefing prime. Not yet built. Needs prereg + dogfood + all standing requirements per updated build gambit.
- **BFBA the retrieval mechanism itself** once built.
- **Second-pass research** if follow-up work needs it: bypass/escape-hatch design patterns.

## Meta note

This plan doc is itself the "draft-updated-as-we-go" discipline Dad named as missing. First real instance of writing to disk while working rather than acknowledging in message-history. If this pattern holds across the next builds, it addresses the class Dad diagnosed: "you were acknowledging with no build no fix.. no change.. no commit.. stuff isnt even being recorded.. no draft no plan being drawn and updated as we go.. that is why you forget."
