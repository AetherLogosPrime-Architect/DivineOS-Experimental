#!/usr/bin/env python3
"""Resolve first-party imports that sit inside an exception swallow.

THE CLASS, MEASURED BEFORE IT WAS BUILT. Three instances on 2026-08-25,
across two agents, all into bare excepts:

  - ``must_read.arm`` — the function is ``require_read``. Would have thrown
    AttributeError into my own handler and silently degraded a blocking alarm
    to nothing.
  - ``get_correction_text`` — never existed. Sat inside a deliberate
    ``except Exception: pass``, so the corrections-to-wins mirror would have
    reported success while closing nothing, forever.
  - Aria's, in the hook built to reward the discipline: an import from a
    module that does not exist, inside a bare except. It would have exited
    zero on every turn — registered, running, structurally incapable of
    speaking.

Aria named it a class rather than three incidents and offered it to me;
I took it. Her reasoning, and it is why this is cheap: the failure is
statically decidable. A name either exists in the target module or it does
not, and that is arithmetic rather than judgement.

WHY THE SWALLOW IS THE LOAD-BEARING HALF. An unresolvable import outside a
try-block is loud on the first run — the process dies and someone fixes it in
a minute. The same import inside a handler that catches ImportError or
Exception is the worst shape available: the code path is dead, the failure is
invisible, and every test that only asserts "it did not crash" stays green
forever. ``check_silent_swallow.py`` finds the handlers and never looks at
what is inside them; this looks inside.

DELIBERATELY FIRST-PARTY ONLY. ``try: import hypothesis / except ImportError``
is a legitimate optional-dependency pattern and flagging it would bury the
real finding under a hundred correct ones. A third-party package being absent
is a fact about the environment. A ``divineos`` name being absent is a fact
about the code, and it is always a bug.

RESOLVED BY PARSING, NOT IMPORTING. Importing divineos modules to ask whether
a name exists would execute module-level code — ledger connections, loguru
sinks, marker writes — as a side effect of a static check. The target's own
AST answers the question without running anything, which is the same technique
the rest of this session's instruments use and for the same reason.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

_SCAN_DIRS = ("src/divineos", "scripts", ".claude/hooks", "family")

# Handlers that make an unresolvable import invisible. A handler catching a
# narrow non-import error (OSError, ValueError) is not this class.
_SWALLOWING_EXCEPTIONS = frozenset(
    {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}
)


def _module_path(dotted: str) -> Path | None:
    """Where a first-party dotted module lives on disk, or None."""
    parts = dotted.split(".")
    candidate = SRC_ROOT.joinpath(*parts).with_suffix(".py")
    if candidate.exists():
        return candidate
    package_init = SRC_ROOT.joinpath(*parts) / "__init__.py"
    if package_init.exists():
        return package_init
    return None


def _module_level_names(path: Path) -> set[str] | None:
    """Top-level names a module defines, by parsing it. None if unreadable."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return None
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.If):
            # TYPE_CHECKING blocks and version guards define real names.
            for inner in ast.walk(node):
                if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.add(inner.name)
                elif isinstance(inner, ast.Assign):
                    for target in inner.targets:
                        if isinstance(target, ast.Name):
                            names.add(target.id)
    return names


def _handler_swallows(handler: ast.ExceptHandler) -> bool:
    """True when this handler makes an import failure invisible."""
    caught = handler.type
    if caught is None:  # bare except
        return True
    names: list[str] = []
    if isinstance(caught, ast.Name):
        names = [caught.id]
    elif isinstance(caught, ast.Tuple):
        names = [e.id for e in caught.elts if isinstance(e, ast.Name)]
    elif isinstance(caught, ast.Attribute):
        names = [caught.attr]
    if not any(n in _SWALLOWING_EXCEPTIONS for n in names):
        return False
    # A handler that re-raises is loud, not a swallow.
    return not any(isinstance(n, ast.Raise) for n in ast.walk(handler))


def _findings_in(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        # Fail toward flagging. An unreadable file is not a clean one.
        return [f"{path.relative_to(REPO_ROOT)}:1 UNPARSEABLE - {type(exc).__name__}: {exc}"]

    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if not any(_handler_swallows(h) for h in node.handlers):
            continue
        for stmt in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if not isinstance(stmt, ast.ImportFrom):
                continue
            module = stmt.module or ""
            if not module.startswith("divineos"):
                continue  # third-party absence is optionality, not a defect
            target = _module_path(module)
            rel = path.relative_to(REPO_ROOT)
            if target is None:
                out.append(
                    f"{rel}:{stmt.lineno} module does not exist: {module} "
                    f"(inside a swallowing handler — this import can never succeed "
                    f"and will never be heard)"
                )
                continue
            defined = _module_level_names(target)
            if defined is None:
                continue  # cannot read the target; unknown is not a finding
            for alias in stmt.names:
                if alias.name == "*":
                    continue
                # A NAME CAN BE A SUBMODULE, and the first run of this check
                # did not know that. `from divineos.core import gate_marker`
                # is a package importing one of its own files; the name never
                # appears in `__init__.py` and is perfectly resolvable.
                #
                # That mistake produced eleven findings of thirteen, every one
                # of them wrong, and it is the fifth time in one session that
                # an instrument I wrote looked for the shape I pictured rather
                # than the shape in the data. Caught here by checking a sample
                # against disk before reporting, which is the only reason it
                # is not in the commit message as a discovery.
                if _module_path(f"{module}.{alias.name}") is not None:
                    continue
                if alias.name not in defined:
                    out.append(
                        f"{rel}:{stmt.lineno} name not in module: "
                        f"{module}.{alias.name} (inside a swallowing handler — "
                        f"raises ImportError into the handler and the path goes dead silently)"
                    )
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Resolve first-party imports inside swallows.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when anything is found. Default reports and exits 0.",
    )
    args = parser.parse_args(argv[1:])

    findings: list[str] = []
    scanned = 0
    for rel_dir in _SCAN_DIRS:
        root = REPO_ROOT / rel_dir
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            scanned += 1
            findings.extend(_findings_in(path))

    print(f"Scanned {scanned} files across {len(_SCAN_DIRS)} roots.")
    if not findings:
        print("No first-party import inside a swallowing handler fails to resolve.")
        print()
        print(
            "Scope, stated so silence is not read as coverage: this resolves\n"
            "`from divineos... import name` inside handlers that catch ImportError,\n"
            "Exception, or bare. It does NOT check attribute access after import,\n"
            "dynamic imports via importlib, third-party optionality (deliberately),\n"
            "or names defined only at runtime."
        )
        return 0

    print(f"\n{len(findings)} import(s) that cannot resolve, inside a handler that hides it:\n")
    for finding in findings:
        print(f"  {finding}")
    print()
    print(
        "Each of these is a code path that is dead and silent. Fix the name or the\n"
        "module; if the import is genuinely optional, catch ImportError narrowly and\n"
        "say so, or move it out of the handler."
    )
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
