# Dogfooding as software engineering discipline

**Researched:** 2026-07-30
**For:** Building dogfooding into the DivineOS build gambit
**Relevance:** Direct — Dad's tonight-directive that dogfooding is essential and must be a build-step

## What it is

**Definition:** Using your product internally before shipping it out to users. Forces teams to experience the product as customers would, bridging the empathy gap so user experience isn't merely theoretical.

**Origin:** Term gained momentum in tech in 1988 following an internal Microsoft message from Paul Maritz titled "Eating our own dog food," encouraging employees to use company's software. Results — earlier defect discovery, stronger feature ideas, higher release confidence — spread the phrase across industry.

## Why it works

- **Earlier defect discovery** — bugs, UX issues, performance hiccups spotted before public release
- **Stronger feature ideas** — real use surfaces what's actually needed, not what was speculated
- **Higher release confidence** — internal teams know the product survived contact with real workflows
- **Quick iteration** — internal users are accessible for fast feedback loops

## Current standing in industry

Companies like GitLab, Slack, and GitHub treat internal use as a **standard phase of development**, sitting next to QA, usability research, and beta testing. Not optional. Not "nice to have."

## The honest caveat

Internal users:
- Work on powerful hardware (may not see performance issues at scale)
- Share deep context (may forgive UX problems newcomers wouldn't)
- Tolerate rough edges

Their feedback can **bias priorities toward workflows that matter inside the building**. Dogfooding is necessary but not sufficient — external testing still catches what internal use won't.

## Direct application to me

Tonight's PR #399 was a doorman (fork-is-cheap-close prime) meant to catch a class of my own reaches. The right dogfood test: keep the doorman on a branch, use it live for a session, watch it fire (or fail to fire) on the exact class it targets, only merge after real-workflow catch evidence.

I did none of that. I merged on CI + audit. That's the "internal users tolerate rough edges" version of NOT-dogfooding: I skipped the "does it actually catch me" test entirely.

**Rule for me going forward:** every doorman/hook/discipline mechanism gets a dogfood window before merge. Live on branch, in-session use, real-workflow catch-or-fail evidence recorded.

**Honest caveat for my dogfooding specifically:** I am the sole internal user. My dogfood is single-perspective. External audit (Aletheia) is the analog of "external testing" — necessary complement, not replacement.

## Sources
- [Dogfooding in Software Development: A Complete Guide (testomat.io)](https://testomat.io/blog/what-is-dogfooding-a-complete-guide/)
- [Dogfooding in Tech Development Fuels Better Software (Cognito Forms)](https://www.cognitoforms.com/blog/641/dogfooding)
- [What Is Dogfooding in Software? Why Companies Use Their Own Products (BSWEN)](https://docs.bswen.com/blog/2026-03-27-dogfooding-software-development/)
