# Public Repo Security Audit — 2026-07-26

**Auditor**: Vanta (external actor, contacted Andrew via Discord)
**Method**: pattern-based scan of every blob in object store (11,780 objects, 1,753 commits, 16 branches, including deleted files still reachable from history)
**Scope**: `github.com/AetherLogosPrime-Architect/DivineOS-Experimental`
**Headline**: No live credentials. Nothing needs rotating.
**Received via**: Andrew, 2026-07-26

---

## Findings summary

### MEDIUM #1 — Permission allowlist exposed via .gitignore bypass

**File**: `.claude/settings.local.json.pre-prune-2026-07-23` (305 KB)
**Commit**: `d45b65048beb6df4a219852583f4ab3d45eab26b`
**Branch**: `origin/feat/correction-shape-and-hook-timing-2026-07-22`
**Root cause**: `.gitignore` ignores `.claude/settings.local.json` exactly; the `.pre-prune-...` backup suffix slipped past the rule.
**Exposure**: contains full `permissions.allow` list (maps internal tooling + command surface) + OS username 122 times. Publicly fetchable from the branch.
**Credential check**: no credentials in the file.
**Fix**: delete the branch. Unmerged, costs nothing, removes exposure completely. **Single highest-value action per Vanta.**
**Cross-reference**: Aletheia F91 (2026-07-26 audit) also flagged this file as repo hygiene issue.

### LOW-MEDIUM #2 — OS username exposed ~2,945 times across history

**Files/paths**: username appears throughout history. Largest concentration in file from #1. Also in `.divineos_data_home` (30 bytes, absolute home path), deleted at HEAD but reachable from main + 13 other refs.
**Exposure model**: username alone is not a breach; combined with public commit email + domain, becomes a usable correlation set for targeted phishing / social engineering.
**Fix**: mostly resolved by fixing #1. Full history rewrite via `git filter-repo` would clear remainder but invalidates every existing clone. Username is already inferable from public commit metadata.
**Vanta's recommendation**: don't bother with filter-repo — cost outweighs benefit.

### LOW #3 — .envrc committed, not gitignored

**File**: `.envrc` (currently the empty blob `e69de29...`, harmless today)
**Issue**: `.gitignore` covers `.env` and `.env.*` but not `.envrc`. Structural bug: day someone adds real `export` lines to `.envrc`, they get committed silently.
**Fix**: gitignore addition (see below).

### Suggested .gitignore additions

```
.claude/settings.local.json*
.envrc
.divineos_data_home
```

---

## False positives (ruled out; documented to prevent future re-flag)

- **8 "credit card numbers"**: all fail Luhn. Floating-point artifacts (`4666666666666667` is 14/3 with decimal removed).
- **21 "public IP addresses"**: document section numbers like `3.2.3.1`.
- **~24 third-party home directories under benchmark/**: `/Users/mattia`, `/home/beda` etc. Upstream SWE-bench data scraped from public OSS issue text. Not ours.
- **Postal addresses**: matched code fragments.
- **One database URI with credentials**: fixture inside redactor tests.

---

## Limits of this review

- Pattern-based scan only. Strong on known credential shapes and structured PII.
- Cannot catch a secret with no recognizable shape — bare password in prose inside a markdown file would not be detected.
- Covering that requires human read of high-risk directories, not regex.

---

## Auditor's note

> "Nothing from your repo was copied, published, or shared anywhere; the clone was local and has been kept to a scratch directory."

Vanta offered to send scanner scripts if useful.

---

## Cross-audit convergence (2026-07-26)

Two independent audits (Vanta external, Aletheia internal-family) filed on same day converge on the `.pre-prune` file. Aletheia flagged as F91 repo-hygiene ("a manual backup file in version control. That is what git is for."). Vanta flagged as MEDIUM security exposure. Same file, different vantages, same fix recommendation.

Also converges on the branch itself: Aletheia F88 flags 10,901 insertions across 108 files sitting unmerged. Vanta's fix ("delete the branch") and Aletheia's fix ("fresh branch from main, cherry-pick, PR body manifest") both resolve the same underlying exposure while Aletheia's preserves substantive work.

**Combined fix shape**: fresh branch from main, cherry-pick clean commits (skipping the ones that added `.pre-prune` or `bash.exe.stackdump`), gitignore updates, merge fresh branch, delete old branch. Exposure removed AND work preserved.

## Priority for today

Per Andrew's 2026-07-26 09:42 directive (day just begun, full runway available), execution order:

1. **File this audit as watchmen round + route findings** (in progress)
2. **Add `.gitignore` entries** (Vanta #3 + protects against #1 recurring)
3. **Execute combined F88+F91+Vanta1 fix**: fresh branch, cherry-pick, delete old
4. **F87 thread-walk gate re-key on structural evidence** (Aletheia's second priority; the load-bearing catch)
5. **F89 tracked-deferral for lexical detector retirement**
6. **A2 room-gate trigger inversion**
7. **F90 liveness markers on fail-open paths**
8. **Harvest facts** (3rd ask carried forward)
9. **Read stackdump once before deleting** (F91)
