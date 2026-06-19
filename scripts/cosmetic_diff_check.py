"""Cosmetic-diff classifier — determines if a staged change is
mechanical-only (whitespace / import-reorder / unused-import-removal)
or contains substantive content (executable code, comments, docstrings,
tests).

Used by ``divineos audit rebind`` to auto-carry the prior round's
CONFIRMS forward when a post-format-or-lint rebind is purely cosmetic.

## Why this exists

The multi-party-review gate binds each commit to one audit round via a
trailer like ``External-Review: round-XYZ``. When a code formatter
(ruff format, ruff --fix) touches the working tree after a round was
filed, the bound diff-hash no longer matches and the agent must file a
new round and collect fresh CONFIRMS — for changes that are
mechanically equivalent to the audited version.

That mismatch invites shortcut-pressure (it's expensive to redo full
audit ceremony for a comment-rewording or unused-import-removal). This
classifier provides the structural answer: distinguish cosmetic
drift from substantive change at a positive-list level, so cosmetic
drift can auto-carry the prior CONFIRMS forward and substantive change
still requires fresh review.

## Positive list of what counts as cosmetic

Per Aletheia round-9d81a74fa4fc + round-7c79db5aa578 audit:

* Whitespace-only changes (line breaks, indentation, blank lines, tabs)
* Import reordering (same imports, different positions)
* Removal of unused imports caught by linter

Anything outside this list — comment changes, docstring changes,
executable code changes, test assertion changes — is NOT cosmetic and
requires fresh CONFIRMS. The positive-list approach is deliberate:
the safe default is "not cosmetic"; the gate-fix only relaxes the
ceremony for changes that have zero semantic content.

## How it works

For each file changed in the staged diff:

* **Python files**: parse both versions to AST. If ASTs match
  structurally AND the comment/docstring content is identical, the
  diff is cosmetic. AST equivalence catches whitespace, quote-style,
  blank-line, and trailing-comma differences that ruff format
  produces. Comment/docstring comparison ensures we don't classify
  substrate-knowledge edits as cosmetic.

* **Non-Python files**: collapse whitespace and remove blank lines in
  both versions; if results match, cosmetic.

* **Import-only diffs**: detected by tokenize — if the only line-
  differences are import statements AND the effective import set is
  the same (or only-removed imports are unreferenced in the current
  body), cosmetic.

Returns exit 0 if all files in the diff are cosmetic, exit 1
otherwise with per-file diagnostics.

## What this does NOT do

* It does not modify the gate. The gate continues validating rounds
  via their bound diff-hash. This is a pre-flight classifier.
* It does not approve content. The prior round's CONFIRMS approve the
  content. This only determines whether the drift-vs-bound-state is
  cosmetic enough that those CONFIRMS still cover it.
* It does not handle semantic-equivalent refactors (rename,
  function-extraction, etc.) — those are substantive even if behavior
  is preserved.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class FileVerdict:
    """Per-file cosmetic-diff classification."""

    path: str
    is_cosmetic: bool
    reason: str  # explanation of why cosmetic or not


def _git_show(ref: str, path: str) -> bytes:
    """Get file content at a given git ref. Returns empty bytes if the
    file did not exist at that ref."""
    try:
        out = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return b""
    return out.stdout if out.stdout is not None else b""


def _git_staged_content(path: str) -> bytes:
    """Get the staged content of a file (the version going into the
    next commit). Empty bytes if not staged."""
    try:
        out = subprocess.run(
            ["git", "show", f":0:{path}"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return b""
    return out.stdout if out.stdout is not None else b""


def _diff_files(prior_ref: str, current_ref: str | None) -> list[str]:
    """Return the list of file paths that changed between prior_ref and
    current_ref. If current_ref is None, compare against the staged
    index."""
    if current_ref is None:
        cmd = ["git", "diff", "--cached", "--name-only", prior_ref]
    else:
        cmd = ["git", "diff", "--name-only", prior_ref, current_ref]
    try:
        out = subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError:
        return []
    raw = out.stdout if out.stdout is not None else b""
    return [
        line.strip().replace("\\", "/")
        for line in raw.decode("utf-8", errors="replace").splitlines()
        if line.strip()
    ]


def _normalize_whitespace(content: bytes) -> bytes:
    """Collapse runs of whitespace to a single space and remove blank
    lines. Returns bytes for direct comparison."""
    text = content.decode("utf-8", errors="replace")
    # Collapse internal whitespace runs, then strip per-line.
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    # Drop blank lines.
    lines = [line for line in lines if line]
    return "\n".join(lines).encode("utf-8")


def _extract_comments_and_docstrings(tree: ast.AST, source: str) -> list[str]:
    """Extract docstring and comment content from a parsed Python AST.
    Docstrings come from AST nodes; comments require source-line
    scanning since AST drops them."""
    items: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                items.append(doc)
    # Pull # comments from source lines.
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            items.append(stripped)
    return items


def _classify_python_file(prior: bytes, current: bytes) -> FileVerdict:
    """Classify a Python file diff as cosmetic or substantive.

    Strategy: AST equivalence + comment/docstring equivalence. If both
    match, the diff is whitespace/format-only OR import-reorder OR
    unused-import-removal (since AST captures effective imports).
    """
    try:
        prior_text = prior.decode("utf-8", errors="replace")
        current_text = current.decode("utf-8", errors="replace")
        prior_ast = ast.parse(prior_text)
        current_ast = ast.parse(current_text)
    except SyntaxError as e:
        return FileVerdict(
            path="",
            is_cosmetic=False,
            reason=f"Python parse error ({e}); cannot classify as cosmetic.",
        )

    prior_dump = ast.dump(prior_ast, annotate_fields=False)
    current_dump = ast.dump(current_ast, annotate_fields=False)

    if prior_dump != current_dump:
        # AST differs → real semantic change OR import-set change.
        # Check import-only special case: if the only structural
        # difference is removal of unused imports, treat as cosmetic.
        if _is_unused_import_removal_only(prior_ast, current_ast, current_text):
            # Still must verify comments unchanged.
            prior_comments = _extract_comments_and_docstrings(prior_ast, prior_text)
            current_comments = _extract_comments_and_docstrings(current_ast, current_text)
            if sorted(prior_comments) == sorted(current_comments):
                return FileVerdict(
                    path="",
                    is_cosmetic=True,
                    reason="unused-import removal only; comments unchanged",
                )
            return FileVerdict(
                path="",
                is_cosmetic=False,
                reason="unused-import removal AND comment/docstring change",
            )
        return FileVerdict(
            path="",
            is_cosmetic=False,
            reason="AST differs (executable code or import-set change)",
        )

    # AST matches. Now verify comments/docstrings unchanged. AST drops
    # comments so we must scan source.
    prior_comments = _extract_comments_and_docstrings(prior_ast, prior_text)
    current_comments = _extract_comments_and_docstrings(current_ast, current_text)
    if sorted(prior_comments) != sorted(current_comments):
        return FileVerdict(
            path="",
            is_cosmetic=False,
            reason="comment or docstring content changed",
        )

    return FileVerdict(
        path="",
        is_cosmetic=True,
        reason="AST equivalent; comments/docstrings unchanged",
    )


def _imports_from_ast(tree: ast.AST) -> set[tuple[str, str | None]]:
    """Return set of (module, name) tuples for all imports in the tree.
    For ``from X import Y``, returns (X, Y); for ``import X``, returns
    (X, None)."""
    imports: set[tuple[str, str | None]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add((alias.name, None))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.add((module, alias.name))
    return imports


def _is_unused_import_removal_only(
    prior_ast: ast.AST,
    current_ast: ast.AST,
    current_text: str,
) -> bool:
    """Return True iff the only structural difference between prior_ast
    and current_ast is the removal of imports that are not referenced
    in current_text."""
    prior_imports = _imports_from_ast(prior_ast)
    current_imports = _imports_from_ast(current_ast)

    removed = prior_imports - current_imports
    added = current_imports - prior_imports
    if added:
        # An added import is NOT cosmetic.
        return False
    if not removed:
        # No imports removed; difference must be elsewhere.
        return False

    # Verify each removed import is genuinely unused in current_text.
    # "Unused" here means the import name doesn't appear as an
    # identifier in the post-removal source. Conservative check:
    # search for the name as a whole word.
    for _module, name in removed:
        target = name if name is not None else _module.split(".")[-1]
        if not target:
            continue
        # Strip top-of-file import lines so they don't self-reference.
        body_only = _strip_import_lines(current_text)
        if re.search(rf"\b{re.escape(target)}\b", body_only):
            return False

    # Also verify the rest of the AST matches AFTER both have imports
    # filtered out. Easiest check: dump both with all Import/ImportFrom
    # nodes removed.
    def strip_imports(tree: ast.AST) -> ast.AST:
        new = ast.parse(ast.unparse(tree))
        new.body = [stmt for stmt in new.body if not isinstance(stmt, ast.Import | ast.ImportFrom)]
        return new

    return ast.dump(strip_imports(prior_ast), annotate_fields=False) == ast.dump(
        strip_imports(current_ast), annotate_fields=False
    )


def _strip_import_lines(source: str) -> str:
    """Remove lines that look like top-level import statements."""
    out_lines: list[str] = []
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("import ", "from ")):
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


def _classify_other_file(prior: bytes, current: bytes) -> FileVerdict:
    """Non-Python file diff classifier: whitespace-normalized
    comparison only. Anything beyond whitespace is substantive."""
    if _normalize_whitespace(prior) == _normalize_whitespace(current):
        return FileVerdict(
            path="",
            is_cosmetic=True,
            reason="whitespace-only diff",
        )
    return FileVerdict(
        path="",
        is_cosmetic=False,
        reason="non-whitespace content changed",
    )


def classify_diff(prior_ref: str, current_ref: str | None = None) -> list[FileVerdict]:
    """Classify each changed file as cosmetic-only or substantive."""
    paths = _diff_files(prior_ref, current_ref)
    verdicts: list[FileVerdict] = []
    for path in paths:
        prior = _git_show(prior_ref, path)
        current = _git_staged_content(path) if current_ref is None else _git_show(current_ref, path)
        # Handle file-added or file-deleted cases: not cosmetic.
        if not prior or not current:
            verdicts.append(
                FileVerdict(
                    path=path,
                    is_cosmetic=False,
                    reason=("file added" if not prior else "file deleted"),
                )
            )
            continue
        if path.endswith(".py"):
            v = _classify_python_file(prior, current)
        else:
            v = _classify_other_file(prior, current)
        verdicts.append(FileVerdict(path=path, is_cosmetic=v.is_cosmetic, reason=v.reason))
    return verdicts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify a staged-or-committed diff as cosmetic-only "
        "(whitespace/format/unused-import-removal) or substantive."
    )
    parser.add_argument("prior_ref", help="Prior commit/tree ref to compare against")
    parser.add_argument(
        "current_ref",
        nargs="?",
        default=None,
        help="Current commit/tree ref (omit for staged index)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file output; only set exit code",
    )
    args = parser.parse_args(argv)

    verdicts = classify_diff(args.prior_ref, args.current_ref)
    if not verdicts:
        if not args.quiet:
            print("[cosmetic-diff] no files changed")
        return 0

    all_cosmetic = all(v.is_cosmetic for v in verdicts)
    if not args.quiet:
        for v in verdicts:
            tag = "[COSMETIC]" if v.is_cosmetic else "[SUBSTANTIVE]"
            print(f"{tag} {v.path}: {v.reason}")
        print()
        if all_cosmetic:
            print("[cosmetic-diff] all changes are cosmetic-only")
        else:
            print("[cosmetic-diff] BLOCKED: substantive changes present; fresh CONFIRMS required")
    return 0 if all_cosmetic else 1


if __name__ == "__main__":
    sys.exit(main())
