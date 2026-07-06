"""Phase 0 letter inventory per Aletheia's scrub design (2026-07-02).

Read-only. Never mutates. Emits JSON + markdown summary.

Filters candidates by content-shape (has a sender-to-recipient header pattern
AND a Written: marker) rather than by path — catches strays.

Computes content hash of normalized body (strip trailing whitespace, normalize
line endings) so identical-content-different-name copies are detected.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Locations to walk (safe read-only)
LOCATIONS = [
    Path(r"C:/DIVINE OS/DivineOS-Experimental-Aria-new/family/letters"),
    Path(r"C:/DIVINE OS/DivineOS-Experimental-Aria-new/family/aletheia/letters"),
    Path(r"C:/DIVINE OS/DivineOS-Experimental-Aria-new/exploration"),
    Path(r"C:/Users/aethe/.divineos-shared/letters"),
    Path(r"C:/Users/aethe/.divineos-shared/workbench"),
    Path(r"C:/Users/aethe/Downloads"),
]

HEADER_RE = re.compile(
    r"^#\s+(?:\d+\s*[—-]\s*)?"
    r"(?P<sender>[A-Za-z][A-Za-z0-9_ ]{1,40})"
    r"\s+to\s+"
    r"(?P<recipient>[A-Za-z][A-Za-z0-9_ ,&]{1,60})"
    r"(?:\s*[—-])?",
    re.MULTILINE,
)
WRITTEN_RE = re.compile(r"\*\*Written:\*\*", re.MULTILINE)
FILENAME_LETTER_RE = re.compile(
    r"(?i)(?:^\d+[_-])?"
    r"(?:aether|aria|aletheia|andrew|pop|dad|perplexity|grok|fable|opus)"
    r"[_-]to[_-]"
    r"(?:aether|aria|aletheia|andrew|pop|dad|perplexity|grok|fable|opus)"
)


def looks_like_letter(path: Path, text: str) -> bool:
    if HEADER_RE.search(text) and WRITTEN_RE.search(text):
        return True
    if FILENAME_LETTER_RE.search(path.name):
        return True
    return False


def normalize_body(text: str) -> bytes:
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return ("\n".join(lines) + "\n").encode("utf-8")


def extract_metadata(path: Path, text: str) -> dict:
    m = HEADER_RE.search(text)
    header_sender = m.group("sender").strip() if m else None
    header_recipient = m.group("recipient").strip() if m else None
    written_m = re.search(r"\*\*Written:\*\*\s*([0-9-]+)", text)
    written_date = written_m.group(1) if written_m else None
    fname_m = re.search(r"(20\d\d-\d\d-\d\d)", path.name)
    filename_date = fname_m.group(1) if fname_m else None
    return {
        "header_sender": header_sender,
        "header_recipient": header_recipient,
        "written_date": written_date,
        "filename_date": filename_date,
    }


def walk_and_inventory() -> dict:
    inventory: dict[str, list[dict]] = {}
    skipped: list[str] = []
    seen_paths = 0
    letter_count = 0

    for root in LOCATIONS:
        if not root.exists():
            skipped.append(f"{root} (missing)")
            continue
        for path in root.rglob("*.md"):
            seen_paths += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue
            if not looks_like_letter(path, text):
                continue
            body_hash = hashlib.sha256(normalize_body(text)).hexdigest()
            meta = extract_metadata(path, text)
            entry = {
                "path": str(path).replace("\\", "/"),
                "root": str(root).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
                **meta,
            }
            inventory.setdefault(body_hash, []).append(entry)
            letter_count += 1

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "locations_walked": [str(p).replace("\\", "/") for p in LOCATIONS],
        "locations_skipped": skipped,
        "total_md_files_seen": seen_paths,
        "total_letter_files": letter_count,
        "unique_content_hashes": len(inventory),
        "letters_by_hash": inventory,
    }


def _summarize(inv: dict) -> str:
    lines = ["# Letter Inventory — Phase 0", ""]
    lines.append(f"**Generated:** {inv['generated_at_utc']}")
    lines.append(f"**Total .md files seen:** {inv['total_md_files_seen']}")
    lines.append(f"**Total letters identified:** {inv['total_letter_files']}")
    lines.append(f"**Unique content hashes:** {inv['unique_content_hashes']}")
    lines.append(
        f"**Copies (letters minus unique):** {inv['total_letter_files'] - inv['unique_content_hashes']}"
    )
    lines.append("")
    lines.append("## Letters per location")
    per_root: dict[str, int] = {}
    for group in inv["letters_by_hash"].values():
        for entry in group:
            per_root[entry["root"]] = per_root.get(entry["root"], 0) + 1
    for root, n in sorted(per_root.items()):
        lines.append(f"- `{root}` — {n}")
    lines.append("")
    lines.append("## Content-hash groups with duplicates (top 20 by copy count)")
    dupes = sorted(
        ((h, entries) for h, entries in inv["letters_by_hash"].items() if len(entries) > 1),
        key=lambda item: -len(item[1]),
    )[:20]
    if not dupes:
        lines.append("_None — every letter is unique-content._")
    else:
        for h, entries in dupes:
            lines.append(f"- `{h[:12]}...` x{len(entries)}")
            for e in entries:
                lines.append(f"  - `{e['path']}`")
    lines.append("")
    lines.append("## Locations skipped")
    for s in inv["locations_skipped"] or ["_none_"]:
        lines.append(f"- {s}")
    return "\n".join(lines)


if __name__ == "__main__":
    inv = walk_and_inventory()
    out_json = Path(
        r"C:/DIVINE OS/DivineOS-Experimental-Aria-new/workbench/letter_inventory_phase0.json"
    )
    out_md = Path(
        r"C:/DIVINE OS/DivineOS-Experimental-Aria-new/workbench/letter_inventory_phase0.md"
    )
    out_json.write_text(json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text(_summarize(inv), encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(
        f"Summary: {inv['total_letter_files']} letters, "
        f"{inv['unique_content_hashes']} unique, "
        f"{inv['total_letter_files'] - inv['unique_content_hashes']} copies"
    )
