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


def count_hooks_wired() -> int:
    """Count Claude Code hooks wired in .claude/settings.json.

    Round-2 audit (2026-05-07) found README claimed "9 enforcement hooks"
    while settings.json wired 16. The drift went undetected because this
    checker didn't track hook counts. Adding the check makes README hook
    claims structurally verified against the wiring source-of-truth.
    """
    import json

    settings_path = ROOT / ".claude" / "settings.json"
    if not settings_path.exists():
        return 0
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    total = 0
    for matchers in (data.get("hooks") or {}).values():
        if not isinstance(matchers, list):
            continue
        for matcher in matchers:
            if not isinstance(matcher, dict):
                continue
            total += len(matcher.get("hooks") or [])
    return total


def count_council_experts() -> int:
    """Count council expert factory functions (``create_*_wisdom``).

    Round-3 audit (2026-05-07, Grok external-review) flagged that README
    claimed 39 experts while the code had 40. Adding the check makes
    council-roster claims structurally verified against the experts
    package. Single-source: every roster member is a ``create_<name>_wisdom``
    factory in ``core/council/experts/``.
    """
    experts_dir = SRC / "core" / "council" / "experts"
    if not experts_dir.exists():
        return 0
    count = 0
    pat = re.compile(r"^def\s+create_\w+_wisdom\s*\(", re.MULTILINE)
    for p in experts_dir.glob("*.py"):
        if p.name == "__init__.py":
            continue
        try:
            count += len(pat.findall(p.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return count


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

    # Match "9 Claude Code enforcement hooks" / "9 enforcement hooks" /
    # "(9 hooks," — added 2026-05-07 per round-2 audit which found
    # README claimed 9 while settings.json wired 16.
    for m in re.finditer(
        r"(\d+)\s+(?:Claude Code\s+)?enforcement\s+hooks|\((\d+)\s+hooks,",
        text,
    ):
        num = int(m.group(1) or m.group(2))
        findings.append(("hooks", num, f"{path.name}: {m.group(0)}"))

    # Match council-expert claims: "40 expert frameworks" / "council of 40"
    # / "40-expert council" / "40 expert wisdom templates" / "40 expert lenses"
    # / "(40 members)". Round-3 (2026-05-07, Grok review).
    council_patterns = [
        r"(\d+)\s+expert\s+frameworks?",
        r"council\s+of\s+(\d+)",
        r"(\d+)-expert\s+council",
        r"(\d+)\s+expert\s+wisdom",
        r"(\d+)\s+expert\s+lenses",
        r"\((\d+)\s+members\)",
    ]
    for pat in council_patterns:
        for m in re.finditer(pat, text):
            num = int(m.group(1))
            findings.append(("council", num, f"{path.name}: {m.group(0)}"))

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


# Audit Tier 4 (2026-05-16): semantic file-path verification.
# Catches the "claims a file/branch/path exists when it doesn't" class
# of doc drift — e.g. mansion-room name fabrication, stale package list
# (supersession/clarity_enforcement/violations_cli still listed after
# deletion), Lite-branch reference that doesn't exist. Numeric drift
# was caught by check_*_counts; the semantic-existence class was not.
# Andrew named the gap 2026-05-16 after the README audit caught 16+
# fact-errors in cited paths and names.

_CITED_PATH_PATTERNS = [
    # Backticked path-like strings: `foo/bar.py`, `core/family/`
    re.compile(r"`((?:[a-zA-Z_][\w\-.]*/)+[a-zA-Z_][\w\-.]*(?:\.[a-zA-Z]+)?)(?::\d+)?`"),
    # Markdown link href to a relative file: [label](path/to/file.ext)
    re.compile(r"\]\(((?:\./|(?!https?:|mailto:|#))[a-zA-Z_][\w\-./]*\.(?:py|md|sh|json|yml|yaml|toml|txt|cfg))\)"),
]

# Extensions / patterns to verify on disk. Paths without these are skipped
# (they may be CLI command names, package names, or other non-file refs).
_VERIFIABLE_EXTENSIONS = (".py", ".md", ".sh", ".json", ".yml", ".yaml", ".toml", ".txt", ".cfg")

# Paths to skip even if matched (known non-disk references, environment
# variables, placeholders, common false-positives from prose).
_SKIP_PATHS = {
    # Common variable-style references that look like paths
    "./", "../",
}


def _extract_cited_paths(doc_path: Path) -> set[str]:
    """Pull out file-path-like strings cited in a documentation file."""
    if not doc_path.exists():
        return set()
    text = doc_path.read_text(encoding="utf-8", errors="replace")
    cited: set[str] = set()
    for pat in _CITED_PATH_PATTERNS:
        for match in pat.finditer(text):
            path = match.group(1)
            # Strip line-number suffix (foo.py:123 -> foo.py)
            if ":" in path and path.rsplit(":", 1)[1].isdigit():
                path = path.rsplit(":", 1)[0]
            # Strip trailing slash for directory checks
            stripped = path.rstrip("/")
            # Only keep paths with verifiable extension OR clearly-directory paths
            if path.endswith("/") or any(stripped.endswith(ext) for ext in _VERIFIABLE_EXTENSIONS):
                if path not in _SKIP_PATHS:
                    cited.add(path)
    return cited


def _resolve_cited_path(path: str) -> Path | None:
    """Try multiple resolution conventions. Return existing path or None.

    The docs use multiple conventions: repo-root-relative (tests/foo.py),
    src/divineos-relative (core/foo.py meaning src/divineos/core/foo.py),
    or full paths (src/divineos/core/foo.py). Try each.
    """
    stripped = path.rstrip("/")
    candidates = [
        ROOT / stripped,
        ROOT / "src" / "divineos" / stripped,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def check_cited_paths(doc_paths: list[Path]) -> list[str]:
    """Verify file/directory paths cited in docs actually exist on disk.

    Returns list of error strings (empty = all good). Each error names
    the missing path and the doc that cited it.

    Catches the fact-error class: "doc claims X exists when it doesn'''t"
    (fabricated mansion rooms, deleted packages still listed, stale
    branch references, wrong file paths in operator-readable docs).

    Resolution tries both repo-root-relative and src/divineos-relative
    paths since the docs use both conventions.
    """
    errors: list[str] = []
    for doc in doc_paths:
        if not doc.exists():
            continue
        cited = _extract_cited_paths(doc)
        for path in sorted(cited):
            if _resolve_cited_path(path) is None:
                rel_doc = doc.relative_to(ROOT) if ROOT in doc.parents else doc.name
                errors.append(f"  MISSING-CITED-PATH: {path} (cited in {rel_doc} but not found on disk)")
    return errors



# ── Auto-fix ──────────────────────────────────────────────────────────


def _format_count(n: int) -> str:
    """Format a number with thousands separator and trailing +."""
    return f"{n:,}+"


def fix_test_counts(actual_tests: int) -> list[str]:
    """Update test counts in all doc files. MONOTONIC: only raise, never lower.

    Andrew 2026-06-12: every branch auto-fixing the doc counts was creating
    cross-branch rebase conflicts on CLAUDE.md/README.md/ARCHITECTURE.md
    (two branches both bumping to slightly different numbers → conflict on
    rebase). Monotonic-only-raise solves it: branches with HIGHER counts
    update the docs; branches with LOWER counts (because they merged after
    a higher-count PR landed) become no-ops. No conflict, no manual fix tax.

    Net effect: the docs always reflect at least the high-water mark across
    all in-flight branches. Down-revisions (rare — test deletions or test-
    file removal) require manual edit; that's correct because down-revs
    deserve attention.
    """
    doc_files = [
        ROOT / "CLAUDE.md",
        ROOT / "README.md",
        ROOT / "src" / "divineos" / "seed.json",
        # Audit Tier 3 (2026-05-03 round 8): ARCHITECTURE.md was missing
        # from the count check, which is how "202 commands" stayed stale
        # in the document the README points users at as the canonical
        # reference. Adding it here closes that gap.
        ROOT / "docs" / "ARCHITECTURE.md",
    ]
    changed: list[str] = []
    new_count = _format_count(actual_tests)

    # Pattern matches "3,641+ tests" or "3641+ tests" — used both for
    # finding existing counts and replacing them.
    count_pattern = re.compile(r"([\d,]+)\+?\s+tests")

    for doc_file in doc_files:
        if not doc_file.exists():
            continue
        text = doc_file.read_text(encoding="utf-8", errors="replace")

        # MONOTONIC GUARD: find the highest existing count in this file;
        # only rewrite if our actual count exceeds it. Prevents the cross-
        # branch downgrade-rebase conflict.
        max_existing = 0
        for m in count_pattern.finditer(text):
            try:
                val = int(m.group(1).replace(",", ""))
                if val > max_existing:
                    max_existing = val
            except ValueError:
                continue
        if actual_tests <= max_existing:
            continue  # No-op: existing count is already at or above ours.

        updated = count_pattern.sub(f"{new_count} tests", text)
        if updated != text:
            doc_file.write_text(updated, encoding="utf-8")
            changed.append(doc_file.name)

    return changed


def fix_hook_counts(actual_hooks: int) -> list[str]:
    """Update hook counts in all doc files. MONOTONIC: only raise, never lower.

    Same monotonic-only-raise discipline as fix_test_counts — prevents
    cross-branch rebase conflicts on hook-count line edits (Andrew
    2026-06-12). When a hook is removed (genuine down-rev), manual edit
    is required; that's correct because removal deserves attention.

    Added 2026-05-07 per round-2 audit. The "9 enforcement hooks" claim
    in README drifted by 7 because no checker tracked it. Auto-fix
    closes the loop: when a hook is added, --fix updates the docs to
    match settings.json wiring.
    """
    doc_files = [
        ROOT / "CLAUDE.md",
        ROOT / "README.md",
        ROOT / "docs" / "ARCHITECTURE.md",
    ]
    changed: list[str] = []

    # Monotonic guard patterns (capture group for the number).
    pat_a = re.compile(r"(\d+)\s+(?:Claude Code\s+)?enforcement\s+hooks")
    pat_b = re.compile(r"\((\d+)\s+hooks,")

    for doc_file in doc_files:
        if not doc_file.exists():
            continue
        text = doc_file.read_text(encoding="utf-8", errors="replace")

        # MONOTONIC GUARD: find highest existing count across both patterns;
        # skip the file if actual_hooks <= max_existing.
        max_existing = 0
        for pat in (pat_a, pat_b):
            for m in pat.finditer(text):
                try:
                    val = int(m.group(1))
                    if val > max_existing:
                        max_existing = val
                except ValueError:
                    continue
        if actual_hooks <= max_existing:
            continue  # No-op: existing count is already at or above ours.

        # Pattern A: "9 Claude Code enforcement hooks" / "9 enforcement hooks"
        updated = re.sub(
            r"\d+(\s+(?:Claude Code\s+)?enforcement\s+hooks)",
            lambda m: f"{actual_hooks}{m.group(1)}",
            text,
        )
        # Pattern B: "(9 hooks,"
        updated = re.sub(
            r"\(\d+(\s+hooks,)",
            lambda m: f"({actual_hooks}{m.group(1)}",
            updated,
        )
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


def _files_with_conflict_markers(paths: list[Path]) -> list[str]:
    """Return paths that contain git merge-conflict markers.

    --fix mutates docs by blind regex-append (fix_architecture_tree) and
    by line-rewrite (fix_test_counts / fix_hook_counts). Running it while
    a target file is mid-conflict duplicates entries into ghosts — the
    failure that broke PR #213 (knowledge a9e533c2). We check for the
    angle-bracket markers ('<<<<<<<' / '>>>>>>>') rather than '=======',
    because a run of equals signs is legitimate Markdown (headings,
    rules) while the angle brackets never appear in normal doc content.
    """
    conflicted: list[str] = []
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "<<<<<<<" in text or ">>>>>>>" in text:
            conflicted.append(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p))
    return conflicted


def main() -> int:
    fix_mode = "--fix" in sys.argv

    actual_tests = count_test_functions()
    actual_cmds = count_cli_commands()
    actual_source_files = count_source_files()
    actual_packages = count_packages()

    actual_hooks = count_hooks_wired()
    doc_files = [
        ROOT / "CLAUDE.md",
        ROOT / "README.md",
        ROOT / "src" / "divineos" / "seed.json",
        # Audit Tier 3 (2026-05-03 round 8): ARCHITECTURE.md was missing
        # from the count check, which is how "202 commands" stayed stale
        # in the document the README points users at as the canonical
        # reference. Adding it here closes that gap.
        ROOT / "docs" / "ARCHITECTURE.md",
    ]

    # Refuse --fix while any mutation target is mid-conflict. --fix appends
    # and rewrites blindly; on a conflicted file it duplicates entries into
    # ghosts (PR #213, knowledge a9e533c2). Better to fail loud and make the
    # human resolve the conflict first than to mangle the tree silently.
    if fix_mode:
        conflicted = _files_with_conflict_markers([d for d in doc_files if d.exists()])
        if conflicted:
            print("REFUSING --fix: merge-conflict markers present in:")
            for c in conflicted:
                print(f"  {c}")
            print(
                "Resolve the conflict first. --fix appends/rewrites blindly and "
                "would duplicate entries into ghost files (PR #213)."
            )
            return 1

    actuals = {
        "tests": (actual_tests, TEST_DRIFT_THRESHOLD),
        "commands": (actual_cmds, CMD_DRIFT_THRESHOLD),
        "source_files": (actual_source_files, SOURCE_FILE_DRIFT_THRESHOLD),
        "packages": (actual_packages, PACKAGE_DRIFT_THRESHOLD),
        "hooks": (actual_hooks, 0),
        "council": (count_council_experts(), 0),
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

    # Auto-fix hook counts if requested. Added 2026-05-07 per round-2
    # audit which found README claimed 9 enforcement hooks while
    # settings.json wired 16. Without auto-fix, every hook addition
    # required a manual README edit.
    hook_drift_found = any("hooks" in e.split(chr(10))[0] for e in errors)
    if fix_mode and hook_drift_found:
        changed = fix_hook_counts(actual_hooks)
        if changed:
            print(f"Auto-fixed hook counts in: {', '.join(changed)}")
            errors = [e for e in errors if "hooks" not in e.split(chr(10))[0]]

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

    # Audit Tier 4 (2026-05-16): semantic file-path verification.
    # Catches "doc cites X but X does not exist on disk" — the
    # fabricated-mansion-room / stale-package-list / wrong-file-path
    # class that numeric drift checks cannot catch.
    cited_path_errors = check_cited_paths([
        ROOT / "README.md",
        ROOT / "CLAUDE.md",
        ROOT / "TLDR.md",
    ])
    if cited_path_errors:
        errors.append("Cited paths in docs that do not exist on disk:")
        errors.extend(cited_path_errors)

    if errors:
        print(
            f"Doc drift detected (tests={actual_tests}, commands={actual_cmds}, "
            f"source_files={actual_source_files}, packages={actual_packages}, "
            f"hooks={actual_hooks}):"
        )
        print("\n".join(errors))
        if not fix_mode:
            print("\nUpdate documentation to match reality.")
            print("Or run: python scripts/check_doc_counts.py --fix")
        return 1

    print(
        f"Doc checks OK (tests={actual_tests}, commands={actual_cmds}, "
        f"source_files={actual_source_files}, packages={actual_packages}, "
        f"hooks={actual_hooks}, council={count_council_experts()}, tree=synced)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
