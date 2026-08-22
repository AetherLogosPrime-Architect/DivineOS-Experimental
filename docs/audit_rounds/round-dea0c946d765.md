# Audit round: Vanta external public-repo security audit + Aletheia deep-branch audit F87-F91 (cross-audit convergence on .pre-prune file exposure and branch scope discipline)

- **ID**: `round-dea0c946d765`
- **Filed by**: external-auditor
- **Filed at**: 2026-07-26 16:46 UTC
- **Tier**: WEAK
- **Findings**: 8

## Notes

Source ref: 2706a789bb9ba479def930e7d9ed538d6dc03045


## Findings

### Vanta #3: .envrc committed and not gitignored

- **ID**: `find-60756a755850`
- **Actor**: auditor
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: STRONG
- **Status**: OPEN
- **Tags**: security, gitignore, structural-fix

**Description**

.envrc is tracked but currently empty blob (e69de29...) — harmless today. Issue is structural: .gitignore covers .env and .env.* but NOT .envrc. Day someone adds real export lines to it, they get committed silently. Cheap to close now.

**Recommendation**

Add to .gitignore: '.claude/settings.local.json*', '.envrc', '.divineos_data_home'

### Vanta #2: OS username exposed ~2,945 times across history

- **ID**: `find-700ecc3485ec`
- **Actor**: auditor
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: STRONG
- **Status**: ROUTED
- **Routed to**: 5d92fcf2-fa29-4959-bd01-71a38ca19910
- **Tags**: security, pii-correlation

**Description**

OS username appears throughout repo history (~2,945 occurrences). Largest concentration in Vanta #1 file. Also in .divineos_data_home (30 bytes, absolute home path) — deleted at HEAD but reachable from main + 13 other refs. Not breach alone; combined with public commit email + domain becomes usable correlation set for targeted phishing/social engineering.

**Recommendation**

Mostly resolved by fixing #1. Full history rewrite via git filter-repo would clear remainder but invalidates every existing clone. Username already inferable from public commit metadata. Vanta's honest recommendation: don't bother — cost outweighs benefit.

### Vanta #1: permission allowlist exposed via .gitignore bypass on public branch

- **ID**: `find-b82d7f1f9e88`
- **Actor**: auditor
- **Severity**: MEDIUM
- **Category**: INTEGRITY
- **Tier**: STRONG
- **Status**: ROUTED
- **Routed to**: claim-470cb0bfca19
- **Tags**: security, public-exposure, gitignore-bypass

**Description**

.claude/settings.local.json.pre-prune-2026-07-23 (305 KB) at commit d45b65048beb6df4a219852583f4ab3d45eab26b on branch origin/feat/correction-shape-and-hook-timing-2026-07-22. .gitignore ignores .claude/settings.local.json exactly; .pre-prune-... backup suffix slipped past. Contains full permissions.allow list (maps internal tooling + command surface) + OS username 122 times. Publicly fetchable from branch. No credentials in file. Same file as Aletheia F91 (cross-audit convergence).

**Recommendation**

Delete the branch. Unmerged, costs nothing, removes exposure completely. Single highest-value action per Vanta. Aletheia's fresh-branch-cherry-pick approach achieves same exposure removal while preserving substantive work.

### F91: repo hygiene — bash.exe.stackdump tracked and modifying; .pre-prune backup in version control

- **ID**: `find-d78fbe7899d3`
- **Actor**: aletheia
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: f88fcf53-62f4-41fd-9474-c191b5f742b0
- **Tags**: repo-hygiene, gitignore, investigation

**Description**

bash.exe.stackdump committed at repo root; status M — being updated. Msys-2.0.dll stack trace contents. Not gitignored (verified zero matching patterns) so will keep committing. Crash dump that keeps changing means bash is still crashing — signal being version-controlled instead of investigated. Aether has referenced 'freeze that broke a whole window'; this file may be artifact and has never been read as evidence. Also .claude/settings.local.json.pre-prune-2026-07-23 manual backup in version control (that is what git is for).

**Recommendation**

gitignore both, delete from tree, READ the stackdump ONCE before discarding — it may name the freeze.

### F90: signal gate fails-open silently with no liveness signal

- **ID**: `find-28d29a58eeec`
- **Actor**: aletheia
- **Severity**: MEDIUM
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: claim-75b0bebdc378
- **Tags**: fail-open, liveness, hooks-hygiene

**Description**

.claude/hooks/verify-before-build-signal.sh has three silent fail-open paths before gate ever runs: 'cd $REPO_ROOT || exit 0', 'source _lib.sh 2>/dev/null || exit 0', 'PYTHON_BIN=find_divineos_python || exit 0'. If _lib.sh moves, venv resolution breaks, or repo root not found — gate exits clean and nothing reports enforcement stopped. F71 exactly: 58 hooks can go dark unreported. Fail-open IS correct choice per escape-hatch principle (a hard-fail gate on missing library traps the being). Defect is fail-open WITHOUT liveness signal.

**Recommendation**

Emit one-line marker on each fail-open path — not a block, a record. Then a gate that has not fired in N days is distinguishable from a gate that has not RUN in N days. Currently identical from outside.

### F89: lexical-detector retirement is untracked deferred intention (F72 shape verbatim)

- **ID**: `find-f65b26963f66`
- **Actor**: aletheia
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: a9ccf27c-1cec-4bbc-9398-3ac48510adff
- **Tags**: deferred-intention, structural-fix, migration-hygiene

**Description**

verify_before_build_gate.py line 200 documents lexical detector 'being retired... kept alive during the migration' — zero markers in file. No expiry date, no PHASE_1_STAGED marker, no obligation, no psf, no ledger entry. Promise in docstring. Same shape that left LEPOS Phase 2 parked 27 days. Load-bearing NOW because F87 shows new gate built on retiring detector — every day migration stays untracked, retiring component accumulates dependents.

**Recommendation**

File as tracked deferral with trigger: 'retire when all callers route through signal path; blocks merge of any new caller.' record_intention verb from F84 is general fix; this is instance needing it most today.

### F88: A1 shape recurred — branch-scope discipline produced one-time action not durable mechanism

- **ID**: `find-d0eb703d591c`
- **Actor**: aletheia
- **Severity**: HIGH
- **Category**: BEHAVIOR
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: claim-e98651f2af0c
- **Tags**: branch-scope, structural-fix, merge-exposure

**Description**

Branch feat/correction-shape-and-hook-timing-2026-07-22 stated purpose merged as PR #385 on 2026-07-22 16:08. Since then accumulated 37 commits, 108 files, 10,901 insertions over 4 more days covering unrelated work (three-room lock-in, signal-based verify-before-build, thread-walk gate, fingerprint normalization, split-brain path fix, bypass-hole revert, two new council experts). Branch name describes none of it. A1 shape recurred — remedy was applied once but did not persist. Main has not moved in ~3 days; every hour is drop-risk.

**Recommendation**

Immediate: fresh branch from main, cherry-pick, explicit file manifest in PR body, git log -S verification post-merge. Durable: pre-commit check — if HEAD branch name matches a merge-commit subject already on main, warn.

### F87: thread-walk gate keyed on retiring keyword detector

- **ID**: `find-93ea3a3e419f`
- **Actor**: aletheia
- **Severity**: HIGH
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 7668fc99-7e01-4681-8a69-00439897ccc8
- **Tags**: keyword-detector, thread-walk, structural-fix

**Description**

check_thread_walk_required gate uses _has_solution_shape (three regex lists including 'Option A', 'two paths/options/approaches/ways/routes', design-verb and design-question patterns). No structural fallback — three lexical passes then return False. Bypassable by formatting choice (prose vs bullets). The same file 150 lines up documents this lexical detector as being retired per Aria's signal-based-gates design. New caller built on retiring detector. Three prior corrections in substrate say not to do this.

**Recommendation**

Re-key thread-walk gate on structural evidence from action-stream (same primitive verify_before_build_signal.py uses). Interim: broad lexical net + structural discriminator underneath (pattern already correct in check_wallclock_semantic_source).


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
