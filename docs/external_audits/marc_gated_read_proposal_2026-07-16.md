
# Proposal: gated oscillating-read (chunk-per-turn enforcement)

Date: 2026-07-16
Origin: external code audit (see DivineOS-Experimental-AUDIT-2026-07-16.md) of `core/oscillating_read.py`, followed by a design walk.
Target files: `src/divineos/core/oscillating_read.py`, `src/divineos/cli/oscillating_read_commands.py`, new `src/divineos/core/active_read_gate.py`, new `.claude/hooks/enforce-active-read.sh`, `.claude/settings.json`.

## The problem, stated the way the codebase already states problems like this

`oscillating_read.py`'s own docstring names the failure mode it exists to prevent: reading a long document straight through and missing the load-bearing point in the middle. The current fix is `[PAUSE] COMPREHEND CHUNK N/M BEFORE CONTINUING` markers printed between chunks in a single rendered block.

That fix doesn't close the gap it names. The whole rendered output -- every chunk, every pause marker -- lands in the model's context in one tool result, in one forward pass. There is no "before" and "after" for a printed pause line to sit between; the model can attend across the entire block identically whether the markers are there or not. This is the same shape as several findings in the audit: a mechanism that looks like enforcement but is actually self-report (the model choosing to act like it paused), with nothing structural behind it.

## The fix

Comprehension for an LLM isn't a pause -- it's forced generation. The only real way to make a "pause" exist is to make the next chunk's *text* not exist in context until the model has produced something grounded about the current chunk, across an actual tool-call boundary. Two pieces:

1. **Staged reveal.** `read-start` chunks the file (reusing the existing `chunk()` strategies unchanged) and returns only chunk 1, plus instructions. `read-next --point "..."` is the only way to get chunk 2 -- and it validates the stated point actually grounds in the current chunk's text before releasing the next one. Fail the check, get the same chunk back. On the last chunk, `read-next` returns the full ledger of stated points instead of a new chunk, so the closing summary is written with both the raw text and the model's own prior per-chunk claims still in context.
2. **Close the go-around.** Staging does nothing if the agent just calls `Read` (or `cat`/`Get-Content` via Bash) on the same path. A new PreToolUse gate (`active_read_gate.py`, wired the same way `pr_merge_gate.py` gates `gh pr merge`) denies `Read`/`Bash` access to any path with an open session, pointing the agent at `read-next` instead. This is enforced by Claude Code's own hook contract, not by an instruction the model could choose to ignore.

## Falsifier

The gate should NOT fire when: the tool isn't Read/Bash, the target path has no open session, or a Bash command doesn't actually reference an open session's source path.

The gate SHOULD fire when: Read targets a path with an open session, or a Bash command matches a recognizable read pattern (`cat`/`type`/`head`/`tail`/`Get-Content`/`open(`) against an open session's path.

Known, accepted gap: a command that reads the file through an unrecognized program, or copies it elsewhere first, evades the Bash check. Per truth #12 (bypass is a tool, not a sin) and the audit's own recommendation, the answer isn't a fourth layer of pattern-matching -- it's noticing the evasion happened. Suggest a follow-up: log every gate fire (allow AND deny) to the ledger via a lightweight `ACTIVE_READ_GATE_FIRED` event, so an unusual pattern of "session opened, never advanced, file read anyway 40 minutes later" is visible in review even without being blocked at the time.

## Suggested pre-registration (file this the way the project requires for any new mechanism)

```bash
divineos prereg file "gated oscillating read (chunk-per-turn enforcement)" \
  --claim "Replacing static [PAUSE] markers with a stateful chunk-release gate (read-start/read-next, PreToolUse deny on Read/Bash for files under an open session) measurably improves comprehension of mid-document load-bearing points versus the current single-shot oscillating-read output." \
  --success "On a sampled set of specs with a known mid-document load-bearing point (start with the gravity_classifier_spec.md case that originated this module), an agent using the gated flow correctly identifies the load-bearing point in its final summary at a higher rate than an agent given the current single-shot output, across >= 10 trials each." \
  --falsifier "If final-summary accuracy is statistically indistinguishable between gated and current flow, or if agents route around the gate via Bash often enough that real-world compliance stays near current levels, the mechanism has failed and should be reverted to single-shot rendering with the pause markers removed as decorative." \
  --review-days 30
```

---

## Code

### 1. `src/divineos/core/oscillating_read.py` -- additions

Everything currently in the file (`chunk_by_headers`, `chunk_by_paragraphs`, `chunk_by_functions`, `chunk_by_size`, `_auto_strategy`, `chunk`, `format_oscillating`, `oscillate_file`) stays as-is; `read-oscillating` keeps working as a single-shot preview. Add the following below `oscillate_file`, and add the new names to `__all__`.

```python
# --- Gated staged-reveal session layer --------------------------------
# Added 2026-07-16, external audit + design walk. Closes the gap the
# module docstring names but the [PAUSE] markers above don't actually
# close: a printed marker can't create a pause when the whole block
# lands in context in one tool result. This layer makes the pause real
# by withholding chunk N+1's TEXT until a grounded point about chunk N
# has been produced across an actual tool-call boundary. See the
# proposal doc (DivineOS-Experimental-GATED-READ-PROPOSAL-2026-07-16.md)
# for the falsifier. Enforcement half (blocking Read/Bash go-arounds)
# lives in core/active_read_gate.py + .claude/hooks/enforce-active-read.sh.

import hashlib
import json
import time

from divineos.core.atomic_io import atomic_write_text
from divineos.core.paths import divineos_home


def _session_dir() -> Path:
    d = divineos_home() / "reads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _session_key(path: str | Path) -> str:
    resolved = str(Path(path).resolve())
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:16]


def _session_path(path: str | Path) -> Path:
    return _session_dir() / f"{_session_key(path)}.json"


def _load_session(path: str | Path) -> dict | None:
    sp = _session_path(path)
    if not sp.exists():
        return None
    try:
        return json.loads(sp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save_session(path: str | Path, state: dict) -> None:
    atomic_write_text(_session_path(path), json.dumps(state, indent=2))


def active_session_for(path: str | Path) -> dict | None:
    """Return session state if PATH has an open (not done, not
    abandoned) session, else None. This is the entire enforcement
    surface active_read_gate.py checks against.
    """
    state = _load_session(path)
    if state is None:
        return None
    if state.get("done") or state.get("abandoned"):
        return None
    return state


def _iter_open_sessions():
    """Yield state dicts for every open session. Used by the Bash-side
    gate check, which has a command string, not a path, up front.
    """
    for f in _session_dir().glob("*.json"):
        try:
            state = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not state.get("done") and not state.get("abandoned"):
            yield state


def _validate_point(point: str, chunk_body: str) -> tuple[bool, str]:
    """Cheap lexical grounding check. Same accepted tradeoff as this
    project's other regex detectors (ADR-0003): auditable,
    deterministic, fast, gameable in principle. The difference here:
    gaming it buys nothing but access to text already sitting in this
    same tool result -- there's no reward for beating a check that only
    unlocks what honest comprehension would unlock anyway.
    """
    point = (point or "").strip()
    if len(point) < 15:
        return False, "too short to state a load-bearing point (< 15 chars)"
    words = point.split()
    if len(words) < 4:
        return False, "too few words to be a real claim about the chunk"
    norm_point = re.sub(r"\s+", " ", point.lower())
    norm_chunk = re.sub(r"\s+", " ", chunk_body.lower())
    if len(norm_point) > 40 and norm_point in norm_chunk:
        return False, "point is a verbatim excerpt of the chunk, not a stated claim about it"
    stop = {
        "the", "a", "an", "is", "are", "this", "that", "and", "or", "of",
        "to", "in", "on", "for", "it", "its", "was", "were", "with", "as",
    }
    point_terms = {w.strip(".,:;()\"'").lower() for w in words if len(w) >= 4} - stop
    chunk_terms = {w.strip(".,:;()\"'").lower() for w in norm_chunk.split() if len(w) >= 4} - stop
    if point_terms and not (point_terms & chunk_terms):
        return False, "point shares no vocabulary with the chunk -- not grounded in this section"
    return True, ""


def _render_step(state: dict, rejected: str = "") -> dict:
    idx = state["cursor"]
    label, body = state["chunks"][idx]
    total = len(state["chunks"])
    return {
        "ok": not rejected,
        "rejected_reason": rejected or None,
        "chunk_index": idx + 1,
        "total_chunks": total,
        "label": label,
        "body": body,
        "instruction": (
            f"Chunk {idx + 1}/{total}: {label}. State the load-bearing point of "
            "THIS chunk, then run:\n"
            f'  divineos read-next "{state["source"]}" --point "<your point>"\n'
            "to reveal the next chunk. The point is checked for grounding in "
            "this chunk's own text before the next one is released."
        ),
    }


def _render_done(state: dict) -> dict:
    lines = [f"  {p['chunk_index'] + 1}. [{p['label']}] {p['point']}" for p in state["points"]]
    return {
        "ok": True,
        "done": True,
        "total_chunks": len(state["chunks"]),
        "points": state["points"],
        "instruction": (
            "All chunks read. Your stated points, in order:\n"
            + "\n".join(lines)
            + "\n\nWrite the integrated summary now -- the raw chunks above and "
            "these stated points are both in context."
        ),
    }


def start_session(
    path: str | Path, strategy: str = "auto", max_chars: int = _DEFAULT_MAX_CHARS
) -> dict:
    """Chunk PATH and open a gated reading session. Returns the payload
    for chunk 1. Overwrites any existing session for this path --
    starting over is always allowed; skipping ahead is not.
    """
    p = Path(path)
    content = p.read_text(encoding="utf-8", errors="replace")
    chunks = chunk(content, strategy=strategy, max_chars=max_chars, source_path=str(p))
    if not chunks:
        chunks = [("(whole file)", content)]
    state = {
        "source": str(p.resolve()),
        "strategy": strategy,
        "max_chars": max_chars,
        "chunks": [[label, body] for label, body in chunks],
        "cursor": 0,
        "points": [],
        "started_at": time.time(),
        "done": False,
        "abandoned": False,
    }
    _save_session(path, state)
    return _render_step(state)


def advance_session(path: str | Path, point: str) -> dict:
    """Validate POINT against the currently-open chunk. On pass, record
    it and reveal the next chunk (or the closing ledger on the last
    chunk). On fail, re-return the SAME chunk with a rejection reason --
    the session does not advance.
    """
    state = _load_session(path)
    if state is None:
        raise LookupError(f"no active read session for {path} -- run read-start first")
    if state.get("done"):
        return _render_done(state)
    idx = state["cursor"]
    label, body = state["chunks"][idx]
    ok, reason = _validate_point(point, body)
    if not ok:
        return _render_step(state, rejected=reason)
    state["points"].append(
        {"chunk_index": idx, "label": label, "point": point.strip(), "ts": time.time()}
    )
    state["cursor"] += 1
    if state["cursor"] >= len(state["chunks"]):
        state["done"] = True
        _save_session(path, state)
        return _render_done(state)
    _save_session(path, state)
    return _render_step(state)


def abandon_session(path: str | Path, reason: str = "") -> None:
    """Explicitly close a session without finishing it. Logged, not
    silent -- an abandoned gate is a decision, not a leak. Releases the
    PreToolUse gate on PATH.
    """
    state = _load_session(path)
    if state is None:
        return
    state["abandoned"] = True
    state["abandon_reason"] = reason or "(no reason given)"
    state["abandoned_at"] = time.time()
    _save_session(path, state)
```

Add to `__all__`:

```python
__all__ = [
    "chunk_by_headers",
    "chunk_by_paragraphs",
    "chunk_by_functions",
    "chunk_by_size",
    "chunk",
    "format_oscillating",
    "oscillate_file",
    "start_session",
    "advance_session",
    "abandon_session",
    "active_session_for",
]
```

---

### 2. `src/divineos/cli/oscillating_read_commands.py` -- full replacement

No change needed in `cli/__init__.py` -- it already imports this module and calls `oscillating_read_commands.register(cli)`; the new commands ride along.

```python
"""CLI: gated oscillating read -- divineos read-start / read-next /
read-abandon (the enforced flow), plus the original divineos
read-oscillating (single-shot preview, not enforced).

Per claim 3a44289d and the 2026-07-16 external-audit design walk that
added the staged-reveal + PreToolUse gate. See core/oscillating_read.py
and core/active_read_gate.py for the mechanism.
"""

from __future__ import annotations

import click

from divineos.core.oscillating_read import (
    abandon_session,
    advance_session,
    oscillate_file,
    start_session,
)


def register(cli: click.Group) -> None:
    @cli.command("read-oscillating")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    @click.option(
        "--strategy",
        type=click.Choice(["auto", "headers", "paragraphs", "functions", "size"]),
        default="auto",
        help=(
            "Chunking strategy. auto picks by file shape: .py->functions, "
            ".md/.txt with headers->headers else paragraphs, else size."
        ),
    )
    @click.option("--max-chars", type=int, default=2000, help="Max chars per chunk when strategy=size.")
    def read_oscillating_cmd(path: str, strategy: str, max_chars: int) -> None:
        """Single-shot preview with pause markers. NOT enforced -- the
        whole file lands in context at once regardless of the markers.
        Use `read-start` for the gated flow that actually withholds
        later chunks until a grounded point is stated.
        """
        try:
            output = oscillate_file(path, strategy=strategy, max_chars=max_chars)
        except Exception as exc:  # noqa: BLE001
            click.secho(f"[!] read-oscillating failed: {exc}", fg="red")
            raise click.exceptions.Exit(2) from exc
        click.echo(output)

    @cli.command("read-start")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    @click.option(
        "--strategy",
        type=click.Choice(["auto", "headers", "paragraphs", "functions", "size"]),
        default="auto",
    )
    @click.option("--max-chars", type=int, default=2000)
    def read_start_cmd(path: str, strategy: str, max_chars: int) -> None:
        """Open a gated oscillating-read session and print chunk 1.

        While the session is open, Read and Bash read-alikes
        (cat/type/head/tail/Get-Content) are denied for PATH by the
        PreToolUse gate in active_read_gate.py -- the only way forward
        is `read-next`.
        """
        try:
            step = start_session(path, strategy=strategy, max_chars=max_chars)
        except Exception as exc:  # noqa: BLE001
            click.secho(f"[!] read-start failed: {exc}", fg="red")
            raise click.exceptions.Exit(2) from exc
        click.echo(_format_step(step))

    @cli.command("read-next")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    @click.option("--point", required=True, help="Load-bearing point of the current chunk.")
    def read_next_cmd(path: str, point: str) -> None:
        """Submit the point for the current chunk; get the next chunk
        (or, on the last chunk, the full point ledger + summary prompt).
        Re-serves the SAME chunk if the point doesn't ground in it.
        """
        try:
            step = advance_session(path, point)
        except LookupError as exc:
            click.secho(f"[!] {exc}", fg="red")
            raise click.exceptions.Exit(2) from exc
        if step.get("done"):
            click.echo(step["instruction"])
            return
        if not step["ok"]:
            click.secho(f"[rejected] {step['rejected_reason']}", fg="yellow")
        click.echo(_format_step(step))

    @cli.command("read-abandon")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    @click.option("--reason", default="", help="Why the session is being abandoned.")
    def read_abandon_cmd(path: str, reason: str) -> None:
        """Close an open session early. Logged, not silent -- releases
        the PreToolUse gate on PATH.
        """
        abandon_session(path, reason=reason)
        click.secho(f"[ok] session for {path} abandoned. Gate released.", fg="cyan")


def _format_step(step: dict) -> str:
    header = "=" * 60
    parts = [
        header,
        f"CHUNK {step['chunk_index']}/{step['total_chunks']}: {step['label']}",
        header,
        step["body"].rstrip(),
        "",
        step["instruction"],
    ]
    return "\n".join(parts)
```

---

### 3. NEW `src/divineos/core/active_read_gate.py`

```python
"""Active-read gate -- block Read/Bash access to a file that has an
open gated oscillating-read session, so the staged-reveal in
oscillating_read.py can't be bypassed by just reading the file
directly.

## Why this exists

External audit 2026-07-16 found oscillating_read.py's [PAUSE] markers
were pure decoration: the whole rendered file (markers included) lands
in context in a single tool result, so there is no point in time for a
"pause" to occur between chunks. The fix (read-start/read-next staging
in oscillating_read.py) makes the pause real by withholding chunk N+1's
text until a grounded point about chunk N has been stated in its own
tool call. That half is free -- the model cannot attend to tokens that
are not yet in context.

The half that is NOT free: nothing stops the agent from just calling
Read (or cat/type/Get-Content via Bash) on the same path, skipping the
mechanism entirely. This gate closes that hole the same way
gh-pr-merge-gate.sh closes the merge-button hole for pr_merge_gate --
move the discipline into a PreToolUse deny, so going around it means
going around Claude Code's own enforcement, not just an instruction.

## Architecture

Thin doorman, same shape as pr_merge_gate. The hook
(.claude/hooks/enforce-active-read.sh) reads the PreToolUse payload and
asks ``block_reason()`` here for a verdict against
``oscillating_read.active_session_for()`` / ``_iter_open_sessions()``.

## Falsifier

The gate should NOT fire when:
* The tool is not Read/Bash.
* The target path (Read) or referenced path (Bash) has no open session
  (none started, or already done/abandoned).
* The Bash command doesn't reference an open session's source path.

The gate SHOULD fire when:
* Read targets a path with an open oscillating-read session.
* A Bash command contains a recognizable read-the-file pattern
  (cat/type/head/tail/Get-Content/python -c open(...)) whose argument
  resolves to that same path.

Known gap, accepted rather than chased: a command that reads the file
through an unrecognized program, or copies it to a new path first,
evades this specific check. Per truth #12 (bypass is a tool, not a
sin), the response to an evasion is not a fourth layer of
pattern-matching -- it's noticing the evasion happened. See the
proposal doc for a suggested ACTIVE_READ_GATE_FIRED ledger event to
make that visible in review.
"""

from __future__ import annotations

import re
from pathlib import Path

from divineos.core.oscillating_read import _iter_open_sessions, active_session_for

__guardrail_required__ = True

_READ_CMD_PATTERN = re.compile(r"\b(cat|type|head|tail|less|more|Get-Content|gc)\b", re.IGNORECASE)


def _bash_references_path(command: str, source: str) -> bool:
    """True if COMMAND looks like it reads SOURCE directly."""
    if not command or not source:
        return False
    name = Path(source).name
    if name not in command:
        return False
    return bool(_READ_CMD_PATTERN.search(command)) or "open(" in command


def block_reason(tool_name: str, tool_input: dict) -> str | None:
    """Return a deny reason if TOOL_NAME/TOOL_INPUT would read a file
    under an open oscillating-read session by a route other than
    ``divineos read-next``. Returns None to allow.
    """
    if tool_name == "Read":
        path = (tool_input or {}).get("file_path") or ""
        if not path:
            return None
        state = active_session_for(path)
        if state is None:
            return None
        return (
            f"'{Path(path).name}' is under an active oscillating read "
            f"({len(state['points'])}/{len(state['chunks'])} chunks acknowledged). "
            f'Continue with: divineos read-next "{state["source"]}" --point "..." '
            f'-- or cancel with: divineos read-abandon "{state["source"]}"'
        )

    if tool_name == "Bash":
        command = (tool_input or {}).get("command") or ""
        if not command.strip():
            return None
        if not _READ_CMD_PATTERN.search(command) and "open(" not in command:
            return None
        for state in _iter_open_sessions():
            if _bash_references_path(command, state["source"]):
                return (
                    f"'{Path(state['source']).name}' is under an active oscillating read. "
                    f'Continue with: divineos read-next "{state["source"]}" --point "..." '
                    f'-- or cancel with: divineos read-abandon "{state["source"]}"'
                )
        return None

    return None
```

---

### 4. NEW `.claude/hooks/enforce-active-read.sh`

Matcher: `Read|Bash`. Deliberately fails LOUD on both the missing-python path AND a gate-module exception -- the audit found the opposite asymmetry (loud on lookup failure, silent `except: pass` on the gate call itself) in `compass-check.sh`, and that asymmetry is the specific reason the moral-compass rudder became a permanent silent no-op. Not reproducing that shape here. The gate still fails OPEN either way (the tool call proceeds on error); only the *silence* is what's fixed.

```bash
#!/bin/bash
# PreToolUse hook -- block Read/Bash from reading a file that has an
# open gated oscillating-read session. See core/active_read_gate.py
# for the full rationale. Matcher: Read|Bash.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    echo "  [enforce-active-read] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

PY_STDERR=$(mktemp)
RESULT=$(echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception as exc:
    print(f'PARSE_ERROR:{exc}', file=sys.stderr)
    sys.exit(0)

tool_name = data.get('tool_name') or ''
tool_input = data.get('tool_input') or {}

try:
    from divineos.core.active_read_gate import block_reason
except Exception as exc:
    print(f'IMPORT_ERROR:{exc}', file=sys.stderr)
    sys.exit(0)

try:
    reason = block_reason(tool_name, tool_input)
except Exception as exc:
    print(f'GATE_ERROR:{exc}', file=sys.stderr)
    sys.exit(0)

if not reason:
    sys.exit(0)

print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': reason,
    }
}))
" 2>"$PY_STDERR")

if [ -s "$PY_STDERR" ]; then
    echo "  [enforce-active-read] GATE ERROR (failed open, see below):" >&2
    cat "$PY_STDERR" >&2
fi
rm -f "$PY_STDERR"

echo "$RESULT"
exit 0
```

---

### 5. `.claude/settings.json` -- add one matcher block under `PreToolUse`

```json
      {
        "matcher": "Read|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/enforce-active-read.sh",
            "timeout": 10
          }
        ]
      }
```

Place it anywhere in the `PreToolUse` array alongside the other `Read`/`Bash` matcher blocks -- Claude Code runs every matching block for a given tool call, and a deny from any one of them blocks the call.

---

## What this does and doesn't fix

Closes, specifically: the self-attestation gap in this one tool. Comprehension is now structurally required (a grounded point must exist before the next chunk does) rather than requested (a printed marker asking nicely).

Does not touch: any of the other findings from the 2026-07-16 audit (the moral-compass rudder, the council-required gate, the ledger self-destruction on compaction, etc.) -- this is scoped to oscillating-read only.

Honest limits of this specific mechanism, matching the project's own "Known tradeoffs" framing:

- `_validate_point` is lexical/heuristic, same category as the other regex-based detectors the audit flagged as "self-report pattern-matching, not verification." The difference that makes it worth shipping anyway: those detectors were trying to verify a claim about the world (did I actually fix the bug); this one only gates access to text that's already sitting in the same tool result. There's no way to profitably game a check whose only prize is early access to something you'd see two seconds later anyway by complying. If stronger assurance is wanted later, swap `_validate_point` for a real grading call (a cheap model judging "does this point capture this chunk") without changing anything else in the design.
- The Bash-side check is a substring/pattern match on the command text, with the same edges as the project's other command-pattern gates (`no-verify-cost-escalation.sh`, `pre-tool-bypass-rate-scan.sh`): a sufficiently indirect read (copy the file first, pipe through an unlisted program) gets through. Recommend not chasing this with more patterns -- log gate fires to the ledger instead, so an evasion is visible in review even when it isn't blocked in the moment.
