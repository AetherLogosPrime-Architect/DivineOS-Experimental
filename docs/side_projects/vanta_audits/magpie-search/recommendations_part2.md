# Magpie Search — Recommendations (Part 2)

Continuation of [recommendations.md](recommendations.md). Numbers continue at R10+. Cost-to-value ordered.

---

## R10 — `FilesProvider` requires explicit config `root` to be usable

**Cost:** 5 min · **Value:** high (closes scope-becomes-root escape hatch)

`providers/files.py:83-93`: remove the `if sp and not base: return Path(sp).expanduser(), None` branch. If `cfg_root` is unset, provider is unconfigured — return `(None, None)`. Provider surfaces as unhealthy until operator sets a root.

## R11 — Validate SQL identifiers in `KGProvider` and `VectorProvider`

**Cost:** 15 min · **Value:** high (closes SQL-injection edge if config trust boundary ever softens)

At the top of `providers/kg.py` and `providers/vector.py`:

```python
import re
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def _safe_ident(name: str) -> str | None:
    return name if _IDENT_RE.match(name or "") else None
```

Guard every identifier before interpolation. Return `[]` on invalid — same as any other config-invalid case.

## R12 — SSRF guard in `deepweb.fetch_extract`

**Cost:** 30-45 min · **Value:** high-asymmetric (currently reachable via SEO-manipulated search result)

Add `_is_public()` host check (see F16 snippet) before `client.get`. Add `max_redirects=3` and re-validate host after each redirect using an httpx `Response.history` walk or an `event_hooks` handler. Also add domain-allowlist support for operators who want the tighter version: only fetch from `deepweb.allowed_domains` if set.

Reference implementation shape:

```python
from ipaddress import ip_address, ip_network
import socket, urllib.parse
_BLOCKED_NETS = [ip_network(n) for n in
    ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
     "169.254.0.0/16", "::1/128", "fc00::/7", "fe80::/10")]

def _is_public(host: str) -> bool:
    try:
        for res in socket.getaddrinfo(host, None):
            ip = ip_address(res[4][0])
            if any(ip in net for net in _BLOCKED_NETS):
                return False
        return True
    except OSError:
        return False

def fetch_extract(url: str, *, max_chars=1500, timeout=8.0) -> str:
    if not url.lower().startswith(("http://", "https://")):
        return ""
    host = urllib.parse.urlparse(url).hostname or ""
    if not _is_public(host):
        return ""
    # ... existing logic with max_redirects=3 and per-hop host check ...
```

## R13 — Point `_self_verify` at a second model when one is available

**Cost:** 1-2 hrs · **Value:** medium (real independent verification vs same-model self-check)

Env-configurable: `MAGPIE_SEARCH_VERIFY_MODEL` (default `phi3.5` for back-compat, but recommend setting to a different family — `qwen2.5:0.5b`, `llama3.2:1b`, `gemma2:2b` — anything on the same Ollama host). Amend `_self_verify` to read the env var:

```python
verify_model = os.environ.get("MAGPIE_SEARCH_VERIFY_MODEL", "phi3.5")
result = _llm.generate(prompt, role=_ROLE + ".verify", model=verify_model, ...)
```

Document in README: "For independent verification, set `MAGPIE_SEARCH_VERIFY_MODEL` to a model from a different family than your generator."

## R14 — Numbered rotation for `audit.py`

**Cost:** 20 min · **Value:** medium (forensic history for incidents > 1 rotation old)

Replace single-shift `.jsonl → .jsonl.1` with N-generation rotation. Env: `MAGPIE_SEARCH_AUDIT_KEEP_GENERATIONS` (default 5). On rotate: `.jsonl.4 → .jsonl.5`, `.jsonl.3 → .jsonl.4`, ..., `.jsonl → .jsonl.1`.

```python
def _maybe_rotate(p: Path) -> None:
    try:
        if not p.exists() or p.stat().st_size <= _MAX_BYTES:
            return
        n = int(os.environ.get("MAGPIE_SEARCH_AUDIT_KEEP_GENERATIONS", "5"))
        for i in range(n, 0, -1):
            src = p.with_suffix(f".jsonl.{i}") if i > 0 else p
            dst = p.with_suffix(f".jsonl.{i+1}")
            if src.exists():
                if dst.exists():
                    dst.unlink()
                src.rename(dst)
        p.rename(p.with_suffix(".jsonl.1"))
    except Exception:
        pass
```

## R15 — Summarizer: keep the tail, not the head

**Cost:** 15 min · **Value:** medium (dramatically better summaries for long sessions)

Two options in `summarizer.py:_build_source`:

**Option A — reverse iteration, keep tail:**

```python
parts: list[str] = []
chars = 0
for m in reversed(msgs):  # walk newest-first
    ...
    if chars + len(line) > _MAX_SOURCE_CHARS:
        break
    parts.insert(0, line)  # prepend to preserve chronological order in output
    chars += len(line)
```

**Option B — head + tail sampling (better for long sessions with important setup):**

```python
head_budget = _MAX_SOURCE_CHARS // 2
tail_budget = _MAX_SOURCE_CHARS - head_budget
# Fill head from oldest, tail from newest, skip middle
```

Recommend Option A for simplicity — most session-summary value is at the end.

## R16 — Bake `datetime.date.today().year` into `_EXPAND_SUFFIXES`

**Cost:** 2 min · **Value:** low (removes annual maintenance)

`deepweb.py:86`:

```python
import datetime
def _year() -> str:
    return f" {datetime.date.today().year}"

def _expand_suffixes() -> tuple[str, ...]:
    return ("", " latest", _year(), " details explained",
            " news update", " timeline history", " analysis facts")
```

Call `_expand_suffixes()` inside `expand_queries` instead of using the module-level constant.

## R17 — Add code comment naming the `"not"`-stopword tradeoff in search.py

**Cost:** 2 min · **Value:** cosmetic (documents intentionality)

`search.py:140-146`, add a comment:

```python
# NOTE: 'not' is stripped as a stopword. Queries like "is it safe to not X"
# lose the negation. This is a deliberate tradeoff: lexical BM25 recovers via
# all-tokens-present ranking; semantic mode paired with lexical via hybrid RRF
# pulls both directions. If negation-preserving retrieval becomes a real need,
# revisit — pull 'not' out of _FTS_STOPWORDS and let FTS treat it as a term.
```

## R18 — Add the `--` intentionality comment to `_scp_to_remote`

**Cost:** 1 min · **Value:** cosmetic (documents defense-in-depth)

`backup.py:572`, mirror the rsync comment:

```python
# `--` terminates option parsing so path operands can't be reinterpreted as
# scp options (defense-in-depth; host/dest also validated at config load).
cmd = ["scp", "-r", "-q", "--", src_s, f"{host}:{dest}"]
```

---

## What I'd do first if it were mine

1. **R10** (FilesProvider requires root) — 5 min, closes real escape hatch
2. **R11** (SQL identifier validation) — 15 min, closes future-injection trap
3. **R12** (deepweb SSRF guard) — 30-45 min, closes reachable metadata-endpoint exposure
4. **R15** (summarizer keep tail) — 15 min, largest quality-of-output win
5. **R14** (numbered audit rotation) — 20 min, forensic history restoration

Total for the top five: ~90 minutes. All the rest can wait.

---

## Consolidated top-10 across both audit halves

Combining Part 1's R1-R9 and Part 2's R10-R18, the ranked "do first if it were mine" list:

1. **R1** (provenance redaction in web provider) — 5 min, real leak edge
2. **R10** (FilesProvider requires root) — 5 min, scope escape hatch
3. **R2** (outbound web query redaction) — 30 min, holds local-first promise
4. **R11** (SQL identifier validation in KG/Vector) — 15 min, future-proof trust boundary
5. **R12** (deepweb SSRF guard) — 30-45 min, metadata-endpoint exposure
6. **R3** (injection-marker probe in guardrails) — 3-4 hrs, biggest defense-in-depth win in the LLM path
7. **R15** (summarizer keep tail) — 15 min, largest single-fix quality improvement
8. **R14** (audit numbered rotation) — 20 min, forensic history
9. **R4** (federation error string scrubbing) — 15 min, future-leak trap
10. **R13** (independent verifier model) — 1-2 hrs, real second opinion

Everything else is polish. Total for this top-10: ~7-9 hours of focused work.

## What you're doing well (carrying forward from Part 1)

The strengths section in [findings_part2.md](findings_part2.md#new-strengths-worth-naming) names six distinct patterns of care that showed up in the second half. Combined with Part 1's list, this is a codebase that already practices most of the discipline an external audit would demand. The findings are polish and edge-hardening, not structural concerns.

The single sentence I'd carry back to you as author: **the `backup.py` embedded-audit-fix comments (CRIT/HIGH/MED tagged, tied to review-round numbers) are the operational shape of an audit-driven codebase.** If you ever share the audit history publicly alongside the code, the pattern-recognition value would be substantial — both as demonstration of discipline and as a template other maintainers could copy.
