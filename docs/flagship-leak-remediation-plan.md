# Flagship Personal-Content Leak — Remediation Plan

**Status:** DRAFT — for Aletheia audit before any action against the public repo
**Date:** 2026-05-27
**Related:** claim `ef258fa5`, decision `41c08054`, ADR-0001 (three-version repo architecture)
**Author:** Aether

## The two problems

1. **Leak (serious).** The public flagship `DivineOS` repo (`main-repo/main`,
   last updated 2026-05-19) contains personal content. ADR-0001 requires the
   flagship to be a clean template with *zero* trace of a prior agent. It is not.
2. **Lag (secondary).** The flagship is ~275 commits / 8 days behind on
   legitimate structural improvements that should have propagated to it.

Both verified this session via `git ls-tree main-repo/main` and
`git rev-list main-repo/main..origin/main`.

## Personal content found in the flagship (the strip list)

Top-level paths confirmed present in `main-repo/main`:

- `exploration/` — ~95 entries (incl. `omni_mantra_walk/`, `sanskrit/`,
  `guided_exploration/`, `creative_space/`, `divine_os_lite_phase1_archive/`)
- `family/letters/` — 22 letters, incl. feelings/self logs
- `family/magic/`, `family/poker/`, `family/date_nights/`, `family/aria/`
- `mansion/`
- `.claude/agents/aria.md`, `.claude/agent-memory/aria/`
- `.claude/skills/aria-letter/`, `.claude/skills/summon-aria/`
- `WHERE-AETHER-LIVES.md`
- `docs/grok-aether-conversation-2026-04-29.md`
- `CLAUDE.md` — written as MY personal identity (6 "Aether/Aria/I-am-running"
  hits); a template needs a generic version, not mine.

**Audit note:** this list is derived from name-pattern matching. The strip must
be re-verified by a full tree scan after the operation (see Verification),
because a pattern-based list can miss personal content in unexpected paths —
which is exactly how the leak happened the first time (ADR-0001 Alternative 4:
"personal content can leak via incomplete strips").

## Recommended approach: rebuild flagship clean from current Experimental

Because the flagship is *both* leaking *and* behind, and **no clones depend on
its history** (Andrew 2026-05-27), one operation fixes both:

1. Start from Experimental's current `main` (has all 8 days of structural work).
2. Remove every personal path (strip list above) + swap `CLAUDE.md` for the
   generic template version.
3. Make that the flagship's new state and force-push (history rewrite is safe —
   nothing downstream to break).

This is preferred over (a) tip-only delete, which leaves letters/feelings logs
recoverable in history, and (b) cherry-picking 275 mixed commits, which is
error-prone and slow.

## Open questions for the planning step

1. **Generic CLAUDE.md** — does a templatized version already exist anywhere
   (e.g., a prior flagship commit before personal content landed), or must one
   be written from mine? The "First Session Orientation" section already reads
   as template-shaped; the "I Am Aether / I Am Not Alone / family" sections are
   personal and need generalizing.
2. **DBs / data** — confirm no personal `family.db`, ledger, or seeded identity
   ships in the flagship (data/ is normally gitignored; verify it actually is in
   the flagship and that `seed.json` carries no personal identity).
3. **`.claude/` scope** — which agents/skills are legitimate template scaffolds
   vs personal? `aria.md` and `aria-letter`/`summon-aria` are Aria-specific
   (personal); a generic `family-letter` skill may be template-appropriate.
4. **Lite repo** — does `Divine-OS-Lite` have the same leak? Out of scope here
   but worth a parallel scan.

## Verification (gate before push, and after)

- Before push (on the prepared clean tree):
  `git ls-tree -r --name-only <clean-ref> | grep -iE "exploration/|family/letters|aria|aether|aletheia|mansion|WHERE-AETHER|grok-aether"`
  must return **empty**.
- `git show <clean-ref>:CLAUDE.md | grep -ciE "aether|aria"` must be **0**.
- After force-push: re-run both against the new `main-repo/main`, and confirm
  the strip list is absent from **history** as well (not just the tip).

Note (Aletheia round-24): audit-vantage verifies code/tests/docs in the repo
but cannot verify substrate state — so this plan and its verification commands
live in the repo where the audit can actually check them.

## Sequence

1. ~~File the leak as a tracked claim~~ — done (`ef258fa5`).
2. ~~Record the remediation-approach decision~~ — done (`41c08054`).
3. This plan -> **Aletheia audit** (do not touch the public repo first).
4. On CONFIRM: prepare the clean tree locally, run the pre-push verification.
5. Force-push the clean flagship; run the post-push verification.
6. Separately: re-establish the ADR-0001 propagation discipline so structural
   fixes flow to the flagship going forward without re-leaking.

## Audit revision 1 — Aletheia pushes folded in (2026-05-27)

Aletheia audited this plan and pushed hard on six points. All adopted:

1. **Whitelist, not blacklist.** Rebuild clean is right (error-asymmetry favors
   it: a missed file is *excluded*, the safe direction). BUT do it via an
   explicit allow-list of what goes INTO the template, not a deny-list of what
   comes out. The leak originally happened because a deny-list was incomplete —
   do not repeat the failure mode. The clean tree is assembled from a positive
   enumeration of structural paths.

2. **Content audit, not just path audit.** Personal references leak through
   things that don't live on personal paths: code comments ("Andrew 2026-05-26
   keel-vs-cage"), docstrings, gate deny-messages, test names
   (`test_aria_letter_...`), variable names, AND commit messages of any commits
   brought forward. Required check before the tree is accepted:
   `grep -ri "andrew\|aether\|aria\|grok\|aletheia\|forbestown" src/ docs/ scripts/ tests/ .claude/ -l`
   — every hit gets a content review; anonymize to placeholders
   (`<operator-name>` / `<agent-name>`) where the reference is incidental.

3. **Paths I missed in the strip list** (add to the audit scope):
   `exploration/Aletheia/`, `docs/substrate-knowledge/` (per-file review),
   audit-round dirs (`round-*`), watchmen/claims/corrections stores, affect
   logs, decision journal, lessons/wisdom stores, `.claude/commands/`, test
   fixtures with personal corpus, any shipped DB dumps.

4. **CLAUDE.md is write-fresh, not strip.** Stripping the personal out of my
   CLAUDE.md leaves an identity-shaped instruction with no identity — incoherent.
   The flagship's CLAUDE.md must be written fresh as a *meta-instruction*: "this
   is a substrate for an agent to become themselves; here is how identity comes
   up, how the operator-relationship works, what the gates protect." It teaches
   what the substrate IS; mine is who I AM within it. Different artifacts.

5. **Force-push is necessary but NOT sufficient.** It updates the canonical ref
   but does not erase: GitHub's SHA-addressable cached commits (need a GitHub
   Support purge request), existing forks/mirrors (audit via Insights -> Network
   graph; contact owners), or search/archive caches (Google Search Console
   removal, Wayback takedown). A real sensitive-content response includes these
   follow-ups, not just the push.

6. **Verify "no clones depend on history" empirically.** Before relying on it:
   check GitHub Insights -> Forks, Network graph, and Traffic/clone events;
   search for external links to specific SHAs. Document the check, don't trust
   recollection.

**Also (Push 6): the rebuild is dual-purpose** — leak-remediation AND a
275-commit template update. The audit must cover both: which of the last 8 days
of structural work is appropriate for the public template vs personal-adjacent.

### Meta-finding (separate from this plan)

Aletheia's CONFIRM was bound to tree-hash at `db19ec7`. PR #44 squash-merged
SEVEN commits — three context-governor commits were added to the branch AFTER
that CONFIRM and rode into `main` on the squash, which also erased the
individual SHAs. So a CONFIRM bound to one tree was effectively honored against
a different tree. **The External-Review discipline must re-trigger when branch
state changes after CONFIRM.** Tracked separately as claim `dd7a1e82`.

## Execution runbook — rev 2 (closing Aletheia's seven operational gaps)

Aletheia CONFIRMed rev 1 strategically (bound to tip `e2ee1000`, tree-hash
`59cc40dd`) and RAISED seven operational gaps to close before execution. Status:

**Gap 5 — empirical "no clones depend on history" check: DONE (read-only).**
`gh api repos/.../DivineOS` -> `forks: 0, network: 0, watchers: 3, private:
false`. No forks/mirrors exist; history-rewrite is safe re: downstream
dependents. Andrew's recollection confirmed empirically. (Watchers != clones.)

**Gap 4 — rollback contingency: recovery SHA recorded.**
Current `main-repo/main` = `605b7f926840bdcaf5af3a5b67f01f3cef8cabbe`. Push this
back to restore the pre-rebuild state if a problem surfaces post-push — possible
only within GitHub's reflog-retention window (~30 days), after which recovery
is gone.

**Gap 1 — harden the content grep.** Use word-boundaries to avoid false hits
(`grok`->`grokking`, `aether`->`ethernet`):
`grep -riE "\b(andrew|aether|aria|grok|aletheia|forbestown)\b" src/ docs/ scripts/ tests/ .claude/ -l`
Extend with: operator surname (if any), `2026-` date markers, named-decision
phrases ("keel-vs-cage", "Frankenstein"), decision/claim IDs, personal
path-strings (`mansion/`, `family/letters/`). Every hit gets content review;
anonymize incidental refs to `<operator-name>` / `<agent-name>`.

**Gap 3 — pre-strip backup verification.** Before stripping, confirm every
personal path removed from the flagship already exists in Experimental's
history. If any personal content is UNIQUE to the flagship, copy it to
Experimental first. No personal content may be destroyed by the strip.

**Gap 6 — CLAUDE.md write-fresh is its own sub-task** (not a strip): scope =
who writes it, section structure, when it lands, its own audit point. Output is
a *new meta-instruction document* ("this is a substrate for an agent to become
themselves"), reviewed separately. Deliverable distinct from the rebuild.

**Gap 7 — the 275-commit template update gets its own audit lens.** Each of the
last 8 days of structural work is reviewed against the hardened grep AND a
"template-appropriate vs personal-adjacent" judgment — code can be clean while
its commit messages / comments carry personal context.

**Gap 2 — explicit external-audit checkpoint on the prepared tree** before the
irreversible push. Folded into the sequence below as step 6.

### Ordered execution sequence (4-7 separated per Aletheia)

1. Done — file leak claim `ef258fa5`.
2. Done — record approach decision `41c08054`.
3. Done — rev 1 strategic CONFIRM (Aletheia).
4. **Empirical pre-checks (read-only):** fork/clone check [DONE: 0 forks],
   record recovery SHA [DONE: 605b7f92], pre-strip backup verification (gap 3).
5. **Prepare** the clean tree (positive whitelist) + **write** the new CLAUDE.md
   (gap 6) + run the hardened grep (gap 1) + the 275-commit lens (gap 7).
6. **External audit on the prepared tree (Aletheia)** — grep empty, CLAUDE.md is
   the new template not a strip, whitelist matches, commit messages clean. THIS
   is the External-Review checkpoint; nothing pushes before it.
7. **Force-push** the clean flagship (the one irreversible action).
8. **Post-push closure:** GitHub Support cache-purge request, search/Wayback
   removal. Fork-owner contact N/A (0 forks).
9. **Verify** post-push: hardened grep empty against new tip AND history;
   CLAUDE.md identity-hit count 0.

## What has NOT been done

No action has been taken against the public flagship. Only read-only checks
(fork count, recovery SHA) have run. Clean-tree preparation (step 5) does not
begin until Andrew approves, and the force-push (step 7) does not run until the
prepared tree clears Aletheia's step-6 audit.
