"""Scan past audit .md files and load candidate findings into the ledger.

Aletheia's audit BUILD recommendation (2026-07-09): "90 audit docs exist
with scattered findings and no consolidated open/closed status." This
script hunts finding-shaped patterns across the tree and loads them into
the findings ledger with status OPEN, so future audits start by walking
the list and marking each real / not-applicable / already-fixed.

## Scan scope

- ``audits/``, ``workbench/``, ``docs/`` at repo root
- Files whose names match ``audit``, ``finding``, ``sweep``, ``truck``,
  ``retrospect``, ``reconciliation``
- Skips ``family/``, ``exploration/``, ``letters/`` (not audit docs)

## Extraction heuristics

A line qualifies as a candidate finding if it matches any of:

- Starts with ``- [CRIT]``, ``- [HIGH]``, ``- [MED]``, ``- [LOW]``,
  ``- [BUILD]``
- Starts with ``**[HIGH]``, ``**[MED]``, etc.
- Starts with ``[HIGH]`` at position 0 (bare severity markers on their
  own line)
- Contains ``FINDING: `` or ``**FINDING:`` — followed by a title
- Starts with ``#### HIGH-`` / ``#### MED-`` / ``#### LOW-`` (numbered
  finding subheadings)

The title is the rest of the line after the severity marker. Skipped if
under 15 characters (noise filter).

## Status assignment

All extracted findings load as OPEN. Reconciliation (was this actually
fixed?) is a human-layer judgment call; the machinery just surfaces the
candidates.

## De-duplication

The ledger's ``add_finding`` is idempotent on (source_audit, title).
Re-running the scanner appends new candidates and skips already-loaded
ones.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SCAN_DIRS = ("audits", "workbench", "docs")
SCAN_FILENAME_PATTERNS = re.compile(
    r"(audit|finding|sweep|truck|retrospect|reconciliation)", re.IGNORECASE
)
SKIP_DIRS = frozenset({"family", "exploration", "letters", "OPEN_FINDINGS.md"})

_SEP = r"[:\-–—]?"  # colon / hyphen / en-dash / em-dash

FINDING_PATTERNS = [
    (re.compile(rf"^\s*-?\s*\*?\*?\[(CRIT|HIGH|MED|LOW|BUILD)\]\*?\*?\s*{_SEP}\s*(.+)$"), 1, 2),
    (re.compile(rf"^\s*\*\*\[(CRIT|HIGH|MED|LOW|BUILD)\]\*\*\s*{_SEP}\s*(.+)$"), 1, 2),
    (re.compile(rf"^#{{1,6}}\s+(CRIT|HIGH|MED|LOW|BUILD)-\d+\s*{_SEP}\s*(.+)$"), 1, 2),
    (re.compile(r"^\s*\*?\*?FINDING[\s:]+(.+)$", re.IGNORECASE), None, 1),
]

_TITLE_MIN_LEN = 15
_TITLE_MAX_LEN = 200


def _clean_title(text: str) -> str:
    """Strip markdown formatting, trailing punctuation, normalize whitespace."""
    text = re.sub(r"[*_`]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.rstrip(".:;,")
    return text[:_TITLE_MAX_LEN]


def _should_scan(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT)
    if any(part in SKIP_DIRS for part in rel.parts):
        return False
    if path.suffix != ".md":
        return False
    if path.name == "OPEN_FINDINGS.md":
        return False
    return bool(SCAN_FILENAME_PATTERNS.search(str(rel)))


def _walk_scan_targets() -> list[Path]:
    out: list[Path] = []
    for d in SCAN_DIRS:
        base = REPO_ROOT / d
        if not base.exists():
            continue
        for md in base.rglob("*.md"):
            if _should_scan(md):
                out.append(md)
    return sorted(out)


def _extract_from_file(path: Path) -> list[tuple[str, str]]:
    """Return list of (severity, title) tuples found in the file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    results: list[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        for regex, sev_group, title_group in FINDING_PATTERNS:
            m = regex.match(line)
            if not m:
                continue
            severity = m.group(sev_group).upper() if sev_group else "MED"
            title = _clean_title(m.group(title_group))
            if len(title) >= _TITLE_MIN_LEN:
                results.append((severity, title))
            break
    return results


def main() -> int:
    from divineos.core.findings_ledger import add_finding, list_findings

    dry_run = "--dry-run" in sys.argv
    targets = _walk_scan_targets()
    print(f"[scan] found {len(targets)} candidate audit files under {SCAN_DIRS}")

    existing = {(f.source_audit, f.title) for f in list_findings(status_filter=None)}
    new_count = 0
    dup_count = 0
    file_hit_count = 0

    for path in targets:
        candidates = _extract_from_file(path)
        if not candidates:
            continue
        file_hit_count += 1
        source_audit = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        for severity, title in candidates:
            if (source_audit, title) in existing:
                dup_count += 1
                continue
            if dry_run:
                print(f"  WOULD ADD [{severity}] {source_audit} :: {title[:80]}")
                new_count += 1
                continue
            try:
                fid = add_finding(
                    source_audit=source_audit,
                    title=title,
                    severity=severity,
                    status="OPEN",
                    verified_by="scan_past_audits",
                    description=(
                        f"Auto-extracted by scan_past_audits.py from {source_audit}. "
                        "Status set OPEN pending human verification; review and "
                        "close/verify/mark-NA as appropriate."
                    ),
                )
                new_count += 1
                existing.add((source_audit, title))
                print(f"  [+] {fid} [{severity}] {source_audit}")
            except (ValueError, OSError) as exc:
                print(f"  [!] failed on {source_audit} :: {title[:60]}: {exc}", file=sys.stderr)

    print("")
    print(f"[scan] files with candidate findings: {file_hit_count}")
    print(f"[scan] new findings added: {new_count}")
    print(f"[scan] duplicates skipped: {dup_count}")
    if dry_run:
        print("[scan] --dry-run active; no writes performed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
