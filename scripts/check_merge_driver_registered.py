#!/usr/bin/env python3
"""Refuse the quiet half of a merge driver: declared in the repo, absent locally.

A merge driver lives in two places and only one of them travels. The
DECLARATION rides in .gitattributes, so every clone gets it. The
REGISTRATION -- the command line the driver actually runs -- lives in local
git config, which travels nowhere. A fresh clone, a new machine, or a
worktree somebody set up in a hurry therefore has the declaration and not
the registration.

What git does in that state is the problem: it falls back to the ordinary
textual merge, silently. No warning, no marker, no exit code. So two people
run the same merge on the same two branches and get different trees, and
the one whose driver is missing has no way to find out except by noticing
the result is wrong much later.

That is the shape this house keeps finding: a guard that protects whoever
remembered to install it, and whose absence is indistinguishable from its
presence. Aria 2026-09-18, taking this half while Aether writes the driver.
His condition on the driver is that it must fail LOUDLY when the generator
cannot run rather than emit an empty result; this check is that same
condition one level out -- the driver must fail loudly when it is not there
at all.

PRIOR ART, and it is the reason this check is worth having rather than a
second opinion about it. scripts/union_resolve.py already resolves the
regenerated-count conflicts that hit every rebase here, and it is run BY
HAND. So the house has already met the derive-versus-reconcile question and
answered it with a manual script. A hand-run tool has no registration to
miss; it is simply not run, which somebody notices. A driver is the
opposite -- it is silent when absent -- and that difference is exactly what
this file exists to close before the driver lands.

It is deliberately inert until a declaration exists. No declaration means
nothing to enforce, and it says so rather than printing a clean pass that
could equally mean "checked and fine" or "never looked". Once a declaration
lands, this refuses on every checkout that has not registered, including
the checkout of whoever wrote the driver -- Aether asked for that
explicitly: if he is the one who forgets, he would rather be refused than
trusted.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# `merge=<name>` in a .gitattributes line. The name is what must be
# registered in config as merge.<name>.driver.
_MERGE_ATTR = re.compile(r"(?:^|\s)merge=([A-Za-z0-9._-]+)")

# Built into git. Declaring these registers nothing, so there is nothing to
# miss and flagging them would train the reader to ignore this check.
_BUILTIN = frozenset({"text", "binary", "union"})


def _repo_root() -> Path | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None
    path = out.stdout.strip()
    return Path(path) if path else None


def _declared_drivers(root: Path) -> tuple[dict[str, list[str]], list[str]]:
    """(driver name -> declaring files, unreadable attribute files).

    Every .gitattributes counts, not only the one at root: a declaration in
    a subdirectory binds just as hard and hides better.
    """
    found: dict[str, list[str]] = {}
    unreadable: list[str] = []
    for attrs in sorted(root.rglob(".gitattributes")):
        if ".git" in attrs.parts:
            continue
        rel = str(attrs.relative_to(root)).replace("\\", "/")
        try:
            text = attrs.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # Unreadable is not absent, and this file exists because those
            # two must never render the same. Reported, never skipped.
            unreadable.append(rel)
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for name in _MERGE_ATTR.findall(stripped):
                if name in _BUILTIN:
                    continue
                found.setdefault(name, [])
                if rel not in found[name]:
                    found[name].append(rel)
    return found, unreadable


def _registered(name: str) -> tuple[bool, str]:
    """(is_registered, detail). An unaskable config is NOT a pass."""
    try:
        out = subprocess.run(
            ["git", "config", "--get", f"merge.{name}.driver"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return False, f"could not ask git config ({exc.__class__.__name__})"
    if out.returncode == 0 and out.stdout.strip():
        return True, out.stdout.strip()
    return False, f"no merge.{name}.driver in this checkout's config"


def main() -> int:
    root = _repo_root()
    if root is None:
        print("[merge-driver] CANNOT CHECK: not a git repository, or git unavailable.")
        print("  Refusing to report a pass. A check that could not run is not a check")
        print("  that passed, and collapsing those two is the fault this file exists")
        print("  to prevent.")
        return 1

    declared, unreadable = _declared_drivers(root)

    if unreadable:
        print("[merge-driver] CANNOT CHECK: unreadable attribute file(s):")
        for rel in unreadable:
            print(f"      {rel}")
        print("  A declaration could be hiding in there. Unknown is its own answer.")
        return 1

    if not declared:
        print("[merge-driver] no custom merge driver is declared in any .gitattributes.")
        print("  Nothing to register, so nothing to enforce. This line means LOOKED AND")
        print("  FOUND NONE -- not 'skipped'. The two must never render the same.")
        return 0

    missing: list[tuple[str, list[str], str]] = []
    for name, where in sorted(declared.items()):
        ok, detail = _registered(name)
        if ok:
            print(f"[merge-driver] {name}: registered ({detail})")
        else:
            missing.append((name, where, detail))

    if not missing:
        return 0

    print()
    print("MERGE DRIVER DECLARED BUT NOT REGISTERED IN THIS CHECKOUT.")
    print()
    for name, where, detail in missing:
        print(f"  {name}")
        print(f"      declared in   : {', '.join(where)}")
        print(f"      this checkout : {detail}")
    print()
    print("WHY THIS REFUSES RATHER THAN WARNS. Git does not complain about this. It")
    print("falls back to the ordinary textual merge in silence, so the same merge of")
    print("the same two branches produces one tree here and a different tree on a")
    print("checkout that registered the driver. Nothing announces the divergence and")
    print("it gets found much later, by noticing the result is wrong.")
    print()
    print("A guard present only where somebody remembered to install it is a guard")
    print("whose absence is invisible. This refuses the driver author's own checkout")
    print("as readily as anyone else's, by request.")
    print()
    print("Register it, then re-run:")
    for name, _where, _detail in missing:
        print(f'    git config merge.{name}.driver "<the command the driver runs>"')
    print()
    print("The driver's own contract still holds on top of this: when it cannot do")
    print("its job it must fail loudly rather than emit an empty result.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
