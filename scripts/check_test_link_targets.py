"""A test's setup must not create a link that points out of its sandbox.

## The incident this exists for

2026-08-25. A fixture in ``tests/test_venv_python_gate.py`` needed a temp git
repo with a working interpreter in it, so it made a directory junction from the
temp repo's ``.venv`` to the REAL one. It worked. Then pytest's
temp-directory cleanup walked the junction and deleted the contents of the real
venv — ``pyvenv.cfg`` and ``Lib/`` gone, the ``divineos`` shim dead.

A junction is not a copy and ``rmtree`` does not know the difference. This
repo's conftest makes the traversal MORE thorough, not less: its ``onerror``
handler chmods read-only files and retries the unlink, which is exactly right
for stale git pack files and exactly wrong when the tree being deleted has a
door into the working checkout.

It survived precommit, the full suite, and every gate here. None of them ask
whether a test's SETUP can reach outside its sandbox — they check what tests
assert, never what they build in order to assert it.

## What is checked

Link-creating calls inside ``tests/``: ``os.symlink``, ``os.link``,
``Path.symlink_to``, ``Path.hardlink_to``, and the Windows ``mklink`` form
spelled as a subprocess argument list. For each, the TARGET expression is read.
A target derived from ``tmp_path`` / ``tmp_path_factory`` / ``mkdtemp`` is
sandboxed and fine. A target mentioning the repo root, the user's home, or an
absolute literal is a door out, and is reported.

## Fail direction

Toward FLAGGING. This is a heuristic on source text, so it will sometimes be
wrong — and a false positive costs a sentence in a comment while a false
negative cost a rebuilt virtualenv and an hour. Legitimate cases carry
``# link-target-outside-tmp: <reason>`` with a substantive reason, the same
contract as ``# fail-soft:``.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"

_LINK_ATTRS = {"symlink", "link", "symlink_to", "hardlink_to"}
_SANDBOXED = re.compile(r"\btmp_path\b|\btmp_path_factory\b|\bmkdtemp\b|\bTemporaryDirectory\b")
_ESCAPES_SANDBOX = re.compile(
    r"\bREPO_ROOT\b|\bPath\.home\(\)|\bPath\(__file__\)|\bos\.getcwd\(\)|"
    r"\bParent\b|['\"][A-Za-z]:[\\/]|['\"]/(usr|home|etc|opt)/"
)
_EXEMPT = re.compile(r"#\s*link-target-outside-tmp\s*:\s*(.{30,})")


def _lines_with_exemption(text: str) -> set[int]:
    return {i for i, line in enumerate(text.splitlines(), 1) if _EXEMPT.search(line)}


def _link_calls(tree: ast.AST) -> list[ast.Call]:
    out: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _LINK_ATTRS:
            out.append(node)
        elif isinstance(func, ast.Name) and func.id in _LINK_ATTRS:
            out.append(node)
    return out


def _mentions_mklink(node: ast.Call, text: str) -> bool:
    try:
        segment = ast.get_source_segment(text, node) or ""
    except (ValueError, TypeError):
        return False
    return "mklink" in segment


def _target_segment(call: ast.Call, text: str) -> str:
    """The source of the TARGET argument alone, not the whole call.

    THE HOLE THIS CLOSES, and Aletheia flagged the direction I had not
    verified. The first version searched the whole call for sandbox evidence,
    so ``tmp_path`` appearing ANYWHERE made it pass — including when it was the
    LINK LOCATION rather than the target. Measured 2026-08-25:

        os.symlink(target_from_somewhere, tmp_path / "alias")

    passed silently. The target is a name computed elsewhere and could point at
    anything; the only sandbox evidence in that line describes where the link
    is placed, which says nothing about where it points.

    That is the failure direction I wrote this whole check to avoid, sitting in
    the check. The real fixture that ate the venv was caught only because its
    target ALSO carried a repo-root marker — remove that coincidence and my
    check would have waved it through.

    Falls back to the whole call for shapes it cannot decompose (the mklink
    subprocess form), where whole-call matching is the honest best available.
    """
    func = call.func
    args = call.args
    if not args:
        return ast.get_source_segment(text, call) or ""

    # os.symlink(src, dst) / os.link(src, dst)   -> src is the target
    # p.symlink_to(target) / p.hardlink_to(target) -> the sole arg is the target
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
    if name in _LINK_ATTRS:
        return ast.get_source_segment(text, args[0]) or ""

    return ast.get_source_segment(text, call) or ""


def _subprocess_calls(tree: ast.AST) -> list[ast.Call]:
    out: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in {"run", "Popen", "check_call"}:
                out.append(node)
    return out


def findings() -> list[str]:
    out: list[str] = []
    if not TESTS.exists():
        return out

    for path in sorted(TESTS.rglob("*.py")):
        if "_archive" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            continue

        exempt = _lines_with_exemption(text)
        candidates = list(_link_calls(tree))
        candidates += [c for c in _subprocess_calls(tree) if _mentions_mklink(c, text)]

        for call in candidates:
            line = call.lineno
            # The exemption may sit on the call line or in the comment block
            # just above it. The window is four lines rather than one because a
            # 30-character-minimum reason usually wraps, and its FIRST line is
            # the one carrying the marker — a one-line lookback found the last
            # line of the comment and reported the call anyway. Caught by this
            # check's own test, which is the only reason the window is right.
            if line in exempt or any((line - n) in exempt for n in range(1, 5)):
                continue
            segment = _target_segment(call, text)
            if _SANDBOXED.search(segment) and not _ESCAPES_SANDBOX.search(segment):
                continue
            if not _ESCAPES_SANDBOX.search(segment):
                # No evidence either way. Report it: an unreadable target is
                # not a safe target, and this check fails toward flagging.
                rel = path.relative_to(ROOT).as_posix()
                out.append(f"{rel}:{line}: link target could not be shown to stay inside tmp")
                continue
            rel = path.relative_to(ROOT).as_posix()
            out.append(f"{rel}:{line}: link target reaches outside the test sandbox")
    return out


def main() -> int:
    hits = findings()
    if not hits:
        print("Test link-target check OK (no test creates a link out of its sandbox)")
        return 0

    print("Tests creating links whose target may sit outside the temp sandbox:")
    print()
    for hit in hits:
        print(f"  {hit}")
    print()
    print("A junction or symlink is not a copy. pytest's temp cleanup walks it and")
    print("deletes what it finds on the other side — this repo lost a virtualenv that")
    print("way on 2026-08-25, from a fixture that had passed every other gate.")
    print()
    print("Build a real throwaway instead (`python -m venv --without-pip` takes about a")
    print("second), or, if the link genuinely must point outside tmp, say why:")
    print()
    print("    # link-target-outside-tmp: <reason, 30+ chars>")
    return 1


if __name__ == "__main__":
    sys.exit(main())
