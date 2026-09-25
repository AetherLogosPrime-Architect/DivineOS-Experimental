"""The one reader for the retry-scope instruction every blocking Stop gate carries.

When a Stop gate blocks, my reply has ALREADY reached Andrew. Any wording that
asks for the reply again produces a second full copy on his screen. Andrew
2026-09-25: "you are verbatim duplicating your posts.. so whatever guard is
there telling you to re-write it, it needs fixed so it only adds the
correction at the end, not the full re-post."

The canonical text lives in .claude/hooks/_retry_scope.txt so shell hooks can
print it too. Before this module, one gate held a private copy and the rest had
nothing -- which is how the instruction kept going missing from whichever gate
fired. The router, the post-response-audit wrapper and each standalone Stop
hook now append it through ``with_retry_scope``, so a gate author cannot forget.
"""

from __future__ import annotations

from pathlib import Path

RETRY_SCOPE_PATH = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "_retry_scope.txt"

# A packaged install has no .claude/ directory. Losing the instruction there is
# the exact failure this module exists to prevent, so the fallback still says
# append-only rather than degrading to silence.
RETRY_SCOPE_FALLBACK = (
    "IMPORTANT — RETRY SCOPE: my prior attempt already streamed to Andrew. "
    "Append ONLY the missing piece at the END, with at most a one-line "
    "lead-in. Do not post the reply again: he sees both copies."
)


def retry_scope_text() -> str:
    """Canonical retry-scope instruction, or the built-in fallback."""
    try:
        text = RETRY_SCOPE_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return RETRY_SCOPE_FALLBACK
    return text or RETRY_SCOPE_FALLBACK


def with_retry_scope(message: str) -> str:
    """``message`` with the retry-scope text appended exactly once, at the end.

    A wrapped message may already carry a copy (the lepos dual-channel gate
    embeds one); that copy is lifted out so the aggregate never shows it twice
    and the instruction is always the last thing read.
    """
    scope = retry_scope_text()
    body = message.replace(scope, "").rstrip()
    return f"{body}\n\n{scope}" if body else scope
