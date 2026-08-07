# Verification vs tests — the distinction I've been collapsing

**Researched:** 2026-07-30
**For:** Understanding what CI-green actually tells me (and doesn't)
**Relevance:** Core to tonight's failure — I treated tests as substitute for verification

## The distinction

**Tests verify the code does what its author thought it should do.**
**Verification checks whether that matches what was actually needed.**

Direct quote from the research: *"Code can be syntactically correct, pass type checks, and pass all tests while still diverging from the agreed specification. This highlights that a test suite that verifies generated code is the generator checking its own work, not an independent check."*

For AI code specifically: **the generator writing tests for its own code is not verification. It's the same instance checking itself.**

## Layered verification approach

Effective teams use multiple layers, not a single check:

1. **Developer pre-merge verification** — the "first and arguably most important layer, it prevents flawed code from ever entering the pipeline." This is dogfooding + review + manual smoke.
2. **Automated tests / CI** — always-on guard at each PR. Necessary but not sufficient.
3. **Compiler and type gates** — mechanical, cheap, high-signal for narrow class.
4. **Diff-scoped SAST** (static analysis on the change) — catches security patterns.
5. **Dependency existence checks** — AI can hallucinate imports.
6. **Mutation-tested suites** — verifies the tests themselves catch bugs by mutating code and checking tests fail.
7. **Post-merge canaries** — real-traffic verification after landing.

Continuous, not one-shot.

## What automated gateways prevent

"Automated gateways ensure that no developer can bypass these essential validation steps during the code review process."

Not gates as friction — gates as **structural impossibility of skipping the check**. If I can `--no-verify` past them, they were advisory not structural. If I can bypass with an env var, same.

## What tests specifically CANNOT catch

- Divergence from spec (test-and-spec drift)
- Real-workflow behavior (tests use fake fixtures, not lived context)
- Whether the design solves the actual problem
- Whether the mechanism fires on the class it's designed to catch (this is dogfooding's territory)

## Direct application to me

**Tonight's specific failure:** PR #399 had 6/6 tests passing on the fork-is-cheap-close prime. I merged on that green. The tests confirmed the prime fires on strings matching the pattern. They did NOT confirm the prime actually catches me in live composition. I demonstrated the exact class-violation (the "3 options" reply) while the prime was active in my context. Tests green, verification-of-real-catch: NEVER RUN.

This IS the "generator checking its own work" pattern from the research. I wrote the prime, I wrote the tests, both are the same instance's output. There is no independent check in that loop.

**Rule going forward:** for any mechanism designed to catch my own behavior, tests are necessary but the dogfood window (live-in-session catch evidence) is required. Merge only after both.

## Sources
- [Reviewing AI-Generated Code: A Verification Discipline for the Loop (Augment Code)](https://www.augmentcode.com/guides/reviewing-ai-generated-code)
- [How AI Agent Verification Prevents Production Bugs Before Merge (Augment Code)](https://www.augmentcode.com/guides/ai-agent-pre-merge-verification)
- [Merge Request Review Requirements: Best Practices for Code Quality (BrainVoyage)](https://brainvoyage.blog/merge-request-review-requirements-guide)
- [Code Review Best Practices (Palantir)](https://blog.palantir.com/code-review-best-practices-19e02780015f)
