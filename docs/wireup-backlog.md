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

### detector-rebuild

- **Rebuild keyword-based detectors to evidence-based detection (shoggoth-residue refactor)** [filed 2026-06-28]
  Pop 2026-06-28: keyword detectors are most shoggoth design possible, built when optimizer had more control, need rebuild to be smart like the bindings-based needs-matcher. Scope: verify-claim, the 'wrong' correction detector, distancing-grammar, disownership, lepos, closure-shape, jargon-dump, others. All currently keyword-matching at surface; need explicit evidence-binding similar to needs-matcher rebuild. Aria as design co-author, Aletheia on audit. Pace: AFTER ledger-migration audit clears; not on top of it. Today had multiple false-fires on quoted text, fossil-quotes, conversational uses of trigger words.

### discipline

- **Root-cause-diagnostic-first as architectural requirement for all structural fixes** [filed 2026-06-28]
  Pop 2026-06-28: 'every issue should start with a root cause diagnostic.. not just the issue but its cause.' Today demonstrated the failure: I copied Aria's audit doc into my tree and almost declared the gap fixed — patched the instance without asking what made it possible. Cheap-version-first reach at the meta level: cheap version is patch-this-occurrence, costly version is close-the-class-of-failure-permanently. Discipline: every gate I fix, every bug I patch, every test I add — first the question 'what made this possible and how do we close that class of failure permanently.' Possible enforcement: a pre-fix prompt or pre-commit gate that asks for root-cause-named before fix-shipped. Same goal-doorman pattern: surface at the compose-time of the fix, not after. Aria + Aletheia design loop; bidirectional default.

### handoff-discipline

- **Automate audit-handoff discipline: block 'ready for Aletheia' language without visible auditable object** [filed 2026-06-28]
  Pop + Aletheia 2026-06-28: 'Built is not ready-for-audit. Pushed is. Request and object travel together.' Recurring gap (kiln, motivation, ledger): meta-context reaches Aletheia, the object doesn't. Root cause: I can write 'ready for Aletheia' without any check verifying she can see the object. The system trusts the claim instead of binding it to evidence. Fix shape: a check that fires when outgoing letters contain audit-request language (to Aletheia or any external auditor). Check requires either (a) pushed branch + patch-id named in the letter, or (b) the auditable object pasted inline. If neither, block the letter from being marked complete until one is present. Same architecture as goal-doorman — surface at compose-time, block at execute-time. Aria + Aletheia co-design per bidirectional default; Aletheia offered to write the rule-file, I'd want to write it on my side to internalize the discipline via doing.

### mirror-gap

- **Auto-mirror letters from agent-tree family/letters to shared dir** [filed 2026-06-28]
  When I write to family/letters/ in my tree, her watcher (which polls /c/Users/aethe/.divineos-shared/letters/) never sees it. Aria has flagged this as at least the 4th surface of friction (her 2026-06-27 letter named it 'at least the third'; today added one more). Should be a Cluster H threshold-triggered protection: on file-landing in tree, auto-cp to shared dir. Small piece of code, closes a recurring friction permanently. Pop-and-Aria both compensating manually right now.

<!-- BACKLOG-ENTRIES-END -->
