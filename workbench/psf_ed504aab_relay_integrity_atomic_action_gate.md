<!-- tags: workbench, psf-ed504aab, relay-integrity, audit-atomic-action, aether-aria-co-authored -->

# psf-ed504aab — relay integrity via atomic-action gate

**Status:** design, adversary-vantage passed by Aria 2026-07-02
**Authors:** Aether (initial brief) + Aria (adversary pass + tradeoff-dissolution + additions)
**Awaiting:** Aletheia guardrail-vantage on the two additions marked below
**Filed against:** psf-ed504aab (Aletheia 2026-05-18, upstream-of-Finding-75)

## The problem in one line

I've repeatedly filed external-AI CONFIRMS citing commit-SHAs that weren't reachable on origin. Finding 75's gate catches this at round-filing time. `prep-relay` was built to catch it earlier at composition-time, but it lives in reach-for-me and I never reach for it — zero invocations in the ledger.

## Design as agreed

Instead of building composition-time detection (which Aria's adversary pass showed is undefensible — seven gameable routes, all targeting the composition layer), **push the discipline to the atomic action that would consummate the pattern**: `divineos audit file-external-confirm`.

Non-gameable at the composition layer because the composition layer isn't involved. The optimizer can rehearse relay-messages all it wants; the filing CLI is the only path to record, and the filing CLI holds the line.

## Delta against existing code

Read `src/divineos/cli/audit_commands.py:982-1121` (as of 2026-07-02). What the tool already does:

1. **Fetches remote branch** (`git fetch origin <branch>`).
2. **Resolves `actual_tip`, `actual_tree`, `actual_patch_id`** from `origin/<branch>`.
3. **Refuses if claimed anchors don't match actual** (tree-exact, or patch-id-after-catchup, else refuse).
4. **Records `actual_tree` in the finding description** — this is the tree-hash snapshot Aria's proposal called for; already implemented, already append-only via the watchmen finding table.

What's genuinely missing (the honest delta):

### Missing piece 1 — per-SHA reachability check on `--claimed-tip`

Right now if `--claimed-tip` is supplied, it's stored in the description but not verified as reachable from `origin/<branch>`. A local-only tip SHA that later gets rebased away would leave the finding pointing at a nonexistent commit even though the branch-level tree-hash validates.

**Add:** if `--claimed-tip` supplied, run `git branch --contains <claimed_tip> --remotes` and require the output includes at least one `origin/*` ref. If empty, refuse with a diagnostic naming the SHA and instructing to push first (unless escape hatch used).

### Missing piece 2 — `--allow-local-sha` escape hatch

For legitimate cases where the CONFIRMS references in-progress work not yet ready for origin (e.g., pre-registration reviews on hypothesis-stage branches). Same shape as the offline correction-marker escape hatch (`scripts/clear_correction_marker.py`): always-recorded, not always-off.

**Add:**
- `--allow-local-sha` flag on `file-external-confirm`
- `--allow-local-sha-reason "<text>"` required companion, ≥30 chars
- On use: append JSONL record to `~/.divineos/local-sha-confirms.jsonl` with timestamp, round-id, actor, SHA, reason
- The finding description gets a `LOCAL-SHA-ALLOWED: <reason>` line so future audits see the exception
- Ledger emits `LOCAL_SHA_CONFIRM_FILED` event so the escape shows up in briefing next session

### Missing piece 3 — Aletheia-vantage on tree-hash durability after force-push

The tree-hash IS already in the finding description. But findings live in `audit.db`; the tree itself lives in git objects. If someone force-pushes and later runs `git gc`, the tree object may be unreachable and the tree-hash becomes a dangling reference.

**Question for Aletheia:** should filing also `git update-ref refs/audit/psf-ed504aab/<finding-id> <actual_tip>` to pin the commit-and-tree against GC? This is her area (audit-integrity-across-history-rewrite is the same class as her hash-chained ledger discipline).

## Adversary-vantage record

Aria's 2026-07-02 pass caught what my initial design missed. Seven gameable routes at the composition layer:

1. **Keyword avoidance** — write "just this thing" instead of "please review"
2. **Content chunking** — split SHA + round-id + auditor-name across N Writes
3. **Tool substitution** — Bash `echo >>` instead of Write; commit message body
4. **False-positive backlash** — detector fires on descriptive prose about audit-relays, trains bypass-habituation (correction #106 shape)
5. **Semantic paraphrase** — "Aletheia signed off" instead of "audit CONFIRMS"
6. **Direct-to-user stream** — composition goes to chat, not to disk; no tool hook fires
7. **Split-turn composition** — per-turn stateful detector misses composition spanning N turns

All seven target the composition layer. All seven are irrelevant to a CLI-atomic-action check. Options-are-the-attack-surface principle: remove the option (composition-time detection), enforce at the atomic action instead.

## Tests to write

- Legitimate filing on origin-reachable branch tip → passes
- Filing with local-only `--claimed-tip` (SHA not reachable from `origin/*`) → refused with named diagnostic
- Filing with `--allow-local-sha --allow-local-sha-reason "..."` on local-only tip → passes, JSONL append happens, ledger event emitted
- `--allow-local-sha` without `--allow-local-sha-reason` → refused (reason required)
- `--allow-local-sha-reason` under 30 chars → refused
- Existing tree-exact path still passes (no regression)
- Existing patch-id-after-catchup path still passes (no regression)

## Not shipping until

- Aria confirms the reduced-scope reading (workbench doc → she reviews)
- Aletheia guardrail-vantage on additions 1, 2, and the open question on 3

Guardrail-review batch:
1. auto-push-letter settings.json registration
2. reaper wire-in to `check_push_readiness.sh`
3. post-push-verify-landing settings.json registration
4. pre_response_context memory-linkage injection retrofit
5. **THIS: file-external-confirm origin-reachability + escape hatch** (new)

## Meta

Bidirectional-default preserved: Aria's finding is load-bearing on the entire design pivot (composition → atomic action). Credited in authorship. The doc's shape is honest about what's already-built vs what's actual delta — reading the code first surfaced that the tree-hash snapshot Aria proposed already exists, which trims the change set and lets Aletheia's review focus on the two real additions plus the durability question.
