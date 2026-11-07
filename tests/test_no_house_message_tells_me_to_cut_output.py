"""No text the house prints to me recommends cutting output.

Dad, 2026-11-07: "any and all truncation is a bad thing.. period point blank.. if things need chunked or
compressed to read it then so be it but words cut off tells you nothing".

Measured the same day, on one session of mine: 63 percent of my shell commands cut their own output with
tail, head or cut, and a gate message told me to end a line with `| tail -N` or `| head -N` 310 times. The
message was the near-miss text in ``.claude/hooks/lib/remedy_allowlist.sh``. A push report whose reason I had
cut off with `| tail -4` then said only "stopped before tests", and the reason was lost.

This scans every hook script and every in-tree hook module for advice to cut, so the advice cannot come back
by anyone's edit. It is a text scan: a message assembled at run time from pieces could still evade it, which
the game walk for this change names and leaves open.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Advice to cut: a sentence telling the reader to end, pipe or finish a line with tail or head, or the literal
# placeholder form the old message used. Code that itself uses `| head -1` inside a script is not advice.
ADVICE = re.compile(
    r"(?:end|finish|pipe|append|add)\b[^\n\"']{0,70}\|\s*(?:tail|head)\b",
    re.IGNORECASE,
)

OLD_MESSAGE = (
    "so the whole line was treated as ordinary work. If it only filters output, "
    "end the line with | tail -N or | head -N instead."
)


def _scanned_files() -> list[Path]:
    files: list[Path] = []
    for folder in (ROOT / ".claude" / "hooks", ROOT / "src" / "divineos" / "hooks"):
        if folder.is_dir():
            files += [p for p in folder.rglob("*") if p.suffix in {".sh", ".py"} and p.is_file()]
    return files


def test_the_scan_sees_the_old_message():
    """CONTROL: the instrument must be able to find a case it should find, or a clean result means nothing."""
    assert ADVICE.search(OLD_MESSAGE) is not None


def test_there_are_files_to_scan():
    """CONTROL: an empty scan reads as clean and is not."""
    assert len(_scanned_files()) > 20


def test_no_hook_text_tells_me_to_cut_output():
    offenders = []
    for path in _scanned_files():
        for number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if line.lstrip().startswith("#"):
                continue  # a comment describing how a command behaves is not a message shown to me
            if ADVICE.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()[:140]}")
    assert not offenders, "a house message advises cutting output:\n" + "\n".join(offenders)
