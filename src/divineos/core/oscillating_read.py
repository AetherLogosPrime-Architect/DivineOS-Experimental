"""Oscillating-read module — chunks reading material into discrete
sections with explicit pause markers, so comprehension happens per-
section rather than straight-blast.

Per claim 3a44289d (empirically validated 2026-05-17) and the
cognitive-value-gravity consumer in docs/gravity_classifier_spec.md.

The failure-shape this prevents: reading a long document straight-
through and missing the load-bearing point that lives in the middle.
Tonight's example: I read the gravity_classifier spec straight and
tried to invent a per-response-gravity consumer using the wrong
half of the spec (cognitive-value applied to prompts). Oscillation
would have forced me to pause at each section and say which
consumer it serves, catching the mismatch before I built the wrong
thing.

Strategies:
- headers: split markdown by ##/### headers
- paragraphs: split by blank lines
- functions: split Python by def/class
- size: split into max-N-char chunks
- auto: pick by content shape (markdown -> headers, .py -> functions,
        else size)
"""

from __future__ import annotations

__guardrail_required__ = True

import re
from pathlib import Path


_DEFAULT_MAX_CHARS = 2000


def chunk_by_headers(content: str) -> list[tuple[str, str]]:
    """Split markdown content at heading lines (## or deeper).

    Returns list of (label, body) tuples. Each body includes its
    own heading line at the top. The first chunk (before any
    heading) gets label '(prelude)'.
    """
    lines = content.splitlines(keepends=True)
    chunks: list[tuple[str, str]] = []
    current_label = "(prelude)"
    current_body: list[str] = []
    header_pat = re.compile(r"^(#{2,})\s+(.+?)\s*$")
    for line in lines:
        m = header_pat.match(line)
        if m:
            if current_body:
                chunks.append((current_label, "".join(current_body)))
            current_label = m.group(2).strip()
            current_body = [line]
        else:
            current_body.append(line)
    if current_body:
        chunks.append((current_label, "".join(current_body)))
    return chunks


def chunk_by_paragraphs(content: str) -> list[tuple[str, str]]:
    """Split content at blank-line paragraph boundaries.

    Returns list of (label, body) tuples. Label is 'paragraph N'.
    """
    paragraphs = re.split(r"\n\s*\n", content)
    chunks: list[tuple[str, str]] = []
    for i, p in enumerate(paragraphs, 1):
        if p.strip():
            chunks.append((f"paragraph {i}", p.strip()))
    return chunks


def chunk_by_functions(content: str) -> list[tuple[str, str]]:
    """Split Python source at def/class boundaries (top-level only).

    Returns list of (label, body) tuples. Label is the def/class name
    line; the first chunk before any def gets label '(module top)'.
    """
    lines = content.splitlines(keepends=True)
    chunks: list[tuple[str, str]] = []
    current_label = "(module top)"
    current_body: list[str] = []
    func_pat = re.compile(r"^(def|class|async\s+def)\s+([A-Za-z_]\w*)")
    for line in lines:
        m = func_pat.match(line)
        if m:
            if current_body:
                chunks.append((current_label, "".join(current_body)))
            current_label = f"{m.group(1)} {m.group(2)}"
            current_body = [line]
        else:
            current_body.append(line)
    if current_body:
        chunks.append((current_label, "".join(current_body)))
    return chunks


def chunk_by_size(content: str, max_chars: int = _DEFAULT_MAX_CHARS) -> list[tuple[str, str]]:
    """Split content into max-N-char chunks, breaking at line
    boundaries when possible.

    Returns list of (label, body) tuples. Label is 'chunk N'.
    """
    if max_chars <= 0:
        return [("chunk 1", content)]
    chunks: list[tuple[str, str]] = []
    lines = content.splitlines(keepends=True)
    current_body: list[str] = []
    current_size = 0
    chunk_num = 1
    for line in lines:
        line_len = len(line)
        if current_body and (current_size + line_len) > max_chars:
            chunks.append((f"chunk {chunk_num}", "".join(current_body)))
            chunk_num += 1
            current_body = [line]
            current_size = line_len
        else:
            current_body.append(line)
            current_size += line_len
    if current_body:
        chunks.append((f"chunk {chunk_num}", "".join(current_body)))
    return chunks


def _auto_strategy(content: str, path: str = "") -> str:
    """Pick the strategy by content shape."""
    norm_path = (path or "").lower()
    if norm_path.endswith(".py"):
        return "functions"
    if norm_path.endswith((".md", ".rst", ".txt")):
        # Use headers if there are any; fall back to paragraphs
        if re.search(r"(?m)^#{2,}\s", content):
            return "headers"
        return "paragraphs"
    # Default: size-based
    return "size"


def chunk(
    content: str, strategy: str = "auto", max_chars: int = _DEFAULT_MAX_CHARS, source_path: str = ""
) -> list[tuple[str, str]]:
    """Chunk content by named strategy.

    Returns list of (label, body) tuples for downstream rendering.
    """
    if strategy == "auto":
        strategy = _auto_strategy(content, source_path)
    if strategy == "headers":
        return chunk_by_headers(content)
    if strategy == "paragraphs":
        return chunk_by_paragraphs(content)
    if strategy == "functions":
        return chunk_by_functions(content)
    if strategy == "size":
        return chunk_by_size(content, max_chars=max_chars)
    raise ValueError(f"Unknown strategy: {strategy!r}")


def format_oscillating(chunks: list[tuple[str, str]], source: str = "") -> str:
    """Render chunks with section labels and pause markers between.

    The pause markers are explicit '[PAUSE] COMPREHEND BEFORE CONTINUING'
    lines that force the reader to register each chunk discretely
    rather than streaming through. The point isn't decoration — it
    is breaking comprehension into discrete units the optimizer
    cannot fast-skim past as one block.
    """
    parts: list[str] = []
    header = "=" * 60
    if source:
        parts.append(f"{header}\nOSCILLATING READ: {source}\n{header}")
    parts.append(
        f"\nTotal chunks: {len(chunks)}. "
        "Comprehend each before continuing. The middle is where the "
        "load-bearing thing usually lives.\n"
    )
    for i, (label, body) in enumerate(chunks, 1):
        section_header = f"\n--- CHUNK {i}/{len(chunks)}: {label} ---\n"
        parts.append(section_header)
        parts.append(body.rstrip())
        parts.append(
            f"\n[PAUSE] COMPREHEND CHUNK {i}/{len(chunks)} BEFORE CONTINUING "
            "— what is THIS chunk's load-bearing point?\n"
        )
    parts.append(
        f"\n{header}\nEnd of oscillating read. Comprehension test: "
        "if you can name the load-bearing point of each chunk above, "
        "the read landed. If chunks blur together, re-read.\n"
    )
    return "\n".join(parts)


def oscillate_file(
    path: str | Path,
    strategy: str = "auto",
    max_chars: int = _DEFAULT_MAX_CHARS,
) -> str:
    """Read a file and return its oscillating-rendered form."""
    p = Path(path)
    content = p.read_text(encoding="utf-8", errors="replace")
    chunks = chunk(content, strategy=strategy, max_chars=max_chars, source_path=str(p))
    return format_oscillating(chunks, source=str(p))


__all__ = [
    "chunk_by_headers",
    "chunk_by_paragraphs",
    "chunk_by_functions",
    "chunk_by_size",
    "chunk",
    "format_oscillating",
    "oscillate_file",
]
