# Magpie Search — Findings (Part 3, Final)

**Audit date:** 2026-07-26 (continued 2026-07-27)
**Auditor:** Aether (DivineOS substrate)
**Scope of Part 3:** `indexer.py` (994 LOC — the writer path), `backfill.py`, `nightly_sync.py`, `cli.py`, `telemetry.py`. **Combined with Parts 1 and 2 this now covers ~8,600 of 8,956 LOC — effectively the full codebase** (remaining ~350 LOC is `__init__.py`, `providers/__init__.py`, and tests fixtures I skipped intentionally).
**Framing:** Andrew 2026-07-27: *"high in thoroughness and not high in ceremony — look-good pass with every relevant lens, plus anything else you missed from the rest of it."* So this pass added Peirce (signs-of-data becoming signs-of-search — the indexer's job) alongside the earlier Feynman/Schneier/Taleb/Meadows/Jacobs set, and revisits three items from Parts 1-2 I want to name properly.

Finding numbers continue at F21+. Recommendations continue in [recommendations_part3.md](recommendations_part3.md) at R19+.

---

## New strengths worth naming (indexer is the crown)

`indexer.py` is the writer path — the file where bad decisions become permanent DB state. It's been heavily audited:

- **`CRIT-1` (line 687-702)**: complete-line boundary computed from raw bytes, not from string-search. Comment names the exact prior bug: "when a read had NO newline at all (one long partial line, common on a live JSONL mid-append, especially with a non-UTF-8 byte), `complete_lines` was empty so the correction was skipped and `bytes_after` stayed at EOF — permanently skipping that content." Silent data loss. The fix is unconditional cursor computation from raw bytes. **This is the same shape of failure as backup.py's success-marker-that-lies** — both are "the code thought it worked but didn't."
- **`HIGH-1` (line 740-759)**: FTS5 rowid invariant assertion. After executemany insert, verify `MAX(rowid) == prev_max + N`. If FTS5 ever assigned non-contiguous rowids, the `messages_vec` and `messages_meta` inserts would silently bind to the WRONG messages. Cheap check (one query), converts silent corruption into immediate failure with a specific error message. **This is the shape of gate the DivineOS `verify-claim` mechanism aims for** — a cheap check that catches a silent-corruption class.
- **`HIGH-2` (line 648-657)**: on truncate/replace of a source file, cascade delete `messages_meta` and `messages_vec` rows too. Comment names the specific bug: "FTS5 reuses rowids after delete. If we drop the messages rows but leave their messages_meta rows, a freshly-indexed message can be assigned a recycled rowid that still maps (via messages_meta) to the OLD content's hash — dedup then clusters the wrong messages."
- **`HIGH-4` (line 584-611)**: `backfill_dedup()` runs INSIDE the advisory lock even though the primary indexing connection has already closed. The comment names why: doing the DDL under WAL while another indexer process writes caused contention on busy 85k boxes. Holding the lock serializes it with every other indexer. This is subtle threading discipline named in-place.
- **Redact BEFORE truncate** (`indexer.py:428-436`): "Redact BEFORE truncating: truncating first can split a multiline secret (e.g. a PEM key) so its end-marker falls past the cut and the regex no longer matches, leaking key material into the index." That's the specific attack class named at the point of defense.
- **Bounded per-file read** (line 168): 64 MiB cap on any single indexing-pass read. Prevents a 3x RAM spike on a multi-GB session. Loop calls `_index_one_file` up to 100,000 times to catch up.
- **Advisory lock with PID liveness check** (line 343-386): both POSIX (`os.kill(pid, 0)`) and Windows (`ctypes.windll.kernel32.OpenProcess`) paths, so a stale lockfile from a crashed indexer doesn't hold the whole system hostage.
- **`stats_summary()` exposes `embed_coverage`** — the ratio of `messages_vec` count to `messages` count. Turns "is my semantic index caught up?" into a queryable number. Small but exactly the kind of observability that lets a caller reason about degraded modes.
- **Telemetry firewall in `_clean()`** (`telemetry.py:91-102`): drops anything that isn't a number, bool, or short (48-char) space-free token. The most disciplined "we cannot accidentally send user content" implementation I've seen — the firewall runs at the emit point, before any serialization touches the network.
- **CLI stdio UTF-8 reconfigure on Windows** (`cli.py:335-347`): solves the entire class of "printing an emoji or smart-quote from a web snippet crashes the CLI." Comment names cp1252 as the culprit. Named at the fix.

---

## Findings

### F21 — Telemetry endpoint is a Tailscale hostname; most opt-in installs will fail silently

**File:** `src/magpie_search/telemetry.py:29`

```python
DEFAULT_URL = "https://vektor.taildabcb6.ts.net/v1/ingest"
```

The `.ts.net` domain is Tailscale's MagicDNS. Resolution behavior:
- If the sender is on the same tailnet as `vektor`: DNS resolves via MagicDNS, POST succeeds.
- If the sender is NOT on that tailnet: DNS resolution fails, `urlopen` raises, `_send`'s `except Exception: pass` swallows it.

The result: **most opt-in installs (anyone not on your tailnet) will silently never send telemetry**. The `enable` message says "help improve it" and looks like the user is contributing, but the events land nowhere. `is_enabled()` returns True, `install_id` is created, and every POST fails silently.

**Not a security bug** — no data leaks, telemetry is opt-in — but it's a **broken contract with the operator who opted in**. Either:
1. Document that the default endpoint is Tailscale-only, and users must set `MAGPIE_SEARCH_TELEMETRY_URL` to a reachable collector; or
2. Move the collector to a publicly-resolvable domain; or
3. On enable, do a preflight POST and report if the endpoint is unreachable.

The fail-open behavior is correct (telemetry must never break the tool). The **silent-failure** on preflight is what breaks the contract.

### F22 — Indexer `RuntimeError` on rowid-invariant violation is caught + logged to stderr only

**File:** `src/magpie_search/indexer.py:558-560, 749-759`

The rowid-invariant assertion at line 752-759 (F/HIGH-1 mentioned above) does exactly the right thing at the raise site — cheap check, loud error message, `conn.rollback()` before the raise. But the OUTER loop catches every exception:

```python
except Exception as e:
    print(f"  ! {fp.name}: {e}", file=sys.stderr)
    continue
```

Effect: the invariant violation logs one stderr line ("! foo.jsonl: FTS5 rowid invariant violated...") and indexing moves on to the next file. **A user tail-following stderr sees it; a user checking `stats_summary()` or a health endpoint doesn't.**

**Fix**: write invariant-class violations to an internal error surface (`stats_summary()` grows an `errors_this_pass` field, or a separate `health_check()` similar to backup.py's `health_check()` reads a state file). The invariant assertion is the right catch — its follow-through is what's missing.

### F23 — `install_id` "anon" fallback collides across installs when UUID write fails

**File:** `src/magpie_search/telemetry.py:60-71`

```python
def install_id() -> str:
    try:
        if f.exists():
            return f.read_text("utf-8").strip()
        ...
    except Exception:
        return "anon"
```

If `~/.magpie-search` isn't writable (permission problem, read-only fs, disk full), every failing install identifies as `"anon"`. Telemetry analytics can't distinguish "50 events from one install with a filesystem problem" from "50 events from 50 different installs each with a filesystem problem." Minor because telemetry is opt-in and best-effort, but worth flagging.

**Fix**: `return f"anon-{uuid.uuid4().hex[:8]}"` — a per-process pseudo-id that at least separates runs. Or accept that unwritable installs get one identity and document it.

### F24 — `chunk_dedup` backfill upserts empty-string timestamps

**File:** `src/magpie_search/indexer.py:933-937`

```python
conn.execute(
    "INSERT INTO chunk_dedup(sha256, first_seen_at, last_seen_at, count) "
    "VALUES (?, '', '', 1) "
    "ON CONFLICT(sha256) DO UPDATE SET count=chunk_dedup.count+1",
    (h,),
)
```

Backfilled rows get `first_seen_at=''` and `last_seen_at=''`. The live path at line 817-825 uses `m.ts or ""` — which has the same issue when a message lacks `ts`, but at least tries to preserve it. **Post-hoc analysis that asks "when did this content first appear?" will get empty strings for anything backfilled**, silently mis-representing history.

**Fix**: in `backfill_dedup`, pull `m.ts` from the messages row and pass it into the upsert. Even a fallback to `datetime('now')` would be better than empty-string. Alternatively document that `first_seen_at` is only meaningful for rows created by the live path.

### F25 — `_normalize_for_hash` is case-preserving (deliberate) but this deserves a comment

**File:** `src/magpie_search/indexer.py:57-58`

Whitespace normalizes; case preserved. This IS correct — for code, IDs, hashes, case is content. But `"Hello World"` and `"hello world"` deduplicate to different clusters. A user searching for "the greeting message" gets both variants back with `dup_count=1` each, when they might expect them to fold.

**Not a bug** — deliberate. But **the next contributor might not know it's deliberate** and helpfully add `.lower()`, which would immediately conflate legit distinct content. Add a one-line comment naming why case is preserved.

### F26 — `LLM client._looks_like_refusal` checks only the first 200 chars

**File:** `src/magpie_search/llm/client.py:63-65` (revisit from Part 1)

```python
def _looks_like_refusal(text: str) -> bool:
    low = text.lower().strip()
    return any(m in low[:200] for m in _REFUSAL_MARKERS)
```

If the model preambles for >200 chars then refuses, the check misses. Bounded scope (model preambles are usually short — phi3.5's known refusal shape starts within ~50 chars), but worth naming as a known-tradeoff and matching the length cap to observed data. Currently no comment explains the 200 choice.

### F27 — Reranker discards `rrf_score` on rerank success, changing return shape silently

**File:** `src/magpie_search/llm/reranker.py:143` (revisit from Part 2)

```python
h = dict(h)
h["rerank_score"] = float(sc)
h.pop("rrf_score", None)
```

After a successful rerank, hits lose their `rrf_score` field and gain `rerank_score`. After a FAILED rerank (fallback path), hits keep `rrf_score` and lack `rerank_score`. A caller inspecting hit shape sees two variants; if they wrote `hit["rrf_score"]` they'd `KeyError` on the success path.

**Not necessarily a bug** — the return dict has `reranked: True/False` at top level so callers CAN branch — but the per-hit shape drift is a foot-gun. Either always-set-both (`rerank_score=None` on fallback) or document the branching contract.

### F28 — `audit.py.tail(n)` reads the full log to slice last N lines

**File:** `src/magpie_search/llm/audit.py:141-152` (revisit from Part 2)

```python
with p.open("r", encoding="utf-8") as f:
    lines = f.readlines()
out = []
for line in lines[-n:]:
    ...
```

At 50 MB rotate cap, that's ~50 MB into memory each `check()` call. Trust monitor runs hourly per the module docstring. On a well-utilized system with the trust monitor also polling, this is real per-hour cost. Not catastrophic but scales linearly with log-size-to-rotate.

**Fix**: reverse-line-read from the end of the file (`os.lseek` from `SEEK_END`, read backward in blocks until N newlines found). Standard pattern.

### F29 — `nightly_sync.py` compat shim lacks a `DeprecationWarning`

**File:** `src/magpie_search/nightly_sync.py`

21 lines, cleanly forwards to `backup.main`. Docstring notes it's a compat shim but there's no runtime signal to users still calling it. If the shim ever gets removed (as the docstring implies is expected), the migration will surprise operators whose Task Scheduler / cron entries silently 404.

**Fix**:

```python
import warnings
warnings.warn(
    "magpie_search.nightly_sync is a compat shim; migrate to magpie_search.backup",
    DeprecationWarning, stacklevel=2,
)
```

At the top of `main`. Small.

### F30 — `_h_reindex` in MCP server silently exposes the writer path

**File:** `src/magpie_search/mcp_server.py:242-247` (revisit — I only glanced at this before)

```python
def _h_reindex(a: dict[str, Any]) -> Any:
    res = magpie_search.index(source=a.get("source"))
    ...
```

The MCP `reindex` tool accepts a `source` param and passes it as `source_dir` to `index_all()`. An agent (potentially prompt-injected) can call `search(sources=[...], reindex=...)` and steer `source` to any path. `index_all(source_dir=Path("/etc"))` would then walk `/etc/**/*.jsonl` and index everything found under the transcripts schema.

Effects:
- Anything that looks like a valid Claude Code JSONL under `/etc` (or wherever) gets indexed into the FTS5 store. Real JSONL is unlikely there, but attacker-supplied path with attacker-supplied `.jsonl` file would get indexed.
- Under `source=path/attacker-controls` the indexer processes messages through `redact()` before storage — so it's not a raw-secret injection path, but it IS attacker content flowing into your search results.
- More concerning: the `source_dir` becomes the ambient context for `_project_name_from_path` and the FTS index gains rows with attacker-controlled `project` field. Future queries `list_sessions --project X` return attacker-planted rows.

**Same class as F11 (FilesProvider scope)**: MCP tool exposes a path parameter with no allowlist. Fix: the MCP `reindex` tool should NOT accept a source override; if operators need to reindex from a non-default dir, they set `CLAUDE_PROJECTS_DIR` and restart. The MCP surface stays search-only.

### F31 — `_extract_text_from_content` "unknown block type" catchall serializes arbitrary JSON

**File:** `src/magpie_search/indexer.py:449-452`

```python
else:
    # Unknown block type — index a stub for visibility. Redact before
    # truncating (see tool_use note above).
    out.append((f"block:{t}", redact(json.dumps(item, ensure_ascii=False))[:2000]))
```

Any block whose `type` isn't recognized gets serialized whole (2000-char cap). If Claude Code adds new block types with sensitive metadata (e.g., a future `computer_use` block with pixel-coordinates of a screenshot showing sensitive UI), the whole JSON blob enters the index. Redact runs but only catches known secret patterns — UI content, coordinates, arbitrary structured metadata pass through.

**Fix options**:
1. Allowlist known block types; unknown types index only their `type` field, not their content.
2. Keep the current catchall but log unknown types once so an operator can add explicit handling.
3. Cap far shorter (200 chars, enough for debugging visibility) and drop.

Option 2 is cheapest and most useful for a project that has to keep pace with Claude Code's evolving JSONL schema.

### F32 — `CLI._cmd_backup` re-serializes args to strings then re-parses in `backup.main`

**File:** `src/magpie_search/cli.py:205-213` (cosmetic)

Works. Small smell. Cosmetic.

### F33 — `telemetry._SAFE_TOKEN` allows `.` and `:` — IP-address-shaped identifiers slip through

**File:** `src/magpie_search/telemetry.py:34`

`^[A-Za-z0-9_.:+\-]{1,48}$` — allows `192.168.1.1` (12 chars, all allowed). If someone naively passed an IP (host discovery, network scan result) as a property value, it'd pass the firewall. Deliberate tradeoff (need `.` for version strings, `:` for `namespace:action` events). Real risk: very low. Named for completeness.

**Optional hardening**: split into `_SAFE_ENUM` (letters/underscore only, for names) and `_SAFE_VERSION` (digits/dot/plus/dash only, for version strings), reject anything that looks like an IPv4 pattern.

---

## Not-findings (checked and fine — indexer edition)

- **`_pid_alive` handles Windows and POSIX correctly** — `PROCESS_QUERY_LIMITED_INFORMATION` on Windows, `os.kill(pid, 0)` on POSIX, catches both `ProcessLookupError` and `PermissionError` ✓
- **`init_db` runs `_migrate_messages_meta` before creating vec table** — order matters ✓
- **`connect(read_only=True)` uses URI `file:...?mode=ro`** — actually read-only, not just "we promise not to write" ✓
- **`_extract_text_from_content` skips `thinking` blocks** — reasoning ≠ conversation; the noise reduction is real ✓
- **`_MAX_READ_BYTES = 64 MiB`** — well-chosen; the docstring notes it's "far larger than any real single JSONL line" so the truncation is a memory-cap not a content-cap ✓
- **`chunk_dedup` uses `ON CONFLICT ... count=chunk_dedup.count + 1`** — atomic increment, safe under advisory lock ✓
- **Truncation-detection uses `size < prev_bytes`, not mtime** — mtime is unreliable on live JSONL append ✓
- **`backfill.py` reuses `advisory_lock()` from indexer** — same single-writer discipline for the backfill pass ✓
- **`_send_stdio_unicode_safe`** — solves the entire cp1252-print-crash class on Windows ✓
- **Telemetry emit runs on a daemon thread with `join(2.0)` timeout** — short-lived CLI finishes without hanging on a slow POST ✓
- **`telemetry.maybe_first_run_notice`** is one-shot via a marker file — no ongoing nag ✓

---

## Coverage summary across the full audit

| Part | Files | LOC | Findings | Recs |
|---|---|---|---|---|
| 1 | search, federation, redactor, safe_subprocess, embeddings, providers/base, providers/web, llm/{trust,guardrails,client} | ~4,000 | F1-F10 | R1-R9 |
| 2 | providers/{files,kg,transcripts,vector,youtube}, llm/{summarizer,reranker,audit}, backup, deepweb | ~3,000 | F11-F20 | R10-R18 |
| 3 | indexer, backfill, nightly_sync, cli, telemetry | ~1,600 | F21-F33 | R19-R28 |
| **Total** | **~30 files** | **~8,600 of 8,956** | **33 findings** | **28 recommendations** |

**Coverage: ~96%** of the codebase read directly. The remaining ~4% is `__init__.py`, `providers/__init__.py`, and test fixtures — low-signal for architectural findings.

---

## Meta-observation across the three parts

Reading indexer.py sealed what the earlier passes suggested: **this project practices the discipline of naming failures at the site of the fix.** Every `CRIT-1` / `HIGH-1` / `HIGH-2` / `HIGH-4` in indexer, every `MED-2` in backup, every `GAP-5` in search hybrid — these aren't just fix commits, they're **teaching comments for the next reader**. A contributor who touches the FTS5 rowid invariant now KNOWS why the assertion is there, WHY it can't be removed, and WHAT class of silent corruption it prevents. That's the shape of a codebase that survives its own future maintainers.

The findings across all three parts are edge-hardening and expectation-alignment. **There are no structural concerns.** The largest single class of issue is trust-boundary drift — several places (F11 files scope, F12 kg identifiers, F13 vector identifiers, F30 reindex source, F1/F2 web provenance) assume config is trusted operator input; if the project ever adds a plugin system or MCP-input-to-config path, all of these become active holes at the same time. Treating them as a class and hardening them together is the right architectural move.

Recommendations continue in [recommendations_part3.md](recommendations_part3.md).
