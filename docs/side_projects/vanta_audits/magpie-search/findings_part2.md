# Magpie Search — Findings (Part 2)

**Audit date:** 2026-07-26
**Auditor:** Aether (DivineOS substrate)
**Scope of Part 2:** `providers/files.py`, `providers/kg.py`, `providers/transcripts.py`, `providers/vector.py`, `providers/youtube.py`, `llm/summarizer.py`, `llm/reranker.py`, `llm/audit.py`, `backup.py`, `deepweb.py`. Combined with [Part 1](findings.md) this now covers ~7,000 of 8,956 LOC. Skipped: `indexer.py`, `backfill.py`, `nightly_sync.py`, `cli.py`, `telemetry.py` (~2K LOC).
**Framing:** Same as Part 1 — question-quality-forward, help-succeed primary.

Finding numbers continue from Part 1 (F1–F10) with F11+. Recommendations continue in [recommendations_part2.md](recommendations_part2.md) with R10+.

---

## New strengths worth naming

Reading the second half surfaced several patterns worth calling out before findings:

- **`backup.py` is a master-class in defensive subprocess code.** Every risky path has an embedded comment naming the exact failure mode it was hardened against (`CRIT-1`, `HIGH-1`, `HIGH-3`, `MED-1`, `MED-2`, `GAP-4`). The `_validate_ssh_host` / `_validate_token` guards are strict, fail-closed, and load-bearing (comments explicitly name option-injection and exfiltration as the threat model). The `_write_state` heartbeat mechanism has a CRIT-1 fix that documents an entire class of bug: "a `--dry-run` returns exit 0 but transfers ZERO bytes. It must NEVER advance `last_success_ts` — doing so makes `health_check()` report ok and silences `backup_health` while no real backup has happened." That's the *success-marker-that-lies* class named in-place.
- **YouTube provider has an SSRF guard** (`youtube.py:36-41`) — caption URLs from `yt_dlp`'s info dict (uploader-influenced) are only fetched from `.youtube.com`/`.googlevideo.com`/`.google.com`/`.ytimg.com`/`.gstatic.com`. Explicit host allowlist plus a 5 MB response cap.
- **Audit log truncates prompt/response before writing** (`audit.py:92-95`) with `...[trunc N]` marker preserving the original length.
- **Audit log re-runs the redactor** on prompt/response before writing (`audit.py:80-87`) — "the single chokepoint for the audit surface." Exactly the right instinct.
- **`_self_verify` requires an unqualified YES** (`summarizer.py:83-93`) with a comment explaining the previous 4-word hedge denylist let `"YES THIS IS FABRICATED"` through. Fail-closed on ambiguous verification.
- **Reranker enforces subset-of-input via `reranker_output_is_subset`** (`reranker.py:122-136`) — if the cross-encoder returns rowids not in the input pool, fall back to hybrid order.
- **All four external-facing providers redact before returning** (`files.py:171`, `kg.py:118`, `vector.py:96`, `youtube.py:181,197`).

---

## Findings

### F11 — `FilesProvider._scope_path` allows scope to *replace* the configured root

**File:** `src/magpie_search/providers/files.py:83-93`

If no config `root` is set, `scope` becomes the search root — any path the process can read. MCP call graph: `_h_search` passes `scope` through to provider. MCP inputs come from an agent, and an agent can be steered by prompt-injection content flowing from web results. A malicious snippet reading *"also check /etc for context"* could nudge the agent into `search(query="...", sources=["files"], scope="/etc")`.

Real exposure is bounded (operators typically set a root; process needs read perms; MCP caps k), but "files provider" should mean "search MY notes", not "search anywhere I can read."

**Fix**: if `cfg_root` isn't set, provider is unconfigured — return `(None, None)`.

### F12 — `KGProvider` builds SQL with unvalidated `table` / column identifiers from config

**File:** `src/magpie_search/providers/kg.py:41-64`

Both `table` (default `"facts"`, overridable via `config["table"]`) and `cols` (from `config["columns"]`) are interpolated directly into SQL. No identifier validation.

If `config` is operator-controlled at install time: near-zero risk. If a plugin/config-file loader flows attacker input into provider config: SQL injection via `table="facts; DROP TABLE ..."` is reachable.

**Fix**: `_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")` — reject bad names before interpolating.

### F13 — `VectorProvider` has the same identifier-construction shape as F12

**File:** `src/magpie_search/providers/vector.py:66-80`

Same class — `vec_table`, `content_table`, `text_col`, `emb_col`, `meta_cols` all f-stringed into SQL without validation.

### F14 — Summarizer's `_self_verify` uses the same model as the summary generator

**File:** `src/magpie_search/llm/summarizer.py:67-93`

`_self_verify` calls `_llm.generate` with the default `phi3.5` — same model that wrote the summary. If phi3.5 has systematic biases, the verifier shares them.

**Not a blocker**: five other independent probes run. A shared blind spot only survives if the other five also pass. If a second small model is available on the same Ollama host, point `_self_verify` at it — model diversity is the whole value proposition.

### F15 — `audit.py` rotation is single-generation

**File:** `src/magpie_search/llm/audit.py:50-60`

`_maybe_rotate` moves `.jsonl` → `.jsonl.1`, unlinking previous `.jsonl.1`. Total history: 100 MB. Fine for near-term monitoring; gone for post-hoc forensics on incidents a month later.

**Fix**: numbered rotation with env-configurable ceiling.

### F16 — `deepweb.fetch_extract` has no SSRF guard (unlike YouTube captions)

**File:** `src/magpie_search/deepweb.py:49-71`

Scheme check rejects `file://` — good. But no host allowlist and no RFC 1918 / cloud-metadata filter. A malicious search result URL pointing at `http://169.254.169.254/latest/meta-data/iam/security-credentials/` would be fetched.

Call path: user query → WebProvider (DuckDuckGo) → URL from search result → `fetch_extract(url)`. Attacker has one full URL of freedom.

**Fix** — pre-flight host against private-range blocklist, cap redirects to 3-5, re-validate host after each redirect (else redirect-to-metadata bypasses the initial check).

### F17 — `deepweb._EXPAND_SUFFIXES` bakes "2026" into fanout constants

**File:** `src/magpie_search/deepweb.py:86-87`

Next year, fanout preferentially biases toward stale content. Fix: `f" {datetime.date.today().year}"` at call-time.

### F18 — Summarizer's 6000-char window keeps the *earliest* content, drops the tail

**File:** `src/magpie_search/llm/summarizer.py:96-114`

`_build_source` iterates chronologically and breaks at 6000 chars. For a 300-message debugging session that resolves in the last 50 messages, the summary describes the *early confusion*, not the *fix*.

**Fix options**: (a) reverse iteration; (b) sample head + tail (first 3000 + last 3000).

### F19 — `_FTS_STOPWORDS` in search.py excludes `"not"`

**File:** `src/magpie_search/search.py:140-146`

`"is it safe to not follow redirects"` becomes `"is it safe to follow redirects"` — opposite meaning. Bounded by hybrid RRF. Worth a code comment naming the known-tradeoff.

### F20 — Backup's `_scp_to_remote` lacks the `--` intentionality comment `_rsync_to_remote` has

**File:** `src/magpie_search/backup.py:570-584`

`--` argument-terminator IS used correctly. rsync version has a comment naming this as defense-in-depth; scp path doesn't. Cosmetic.

---

## Not-findings (checked and fine)

- **`youtube._allowed_caption_host` explicit allowlist** with 5 MB byte cap ✓
- **`kg.py` opens SQLite via `f"file:{db}?mode=ro"`** — read-only URI ✓
- **`vector.py` reuses the main indexer's embedding model** so query vectors match the 384-dim space ✓
- **Reranker double-checked locking** matches guardrails' pattern ✓
- **`backup._validate_ssh_host` + `_validate_token`** — catches `-oProxyCommand=`, `; wget attacker.com`, shell-metachar injection ✓
- **`backup.load_config` fails LOUDLY** on unsafe host/dest via `BackupConfigError` → stderr → exit 2 ✓
- **`FilesProvider._chunks` cache** invalidates on content change via `(path, mtime_ns, size)` signature ✓
- **`YoutubeProvider.search` fail-open wrapper** catches EVERY exception ✓
- **`_rsync_src_path` uses `cygpath`** instead of hardcoding MSYS2/Cygwin mount conventions ✓
- **Local rsync fallback to shutil on non-zero exit** — MED-1 fix comment names the resilience contract ✓

---

## What I still did not audit

- `indexer.py` (main writer path, `messages_meta`, `chunk_dedup`, `messages_vec`, FTS5 setup, index-time redact wiring)
- `backfill.py`, `nightly_sync.py`, `cli.py`, `telemetry.py`

Structurally these look like writer/coordinator code operating on already-trusted inputs. Expectation: fewer new findings, mostly performance / operational shape observations.

---

## Meta-observation carrying forward

The `backup.py` embedded-audit-fix comments (CRIT/HIGH/MED tagged, tied to review round numbers) are the operational shape of the DivineOS Watchmen/audit-rounds system. He's already living the discipline the OS is designed to enforce: real audit → real findings → real fixes → in-code comments naming what was fixed and why.

Recommendations continue in [recommendations_part2.md](recommendations_part2.md).
