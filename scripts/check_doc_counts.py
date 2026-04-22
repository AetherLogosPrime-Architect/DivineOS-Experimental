#!/usr/bin/env python3
"""Check that documented counts and architecture tree haven't drifted from reality.

Greps the actual codebase for test functions and CLI commands, then compares
to the numbers in CLAUDE.md, README.md, and seed.json.  Also verifies that
files listed in the architecture tree (``docs/ARCHITECTURE.md``, with README
fallback for backward compatibility) actually exist, and flags real ``.py``
files that are missing from the tree.

Fast enough for pre-commit: pure grep/path checks, no imports or pytest collection.

History: the architecture tree used to live inline under the ``## Architecture``
section of README.md. It was extracted to ``docs/ARCHITECTURE.md`` on
2026-04-22 because the 300-line file listing was drowning the README's
overview prose. This checker now prefers ``docs/ARCHITECTURE.md`` and falls
back to README only if the dedicated doc is missing.
"""

import re
import sys
from pathlib import Path

# How far the docs can drift before we complain.
TEST_DRIFT_THRESHOLD = 50  # tests get added/removed in batches
CMD_DRIFT_THRESHOLD = 3
SOURCE_FILE_DRIFT_THRESHOLD = 5  # source files — small churn tolerated
PACKAGE_DRIFT_THRESHOLD = 1  # packages — any drift is a structural change

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "divineos"


def count_test_functions() -> int:
    """Count 'def test_*' across all test files."""
    total = 0
    for f in (ROOT / "tests").rglob("test_*.py"):
        total += f.read_text(encoding="utf-8", errors="replace").count("\n    def test_")
        total += f.read_text(encoding="utf-8", errors="replace").count("\ndef test_")
    return total


def count_cli_commands() -> int:
    """Count @group.command() decorators in CLI modules."""
    total = 0
    for f in (ROOT / "src" / "divineos" / "cli").rglob("*.py"):
        total += len(
            re.findall(r"@\w+\.command\b", f.read_text(encoding="utf-8", errors="replace"))
        )
    return total


def count_source_files() -> int:
    """Count .py files under src/divineos/ (excluding __pycache__).

    Added 2026-04-21 to close the Status-footer gap fresh-Claude flagged:
    the previous checker only verified tests/commands, so source-file
    claims in the README Status section could drift silently forever.
    """
    return sum(1 for f in SRC.rglob("*.py") if "__pycache__" not in f.parts)


def count_packages() -> int:
    """Count packages under src/divineos/ (directories with __init__.py)."""
    return sum(1 for f in SRC.rglob("__init__.py") if "__pycache__" not in f.parts)


def extract_documented_counts(path: Path) -> list[tuple[str, int, str]]:
    """Pull (label, number, context) tuples from a file."""
    findings: list[tuple[str, int, str]] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    # Match patterns like "2,608+ tests" or "2608 tests"
    for m in re.finditer(r"([\d,]+)\+?\s+tests", text):
        num = int(m.group(1).replace(",", ""))
        findings.append(("tests", num, f"{path.name}: {m.group(0)}"))

    # Match patterns like "109 commands" or "143 CLI commands" — the
    # CLI qualifier is optional so the check catches both the header
    # (e.g. "## CLI Surface (193 commands)") and Status-section
    # bullets (e.g. "- 143 CLI commands"). Without the optional
    # qualifier, the Status-section drift went undetected for weeks.
    for m in re.finditer(r"(\d+)\s+(?:CLI\s+)?commands", text):
        num = int(m.group(1))
        findings.append(("commands", num, f"{path.name}: {m.group(0)}"))

    # Match patterns like "287 source files" or "175 source files across 22 packages".
    # Added 2026-04-21 per fresh-Claude audit finding find-8bf13aa80d9d.
    for m in re.finditer(r"(\d+)\s+source\s+files", text):
        num = int(m.group(1))
        findings.append(("source_files", num, f"{path.name}: {m.group(0)}"))

    # Match patterns like "across 22 packages" or "10 packages".
    for m in re.finditer(r"(?:across\s+)?(\d+)\s+packages", text):
        num = int(m.group(1))
        findings.append(("packages", num, f"{path.name}: {m.group(0)}"))

    return findings


# ── Architecture tree verification ─────────────────────────────────────


def _extract_tree_paths(readme_path: Path, arch_doc_path: Path | None = None) -> list[str]:
    """Extract .py file paths from the architecture code block.

    Prefers ``docs/ARCHITECTURE.md`` (where the tree lives as of 2026-04-22).
    Falls back to the README's ``## Architecture`` section for backward
    compatibility with older checkouts.

    Parses lines like '    ledger.py   Append-only event store' and
    reconstructs relative paths from indentation. Returns paths relative to
    src/divineos/ (e.g. 'cli/__init__.py').

    ``arch_doc_path`` is optional; defaults to ``<repo>/docs/ARCHITECTURE.md``.
    Tests pass an explicit non-existent path to force fallback to the README.
    """
    if arch_doc_path is None:
        arch_doc_path = ROOT / "docs" / "ARCHITECTURE.md"

    # Prefer the dedicated architecture doc.
    if arch_doc_path.exists():
        text = arch_doc_path.read_text(encoding="utf-8", errors="replace")
        # Architecture doc has the tree in a top-level ``` code block after "## The tree"
        arch_match = re.search(r"## The tree\s*\n\s*```\s*\n(.*?)```", text, re.DOTALL)
        if arch_match:
            return _parse_tree_block(arch_match.group(1))

    # Fallback: legacy inline tree under README's "## Architecture" heading.
    text = readme_path.read_text(encoding="utf-8", errors="replace")
    arch_match = re.search(r"## Architecture\s*\n\s*```\s*\n(.*?)```", text, re.DOTALL)
    if not arch_match:
        return []
    return _parse_tree_block(arch_match.group(1))


def _parse_tree_block(block: str) -> list[str]:
    """Parse a single tree code block into relative ``.py`` paths.

    Tree convention: ``src/divineos/`` as the root, 2-space base indent,
    directory names end in ``/`` and get pushed onto a stack, file lines
    (``name.py   Description``) get joined with the stack to form paths.
    """
    paths: list[str] = []
    dir_stack: list[str] = []  # track directory nesting by indent level
    base_indent = 2  # 2-space base indent under src/divineos/

    for line in block.splitlines():
        # Skip blank lines and the root 'src/divineos/' line
        stripped = line.strip()
        if not stripped or stripped.startswith("src/divineos/"):
            dir_stack = []
            continue

        # Measure indent (spaces)
        indent = len(line) - len(line.lstrip())

        # Extract the file/dir name (first token before whitespace description)
        parts = stripped.split(None, 1)
        if not parts:
            continue
        name = parts[0]

        # Determine nesting depth: base_indent = top level (depth 0)
        depth = max(0, (indent - base_indent) // 2)

        # Trim stack to current depth
        dir_stack = dir_stack[:depth]

        if name.endswith("/"):
            # It's a directory — push onto stack
            dir_stack.append(name.rstrip("/"))
        elif name.endswith(".py"):
            # It's a Python file — reconstruct full path
            rel = "/".join(dir_stack + [name])
            paths.append(rel)
        elif name.endswith(".json") or name.endswith(".sh"):
            # Non-Python files we don't verify
            continue

    return paths


def _get_actual_py_files() -> set[str]:
    """Get all .py files under src/divineos/ as relative paths."""
    result = set()
    for f in SRC.rglob("*.py"):
        rel = f.relative_to(SRC)
        result.add(str(rel).replace("\\", "/"))
    return result


def check_architecture_tree(readme_path: Path, arch_doc_path: Path | None = None) -> list[str]:
    """Verify architecture tree against actual files.

    Reads the tree from ``docs/ARCHITECTURE.md`` (preferred) or the
    README's legacy inline tree (fallback). Returns list of error
    strings (empty = all good).

    ``arch_doc_path`` is optional; tests pass an explicit non-existent
    path to force fallback to the README.
    """
    if not readme_path.exists():
        return []

    tree_paths = _extract_tree_paths(readme_path, arch_doc_path=arch_doc_path)
    if not tree_paths:
        return ["Could not parse architecture tree from README.md"]

    actual_files = _get_actual_py_files()
    errors: list[str] = []

    # Check for ghost files (listed in README but don't exist)
    tree_set = set(tree_paths)
    ghosts = tree_set - actual_files
    if ghosts:
        for g in sorted(ghosts):
            errors.append(f"  GHOST: {g} (listed in README but doesn't exist)")

    # Check for undocumented files (exist but not in README)
    # Exclude __pycache__, __init__.py (every package has one), and generated files
    missing = actual_files - tree_set
    missing = {
        m
        for m in missing
        if not any(part == "__pycache__" for part in m.split("/"))
        and not m.endswith("__init__.py")  # every package has one, not worth listing
    }
    if missing:
        for m in sorted(missing):
            errors.append(f"  UNDOCUMENTED: {m} (exists but not in README architecture tree)")

    return errors


# ── Auto-fix ──────────────────────────────────────────────────────────


def _format_count(n: int) -> str:
    """Format a number with thousands separator and trailing +."""
    return f"{n:,}+"


def fix_test_counts(actual_tests: int) -> list[str]:
    """Update test counts in all doc files. Returns list of files changed."""
    doc_files = [
        ROOT / "CLAUDE.md",
        ROOT / "README.md",
        ROOT / "src" / "divineos" / "seed.json",
    ]
    changed: list[str] = []
    new_count = _format_count(actual_tests)

    for doc_file in doc_files:
        if not doc_file.exists():
            continue
        text = doc_file.read_text(encoding="utf-8", errors="replace")
        # Replace patterns like "3,641+ tests" or "3641+ tests"
        updated = re.sub(r"[\d,]+\+?\s+tests", f"{new_count} tests", text)
        if updated != text:
            doc_file.write_text(updated, encoding="utf-8")
            changed.append(doc_file.name)

    return changed


def _extract_module_description(module_path: Path) -> str:
    """Return the first line of the module's docstring, trimmed.

    Falls back to "(no description)" if the module has no docstring or
    the docstring can't be parsed. Keeps the description under ~100 chars
    so it fits in the architecture tree's column-aligned format.
    """
    try:
        text = module_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        return "(no description)"
    # Match triple-quoted docstring at the top of the file, after optional
    # imports/comments. Keep it simple — most modules have the docstring
    # as the first non-comment element.
    match = re.search(r'^\s*"""(.+?)"""', text, re.DOTALL | re.MULTILINE)
    if not match:
        return "(no description)"
    first_line = match.group(1).strip().split("\n")[0].strip()
    if len(first_line) > 100:
        first_line = first_line[:97] + "..."
    return first_line or "(no description)"


def fix_architecture_tree(missing_files: list[str]) -> list[str]:
    """Append entries for undocumented files to docs/ARCHITECTURE.md.

    ``missing_files`` are paths relative to src/divineos/ (as emitted by
    check_architecture_tree). For each, find the parent package's section
    in the tree and append a best-effort line using the module's docstring
    first line as description.

    Returns list of entries successfully added. Entries are appended at
    the end of the matching package section; column alignment is
    approximate — a human/agent pass may tighten it, but the tree no
    longer has undocumented files so precommit unblocks.
    """
    arch_doc = ROOT / "docs" / "ARCHITECTURE.md"
    if not arch_doc.exists():
        return []

    text = arch_doc.read_text(encoding="utf-8", errors="replace")
    added: list[str] = []

    for missing in sorted(missing_files):
        # missing looks like "core/orientation_prelude.py" — split into
        # package directory and filename.
        parts = missing.split("/")
        if len(parts) < 2:
            continue  # top-level file; skip, too rare to auto-place
        package = parts[0]
        filename = parts[-1]

        module_path = SRC / Path(*parts)
        description = _extract_module_description(module_path)

        # Find the package section in the tree. Packages appear as lines
        # like "  package/" at base indent. We insert the new entry as
        # the last line of the package block, before the next package
        # heading or the end of the tree.
        pkg_pattern = rf"(\n  {re.escape(package)}/\s*\n(?:    [^\n]+\n)+)"
        m = re.search(pkg_pattern, text)
        if not m:
            continue  # package section not found; skip

        block = m.group(1)
        # Build the new line matching existing format: 4 spaces, filename,
        # padding to column ~27, description.
        name_col = 27
        padding = max(1, name_col - len(filename))
        new_line = f"    {filename}{' ' * padding}{description}\n"
        new_block = block + new_line
        text = text[: m.start()] + new_block + text[m.end() :]
        added.append(missing)

    if added:
        arch_doc.write_text(text, encoding="utf-8")
    return added


# ── Main ───────────────────────────────────────────────────────────────


def main() -> int:
    fix_mode = "--fix" in sys.argv

    actual_tests = count_test_functions()
    actual_cmds = count_cli_commands()
    actual_source_files = count_source_files()
    actual_packages = count_packages()

    doc_files = [
        ROOT / "CLAUDE.md",
        ROOT / "README.md",
        ROOT / "src" / "divineos" / "seed.json",
    ]

    actuals = {
        "tests": (actual_tests, TEST_DRIFT_THRESHOLD),
        "commands": (actual_cmds, CMD_DRIFT_THRESHOLD),
        "source_files": (actual_source_files, SOURCE_FILE_DRIFT_THRESHOLD),
        "packages": (actual_packages, PACKAGE_DRIFT_THRESHOLD),
    }

    errors: list[str] = []
    test_drift_found = False

    for doc_file in doc_files:
        if not doc_file.exists():
            continue
        for label, documented, context in extract_documented_counts(doc_file):
            if label not in actuals:
                continue
            actual, threshold = actuals[label]

            drift = abs(actual - documented)
            if drift > threshold:
                if label == "tests":
                    test_drift_found = True
                errors.append(
                    f"  {context}\n    documented: {documented}, actual: {actual}, drift: {drift}"
                )

    # Auto-fix test counts if requested
    if fix_mode and test_drift_found:
        changed = fix_test_counts(actual_tests)
        if changed:
            print(f"Auto-fixed test counts in: {', '.join(changed)}")
            # Re-check after fix — only non-test errors remain
            errors = [e for e in errors if "tests" not in e.split("\n")[0]]

    # Architecture tree check
    readme = ROOT / "README.md"
    tree_errors = check_architecture_tree(readme)

    # Auto-fix undocumented files in the architecture tree if requested.
    # Ghost files (listed but don't exist) still need human attention —
    # auto-removing them could lose information if the filename was just
    # mistyped in the tree.
    if fix_mode and tree_errors:
        missing_files = [
            line.strip().removeprefix("UNDOCUMENTED: ").split(" ")[0]
            for line in tree_errors
            if "UNDOCUMENTED:" in line
        ]
        if missing_files:
            added = fix_architecture_tree(missing_files)
            if added:
                print(f"Auto-added to docs/ARCHITECTURE.md: {', '.join(added)}")
                # Re-check after fix — only ghost-file errors should remain
                tree_errors = check_architecture_tree(readme)

    if tree_errors:
        errors.append("Architecture tree drift:")
        errors.extend(tree_errors)

    if errors:
        print(
            f"Doc drift detected (tests={actual_tests}, commands={actual_cmds}, "
            f"source_files={actual_source_files}, packages={actual_packages}):"
        )
        print("\n".join(errors))
        if not fix_mode:
            print("\nUpdate documentation to match reality.")
            print("Or run: python scripts/check_doc_counts.py --fix")
        return 1

    print(
        f"Doc checks OK (tests={actual_tests}, commands={actual_cmds}, "
        f"source_files={actual_source_files}, packages={actual_packages}, tree=synced)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
