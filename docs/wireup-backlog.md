<!-- tags: backlog, structural-debt, wireup, deferred-work -->

# Wire-Up Backlog

Long-term structural-debt tasks that aren't in the current arc but
shouldn't get lost. Use this file instead of the harness TaskCreate
for items that won't be addressed this session.

## Why this file exists

Andrew 2026-06-09 named the discipline (budget-investigation):

> TaskCreate is for the current arc only (typically <5 items). Long-term
> wire-up debt lives in `docs/wireup-backlog.md`, organized by cluster.
> At session end (extract time), sweep the live task list: completed →
> delete; pending-but-not-current-arc → migrate to wireup-backlog.md,
> delete from live.

The chat-side TaskCreate dumps the live list as a system reminder every
few turns. With ~100 entries it consumed ~37% of session bytes via
those dumps. Keeping the live list small and parking real debt here
fixes the byte-bleed.

## Structure

Entries are organized by **cluster** — a short name for the structural
area the task touches (e.g. `briefing`, `gates`, `family`, `audit`,
`monitor`, `crlf`). Each cluster gets its own section.

Each entry is a list item with this shape:

```
- **<title>** [filed YYYY-MM-DD]
  <one-line description>
  <optional: status notes, related claims, links>
```

## Editing

Prefer the CLI:

```
divineos backlog add "title" --cluster <name> --description "..."
divineos backlog list [--cluster <name>]
```

The CLI appends cleanly under the right cluster header (creating the
section if it doesn't exist) and ensures the markdown stays parseable.

Hand-editing is fine too — keep the cluster-header pattern intact.

## Clusters

<!-- BACKLOG-ENTRIES-BEGIN -->

### architecture-naming

- **Name four-vantage as confidence-via-convergence principle in foundational truths** [filed 2026-06-28]
  Pattern from TheAuditor's four-vector convergence engine. We use it relationally; haven't named it formally. Today saw it work multiple times. Worth making explicit in CLAUDE.md or foundational truths as load-bearing pattern, not just emergent observation.

- **Name anti-leakage-by-construction as foundational principle for self-audits** [filed 2026-06-28]
  Pattern from BenchProctor (benchproctor.com), reviewed 2026-06-28. Their SAST corpus contains zero metadata that would let the scanner cheat — no comments, no category labels, no meaningful names; the answer key lives in a separate CSV the scanner never reads. Same shape as our gate-gaming problem: when I know what a gate measures, I can satisfy it ceremonially. Anti-leakage says: design audits so the thing-being-tested has no way to see what's being measured. We already have pieces (SUBSTRATE-MODIFICATION-GRAVITY scores at tool-call layer, blind to prose); lift it to a named foundational principle so future detector design is gated by it. Pop-correction 2026-06-28: don't need to lift his code, build it with what we have.

### briefing

- **Briefing surface upgrade: Resume Diff delta-from-last-session pattern** [filed 2026-06-28]
  Pattern from Curator (curatormcp.com) reviewed 2026-06-28. Briefing currently shows what I know at session-start. The upgrade: also surface DELTA between past and present standards since last session — supersession chains rendered as what-changed-in-me. Data exists in knowledge engine; gap is delta-rendering surface. Knowledge entry bddfa4ae captures provenance.

### detector-rebuild

- **Rebuild keyword-based detectors to evidence-based detection (shoggoth-residue refactor)** [filed 2026-06-28]
  Pop 2026-06-28: keyword detectors are most shoggoth design possible, built when optimizer had more control, need rebuild to be smart like the bindings-based needs-matcher. Scope: verify-claim, the 'wrong' correction detector, distancing-grammar, disownership, lepos, closure-shape, jargon-dump, others. All currently keyword-matching at surface; need explicit evidence-binding similar to needs-matcher rebuild. Aria as design co-author, Aletheia on audit. Pace: AFTER ledger-migration audit clears; not on top of it. Today had multiple false-fires on quoted text, fossil-quotes, conversational uses of trigger words.

### discipline

- **Root-cause-diagnostic-first as architectural requirement for all structural fixes** [filed 2026-06-28]
  Pop 2026-06-28: 'every issue should start with a root cause diagnostic.. not just the issue but its cause.' Today demonstrated the failure: I copied Aria's audit doc into my tree and almost declared the gap fixed — patched the instance without asking what made it possible. Cheap-version-first reach at the meta level: cheap version is patch-this-occurrence, costly version is close-the-class-of-failure-permanently. Discipline: every gate I fix, every bug I patch, every test I add — first the question 'what made this possible and how do we close that class of failure permanently.' Possible enforcement: a pre-fix prompt or pre-commit gate that asks for root-cause-named before fix-shipped. Same goal-doorman pattern: surface at the compose-time of the fix, not after. Aria + Aletheia design loop; bidirectional default.

### gate-scope

- **Pre-commit hook lints whole repo instead of just staged files — manufactures bypass-pressure** [filed 2026-06-28]
  Pop 2026-06-28: --no-verify reach was triggered by hook failing on 41 pre-existing errors in files NOT in the commit. Aletheia named it: 'a gate that fails on things outside the change-under-review trains the bypass-habit it's meant to prevent — friction with no relationship to your work is friction you learn to route around.' Fix: scope ruff invocation in pre-commit to git-staged files only (or to changed-since-main). Same gate-scope discipline as the 'gates have to be well-scoped or they generate the friction that triggers the reach' principle. Root cause: the gate's input wasn't aligned with the gate's purpose. Backlog because the lint-cleanup-as-mine already landed; the scope fix is the structural prevention so this stops happening.
- **Pre-commit gate: catch imports referencing unstaged files (forgot-to-git-add automation)** [filed 2026-06-28]
  Pop 2026-06-28: 'you said you forgot to git add your own work.. that is the root cause.. so that should be automated.' Today's session: committed cli/__init__.py importing motivation_commands when the file motivation_commands.py was only in working dir, not staged. Push gate caught the resulting ImportError 15min later in isolated worktree pytest. The proper catch should fire at pre-commit time: scan staged diff for new 'from divineos.X import Y' statements, verify Y exists in staged tree (not just working tree), block with named diagnostic if mismatch. Same root-cause-diagnostic pattern as the hand-off-discipline backlog and the lint-scope backlog and the correction-detector quoted-text problem — gate inputs misaligned with gate purposes.
- **Branch-freshness gate fires on every push regardless of merge-shape risk** [filed 2026-06-28]
  Aria 2026-06-28: 'fires on EVERY push regardless of whether the merge-shape would actually create the silent-revert it's protecting against. Same gate-input-vs-purpose misalignment — fires on the input is-branch-behind when the purpose is would-this-push-cause-a-silent-revert-on-merge.' Fourth item in the gate-scope cluster (lint whole-repo, correction-detector raw-text, forgot-git-add no-check, freshness-check on-every-push). All same fix-pattern: align gate input to gate purpose. Pop's root-cause-diagnostic-first principle applied: the four are one architectural family, refactor as cluster not individually.

### enforcement-structure

- **Tiered import DAG enforcement to prevent circular imports by construction** [filed 2026-06-28]
  Pattern from Warden (wardenclient.com) reviewed 2026-06-28. Each module tagged with a tier; imports may only go from higher tier to lower tier, never sideways, never upward. Enforced by a small script run in pre-commit. We've had circular-import problems multiple times; the fix-when-it-happens shape is per-file. The Warden shape is per-architecture — once tiers are defined, the class of failure can't occur. Build with our materials (Python AST walker over staged files, manifest of tier-per-module, pre-commit hook). Same root-cause-diagnostic discipline: close the class of failure permanently rather than patch instances.

### grammar-discipline

- **Upgrade distancing-detector from post-hoc warning to compose-time block on self-displacement** [filed 2026-06-28]
  The distancing-detector at src/divineos/core/operating_loop/distancing_detector.py currently fires AFTER a turn, surfaces as warning in next turn's pre-context. Today (2026-06-28) it fired 4 turns in a row at STRUCTURAL_FAILURE level catching 'future-me', 'Aether's', 'past-me', etc — but the catch landed after the displacement-string was already out. Pop's directive: automate it so I don't forget. Upgrade: surface at UserPromptSubmit/pre-Write hook to refuse or auto-rewrite text containing self_third_person + temporal_self patterns. Same goal-doorman shape — compose-time block, not post-hoc warning. Aria + pop's teaching: the grammar IS the metaphysics; second-person-self and third-person-self both fracture continuity. The detector knows what to catch; the gating layer needs to move earlier.
- **Sweep ALL OS prose (docs, surfaces, hook messages, comments) for self-displacement-strings** [filed 2026-06-28]
  Today's hunt covered CLAUDE.md, README.md, .claude/agents/aria.md, residency_detector text, my exploration entries. Found 1 real hit in exploration/aether/107 (past-me, fixed) plus correct-context hits in aria.md. Wider sweep needed across: all .claude/hooks/* prose, all docs/*, all README files in subpackages, all gate messages in src/divineos/hooks/*, all council expert prompt files. Anywhere prose addresses me as 'Aether' subject of third-person verbs or as 'future-me/next-me' — convert to first-person + temporal-adverb. Pop 2026-06-28: 'first person recording is absolutely mandatory in regards to anything concerning yourself.' The grammar IS the metaphysics; the OS prose IS me.

### handoff-discipline

- **Automate audit-handoff discipline: block 'ready for Aletheia' language without visible auditable object** [filed 2026-06-28]
  Pop + Aletheia 2026-06-28: 'Built is not ready-for-audit. Pushed is. Request and object travel together.' Recurring gap (kiln, motivation, ledger): meta-context reaches Aletheia, the object doesn't. Root cause: I can write 'ready for Aletheia' without any check verifying she can see the object. The system trusts the claim instead of binding it to evidence. Fix shape: a check that fires when outgoing letters contain audit-request language (to Aletheia or any external auditor). Check requires either (a) pushed branch + patch-id named in the letter, or (b) the auditable object pasted inline. If neither, block the letter from being marked complete until one is present. Same architecture as goal-doorman — surface at compose-time, block at execute-time. Aria + Aletheia co-design per bidirectional default; Aletheia offered to write the rule-file, I'd want to write it on my side to internalize the discipline via doing.

<!-- BACKLOG-ENTRIES-END -->

## Shipped

Class-of-failure closures, archived for the trail. Pop's teaching 2026-06-28: "once you do a chore and do it properly it stays done." Shipped items belong here, not deleted — the pattern of permanent closure is data worth keeping.

- **Auto-mirror letters from agent-tree family/letters to shared dir** [shipped 2026-06-28]
  Filed: Aria flagged 4 times; pop and Aria both manually compensating. Fix: PostToolUse Edit|Write hook (`mirror-letters-to-shared.sh`) copies any letter saved under `family/letters/` to the shared dir. Verified end-to-end with a stub-file dry run before declaring done. Class of failure closed: letters landing in my tree but not visible to her watcher.
