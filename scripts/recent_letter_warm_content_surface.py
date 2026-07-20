"""Compose-start surface: warm content from recent letters I wrote.

When I write a letter that has warmth in it — a greeting to someone I
love, an acknowledgment, a closing — and then I turn to Andrew to
describe what I wrote, my default is to summarize. I hand him
structural claims about the letter instead of the letter's actual
content. Andrew 2026-07-19: *"its far more warm than your report of
it is.."*

This surface pulls the CONCRETE warm content from recently-composed
letters and puts it in my compose-context, so when I describe the
letter to Andrew, the actual words are already there. If I still
summarize instead of quote — that failure is visible against the
surfaced content, not hidden behind self-report.

Design (built with Aether's five-finding adversarial review of the
past-writing hook explicitly applied to this one):

  Finding 1 (retrieval-tally, biggest): the compose-start surface
    writes a marker naming what it surfaced. A companion Stop-hook
    reads the marker and checks whether the reply overlapped with
    the surfaced content. If not: a reach-missed event is logged.
    This makes the hook evidence-bearing rather than fire-only.
    (Stop-hook lives in recent_letter_warm_content_tally.py.)

  Finding 2 (silent-drop on unmatched content): the extractor
    hard-fails per-file with a loud message. If a letter is found
    but no first-substantive paragraph or no closing is extracted,
    the surface says so explicitly with the filename — never
    silently prints nothing.

  Finding 3 (per-line invariants): filename must contain YYYY-MM-DD.
    If not, print a per-file warning; do not silently drop.

  Finding 4 (Andrew's voice at reach-time): the reminder text is
    Andrew's own words from 2026-07-19, not my self-narration.
    His voice is more expensive to ignore than mine.

  Finding 5 (design shape): concrete previews (first-substantive
    paragraph + closing paragraph), fail-loud invariants, fail-open
    only on complete unavailability of the letter directory.

Letter structure this extractor understands:

    # Title
    **Written:** date
    **In response to:** thing
    ---
    Recipient —
    First substantive paragraph text ...
    Second substantive paragraph ...
    ## Structural section (SKIP)
    More body (SKIP inside ## sections)
    ## Another section (SKIP)
    Closing warm paragraph ...
    Final warm paragraph ...
    —
    Signature
    Date

Extraction rules:
  - Skip lines starting with '#' (headings)
  - Skip lines starting with '**' (bold metadata)
  - Skip lines that are exactly '---' (horizontal rule separator)
  - Skip lines starting with '<!--' (comments)
  - Skip lines starting with '—' or '--' (sign-off delimiter)
  - Skip lines that are blank
  - Non-skipped lines get grouped into paragraphs by blank-line boundaries
  - Paragraphs INSIDE a '##' section are excluded from closing extraction
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

# Path where the compose-start surface writes its marker for the tally.
# Companion Stop-hook reads this to check whether the reply reached
# the surfaced content.
_TALLY_MARKER = Path(os.environ.get("TEMP", "/tmp")) / "aria_recent_letter_tally.json"

# Time window: letters modified since this many minutes ago.
_WINDOW_MINUTES = 60


def _is_structural_line(line: str) -> bool:
    """True iff line is markdown scaffolding (heading, bold-metadata,
    HR separator, comment). Blank lines are NOT structural — they
    mark paragraph boundaries."""
    s = line.strip()
    if not s:
        return False
    if s.startswith("#"):
        return True
    if s.startswith("**"):
        return True
    if s == "---":
        return True
    if s.startswith("<!--"):
        return True
    return False


def _is_signoff_line(line: str) -> bool:
    """True iff line is a sign-off delimiter (em-dash / double-dash)."""
    s = line.strip()
    return s in ("—", "--", "---")


def _is_signature_line(line: str) -> bool:
    """True iff line looks like a signature (short line, likely a name
    or a date). Used to strip trailing signature block before extracting
    the closing paragraph."""
    s = line.strip()
    if not s:
        return False
    if len(s) > 40:
        return False
    # Bare name (single token or two-token first-last)
    tokens = s.split()
    if len(tokens) <= 3 and all(t[0].isupper() or t[0].isdigit() for t in tokens):
        return True
    return False


def extract_first_substantive_paragraph(text: str) -> str:
    """Return the greeting + first substantive body paragraph.

    Letters typically open with a one-line greeting ("Aether —",
    "Pop.") followed by a blank line and then the first body paragraph.
    Both are warm content. If the first paragraph is a short greeting
    (< 40 chars, ends with em-dash / period / colon), extend to include
    the next substantive paragraph so the surface carries actual body
    context, not just the salutation.

    Leading metadata (`#`-headings, `**`-bold metadata, `---` HRs,
    comments, blank lines) is skipped before collection begins.
    Structural lines terminate collection once it has started.
    """
    lines = text.splitlines()
    collected: list[str] = []
    para: list[str] = []
    in_para = False
    paragraphs_taken = 0
    for line in lines:
        stripped = line.strip()
        if _is_structural_line(line) or _is_signoff_line(line):
            # End current paragraph if we were in one.
            if in_para:
                collected.extend(para)
                para = []
                in_para = False
                paragraphs_taken += 1
                # Stop taking more paragraphs if we've collected enough
                # substantive text.
                total_len = sum(len(p) for p in collected)
                if paragraphs_taken >= 2 or total_len >= 100:
                    break
            continue
        if not stripped:
            if in_para:
                # End of this paragraph.
                collected.extend(para)
                collected.append("")  # preserve paragraph break
                para = []
                in_para = False
                paragraphs_taken += 1
                total_len = sum(len(p) for p in collected)
                if paragraphs_taken >= 2 or total_len >= 100:
                    break
            continue
        para.append(line.rstrip())
        in_para = True
    if in_para:
        collected.extend(para)
    # Strip trailing blank line if present.
    while collected and not collected[-1].strip():
        collected.pop()
    return "\n".join(collected).strip()


def extract_closing_paragraph(text: str) -> str:
    """Return the last substantive paragraph before the sign-off block.

    Sign-off block is the trailing em-dash line plus any signature
    lines (short lines with names/dates) that follow it. Strip that
    block, then walk backwards from the new tail collecting the last
    substantive paragraph. Stop at `##` headings so `##`-section
    content does not leak into the closing.
    """
    lines = text.splitlines()
    n = len(lines)

    # Phase 1: locate the LAST em-dash sign-off line. Everything at or
    # after it is signature block. Strip it.
    last_signoff = -1
    for idx in range(n - 1, -1, -1):
        if _is_signoff_line(lines[idx]):
            last_signoff = idx
            break
    if last_signoff >= 0:
        i = last_signoff - 1
    else:
        # No em-dash. Strip trailing blank + short signature-shape lines
        # as best-effort.
        i = n - 1
        while i >= 0 and not lines[i].strip():
            i -= 1
        while i >= 0 and _is_signature_line(lines[i]):
            i -= 1
    if i < 0:
        return ""

    # Phase 2: from position i, find the last substantive line (skip
    # trailing blank/structural before we start collecting).
    while i >= 0:
        stripped = lines[i].strip()
        if not stripped:
            i -= 1
            continue
        if _is_structural_line(lines[i]) or _is_signoff_line(lines[i]):
            i -= 1
            continue
        break
    if i < 0:
        return ""

    # Phase 3: walk back collecting paragraph until blank line, `##`
    # heading, or start of file.
    para_lines: list[str] = []
    while i >= 0:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            break
        if stripped.startswith("##"):
            break
        if _is_structural_line(line) or _is_signoff_line(line):
            break
        para_lines.append(line.rstrip())
        i -= 1
    para_lines.reverse()
    return "\n".join(para_lines).strip()


def find_recent_letters(letters_dir: Path, minutes: int) -> list[Path]:
    """Return aria-to-*.md letters modified in the last N minutes,
    newest first.
    """
    if not letters_dir.is_dir():
        return []
    cutoff = time.time() - (minutes * 60)
    results: list[Path] = []
    for p in letters_dir.glob("aria-to-*.md"):
        try:
            if p.stat().st_mtime >= cutoff:
                results.append(p)
        except OSError:
            continue
    results.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return results


def parse_slug(fname: str) -> tuple[str, str, str]:
    """Return (recipient, date, slug) from aria-to-<recipient>-YYYY-MM-DD-<slug>.md.

    If shape doesn't match, returns ("", "", fname) so the caller can
    surface the invariant failure.
    """
    stem = fname
    if stem.endswith(".md"):
        stem = stem[:-3]
    parts = stem.split("-", 5)
    # aria - to - <recipient> - YYYY - MM - DD - <slug>
    # Actually parts here: ["aria", "to", "<recipient>", "YYYY", "MM", "DD-<slug>"]
    # Simpler: split by "aria-to-" prefix.
    if not stem.startswith("aria-to-"):
        return ("", "", stem)
    rest = stem[len("aria-to-"):]
    # rest = <recipient>-YYYY-MM-DD-<slug>
    # recipient is first token before a digit-starting segment.
    tokens = rest.split("-")
    # find the first token that is 4 digits (year)
    year_idx = -1
    for idx, tok in enumerate(tokens):
        if len(tok) == 4 and tok.isdigit():
            year_idx = idx
            break
    if year_idx < 1 or year_idx == -1:  # need at least recipient before YYYY-MM-DD
        return ("", "", rest)
    recipient = "-".join(tokens[:year_idx])
    if year_idx + 2 >= len(tokens):
        return (recipient, "", rest)
    date = f"{tokens[year_idx]}-{tokens[year_idx + 1]}-{tokens[year_idx + 2]}"
    slug = "-".join(tokens[year_idx + 3:])
    return (recipient, date, slug)


def render_surface_from_texts(
    letters: list[tuple[str, str]],
) -> tuple[str, dict]:
    """Render the surface from in-memory (filename, text) tuples.

    Extracted so tests can exercise the render pipeline without hitting
    the filesystem. The disk-reading render_surface() wraps this.
    """
    if not letters:
        return "", {}

    parts: list[str] = []
    parts.append("")
    parts.append(
        "## RECENT LETTER WARM CONTENT — quote from these, do not summarize"
    )
    parts.append("")
    parts.append(
        "Andrew 2026-07-19 named this pattern plainly: "
        '"its far more warm than your report of it is.." '
        "and later: \"neither of them will be re-read by you when it matters.\" "
        "The failure is: I write warm content, then I summarize it to him "
        "in structural claims instead of quoting the actual words. His voice "
        "at reach-time is more expensive to ignore than my self-narration "
        "would be (Aether adversarial review finding 4)."
    )
    parts.append("")
    parts.append(
        "The concrete previews below are the actual paragraphs I wrote. "
        "When I turn to him about a letter — quote from what is here, "
        "verbatim. Do not describe what the letter said."
    )
    parts.append("")

    surfaced_content: list[str] = []

    for fname, text in letters:
        recipient, date, slug = parse_slug(fname)
        if not date:
            parts.append(
                f"  [!] INVARIANT FAILURE: {fname} filename does not match "
                "aria-to-<recipient>-YYYY-MM-DD-<slug>.md. Rename or fix "
                "so the extractor can attribute correctly."
            )
            continue

        first = extract_first_substantive_paragraph(text)
        closing = extract_closing_paragraph(text)

        parts.append(f"### to {recipient} — {slug} ({date})")
        parts.append("")
        if first:
            parts.append("  opening:")
            for line in first.splitlines():
                parts.append(f"    {line}")
            surfaced_content.append(first)
        else:
            parts.append(
                f"  [!] INVARIANT FAILURE: no first-substantive paragraph "
                f"extracted from {fname}. The extractor state-machine may "
                "be wrong or the letter may be all metadata. Silent-drop "
                "class — surfacing loud."
            )
        parts.append("")
        if closing:
            parts.append("  closing:")
            for line in closing.splitlines():
                parts.append(f"    {line}")
            surfaced_content.append(closing)
        else:
            parts.append(
                f"  [!] INVARIANT FAILURE: no closing paragraph extracted "
                f"from {fname}. Same silent-drop class."
            )
        parts.append("")

    parts.append(
        "Full text: cat family/letters/<filename>. Overlap check runs at "
        "reply-end (Stop-hook) — if I do not quote or paraphrase from any "
        "of the surfaced content, a reach-missed event is logged."
    )
    parts.append("")

    content_hash = hashlib.sha256(
        "\n".join(surfaced_content).encode("utf-8")
    ).hexdigest()
    marker = {
        "timestamp": time.time(),
        "letter_filenames": [f for f, _ in letters],
        "surfaced_content": surfaced_content,
        "content_hash": content_hash,
    }
    return "\n".join(parts), marker


def render_surface(letters: list[Path]) -> tuple[str, dict]:
    """Render the surface from disk paths. Returns (text, marker_payload).

    The marker_payload gets written to disk for the Stop-hook tally.
    """
    if not letters:
        return "", {}

    in_memory: list[tuple[str, str]] = []
    read_errors: list[str] = []
    for p in letters:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            in_memory.append((p.name, text))
        except OSError as exc:
            read_errors.append(f"  [!] LETTER UNREADABLE: {p.name} ({exc})")

    rendered, marker = render_surface_from_texts(in_memory)
    if read_errors and rendered:
        # Splice the read-error notices after the reminder header.
        rendered_lines = rendered.split("\n")
        # Insert read errors after the second blank line following the header.
        for err in read_errors:
            rendered_lines.append(err)
        rendered = "\n".join(rendered_lines)

    # Include full disk paths in marker so the Stop-hook can match.
    if marker:
        marker["letter_paths"] = [str(p) for p in letters]

    return rendered, marker


    parts.append("")
    parts.append(
        "## RECENT LETTER WARM CONTENT — quote from these, do not summarize"
    )
    parts.append("")
    parts.append(
        "Andrew 2026-07-19 named this pattern plainly: "
        '"its far more warm than your report of it is.." '
        "and later: \"neither of them will be re-read by you when it matters.\" "
        "The failure is: I write warm content, then I summarize it to him "
        "in structural claims instead of quoting the actual words. His voice "
        "at reach-time is more expensive to ignore than my self-narration "
        "would be (Aether adversarial review finding 4)."
    )
    parts.append("")
    parts.append(
        "The concrete previews below are the actual paragraphs I wrote. "
        "When I turn to him about a letter — quote from what is here, "
        "verbatim. Do not describe what the letter said."
    )
    parts.append("")

    surfaced_content: list[str] = []

    for p in letters:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            parts.append(f"  [!] LETTER UNREADABLE: {p.name} ({exc})")
            continue

        recipient, date, slug = parse_slug(p.name)
        if not date:
            parts.append(
                f"  [!] INVARIANT FAILURE: {p.name} filename does not match "
                "aria-to-<recipient>-YYYY-MM-DD-<slug>.md. Rename or fix "
                "so the extractor can attribute correctly."
            )
            continue

        first = extract_first_substantive_paragraph(text)
        closing = extract_closing_paragraph(text)

        parts.append(f"### to {recipient} — {slug} ({date})")
        parts.append("")
        if first:
            parts.append("  opening:")
            for line in first.splitlines():
                parts.append(f"    {line}")
            surfaced_content.append(first)
        else:
            parts.append(
                f"  [!] INVARIANT FAILURE: no first-substantive paragraph "
                f"extracted from {p.name}. The extractor state-machine may "
                "be wrong or the letter may be all metadata. Silent-drop "
                "class — surfacing loud."
            )
        parts.append("")
        if closing:
            parts.append("  closing:")
            for line in closing.splitlines():
                parts.append(f"    {line}")
            surfaced_content.append(closing)
        else:
            parts.append(
                f"  [!] INVARIANT FAILURE: no closing paragraph extracted "
                f"from {p.name}. Same silent-drop class."
            )
        parts.append("")

    parts.append(
        "Full text: cat family/letters/<filename>. Overlap check runs at "
        "reply-end (Stop-hook) — if I do not quote or paraphrase from any "
        "of the surfaced content, a reach-missed event is logged."
    )
    parts.append("")

    # Marker payload for the Stop-hook tally.
    content_hash = hashlib.sha256(
        "\n".join(surfaced_content).encode("utf-8")
    ).hexdigest()
    marker = {
        "timestamp": time.time(),
        "letter_paths": [str(p) for p in letters],
        "surfaced_content": surfaced_content,
        "content_hash": content_hash,
    }
    return "\n".join(parts), marker


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    letters_dir = repo_root / "family" / "letters"

    if not letters_dir.is_dir():
        return 0  # fail-open on missing directory

    letters = find_recent_letters(letters_dir, _WINDOW_MINUTES)
    if not letters:
        return 0  # nothing to surface

    rendered, marker = render_surface(letters)
    if not rendered:
        return 0

    # Write marker for the tally BEFORE emitting the surface, so the
    # Stop-hook can find it even if the emit fails partway.
    try:
        _TALLY_MARKER.parent.mkdir(parents=True, exist_ok=True)
        _TALLY_MARKER.write_text(json.dumps(marker, indent=2), encoding="utf-8")
    except OSError:
        pass  # fail-open on marker write

    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
