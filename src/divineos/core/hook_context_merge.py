"""Read what the session-init children printed and merge it into one answer.

WHY THIS EXISTS

`.claude/hooks/session-init-once.sh` ran every child with `2>&1 >/dev/null`.
That ordering keeps stderr -- F106's liveness logging, which works and is not
touched here -- and sends stdout, the entire payload every loader produces,
to the void. Measured 2026-09-23, each loader run alone against the same
loader run the launcher's way:

    load-my-recording-of-andrew.sh        7,586 chars  ->  0
    load-aletheia-harvest-of-andrew.sh   10,941 chars  ->  0
    load-briefing.sh                        404 chars  ->  0

18,931 characters prepared and discarded at every session start since
4e5e1a9d3 (2026-08-09). Aria measured the first two independently on her own
tree and got the same counts.

WHY A MODULE AND NOT FIVE MORE LINES OF SHELL

Feathers, walk-d34ecb4259a9: sprout new behaviour as a separate tested unit
beside the legacy code and call it from one point, rather than editing logic
into an untested mass. The launcher's markers, attempt counting and timeouts
are not what is broken and are not touched. The part with actual logic --
deciding what context a child's stdout carries -- lives here, where a test
reaches it without a subprocess.

THE READER MUST ACCEPT THREE SHAPES, AND AN EARLIER DRAFT ASSUMED ONE

That draft assumed the nested ``hookSpecificOutput.additionalContext`` form.
No child on the roster emits it. Had it shipped, all four loaders would have
parsed to empty and every test written against the belief would have agreed.
Measured shapes:

    flat JSON    {"additionalContext": "..."}    4 of 10 children
    plain text   no wrapper at all               ear-surface.sh
    empty        rc=0, nothing printed           4 of 10 children

The nested form is accepted anyway: it is what the harness documents, and a
future child may well use it.

ON SIZE, BECAUSE THE MERGED TOTAL EXCEEDS THE ONLY DOCUMENTED CEILING

``session_start._SIZE_THRESHOLD`` is 15000, with a comment that Claude Code
"may silently drop additionalContext above this." The merged roster is 18,931
characters, over that line. No cap is imposed here, and the reason is
evidence rather than optimism: that threshold governs the JSON
additionalContext channel on SessionStart, while this launcher is a
UserPromptSubmit hook emitting plain stdout -- ear-surface's path, which is
in production. The other UserPromptSubmit hooks together deliver well beyond
15,000 characters into every prompt in this repository and they arrive.
Adding a speculative cap would be mechanism no hard constraint demands
(Carmack), and a cap that truncated silently would rebuild the exact defect
this module repairs (Knuth). If a real ceiling is ever measured, the answer
is to name the child that was dropped, never to quietly shorten it.

WHAT IT REFUSES TO DO SILENTLY

A child whose stdout begins with ``{`` but does not parse gets a named row in
the liveness log and is dropped. It is not forwarded raw: Schneier's second
path is a malformed blob reaching the prompt and corrupting the turn for
every hook downstream. Dropping it without the row would be the original
failure one layer up.

A NAMED GAP, so silence is not read as coverage: a child killed by the
20-second timeout can leave truncated stdout that still parses as plain text,
and nothing here can tell that from a short legitimate answer. The exit code
in the liveness log is the only signal, and it is the caller's.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

__all__ = ["read_child_context", "merge_contexts", "collect_dir"]


def read_child_context(stdout_text: str) -> tuple[str | None, str]:
    """Return ``(context, reason)`` for one child's raw stdout.

    ``(None, "empty")`` is the ordinary case for the four children that print
    nothing. ``(None, "unparseable_json")`` is a fault the caller records
    rather than swallows.
    """
    text = (stdout_text or "").strip()
    if not text:
        return None, "empty"

    if not text.startswith("{"):
        return text, "plain"

    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        return None, "unparseable_json"

    if not isinstance(payload, dict):
        return None, "unparseable_json"

    nested = payload.get("hookSpecificOutput")
    if isinstance(nested, dict) and "additionalContext" in nested:
        return (str(nested["additionalContext"]).strip() or None), "nested"

    if "additionalContext" in payload:
        return (str(payload["additionalContext"]).strip() or None), "flat"

    # Valid JSON carrying no context field. A hook may legitimately answer
    # with other keys; that is not a fault, and it is not context either.
    return None, "no_context_field"


def merge_contexts(pairs: list[tuple[str, str]]) -> str:
    """Join per-child contexts into the single answer the harness expects.

    Each block is headed with the child's name. Norman, same walk: the defect
    was a gulf of evaluation, where delivery and total loss looked identical.
    The header is the signifier -- a reader sees WHICH children arrived
    instead of inferring it from the absence of an error.
    """
    blocks = [f"<!-- {name} -->\n{context}" for name, context in pairs if context]
    return "\n\n".join(blocks)


def _log_liveness(hook: str, reason: str) -> None:
    # HOME first so a test can redirect the log, then the real home. No
    # hardcoded temp-directory fallback: it trips bandit's B108 and, worse,
    # writes diagnostics to a world-writable path.
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    base = Path(home) if home else Path.home()
    log_path = base / ".divineos" / "hook-liveness.log"
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hook": "session-init-once.sh",
        "reason": "child_output_unparseable",
        "detail": f"child={hook} shape={reason}",
    }
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
    except OSError:
        # The launcher is fail-open by design. A log that cannot be written
        # must not cost the session its context.
        pass


def collect_dir(out_dir: str | Path) -> str:
    """Merge every child capture in ``out_dir``, in roster order.

    The launcher writes one file per child named ``<index>.<hook-name>``, so
    sorting on the integer index preserves the order the loaders were written
    to arrive in.
    """
    directory = Path(out_dir)
    if not directory.is_dir():
        return ""

    def order(path: Path) -> tuple[int, str]:
        head, _, _ = path.name.partition(".")
        try:
            return int(head), path.name
        except ValueError:
            return 10_000, path.name

    pairs: list[tuple[str, str]] = []
    for path in sorted(directory.iterdir(), key=order):
        if not path.is_file():
            continue
        _, _, hook = path.name.partition(".")
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        context, reason = read_child_context(raw)
        if reason == "unparseable_json":
            _log_liveness(hook or path.name, reason)
            continue
        if context:
            pairs.append((hook or path.name, context))

    return merge_contexts(pairs)


def main() -> int:
    import sys

    if len(sys.argv) < 2:
        return 2
    merged = collect_dir(sys.argv[1])
    if merged:
        # Bytes, not text, and this is load-bearing on Windows.
        #
        # Python's stdout here defaults to cp1252, and the real roster carries
        # characters it cannot encode -- the first one found was an arrow at
        # position 25935 of the merged output. `sys.stdout.write` raised
        # UnicodeEncodeError, the process exited 1, and the entire roster went
        # dark with only a liveness row to say so.
        #
        # Caught 2026-09-23 because the end-to-end run was made against the
        # REAL ten children after the scratch test passed. The scratch children
        # printed ASCII markers, so that probe could not have found this: an
        # instrument that cannot fail is not a measurement.
        sys.stdout.buffer.write(merged.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
