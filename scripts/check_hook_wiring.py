"""Every hook is registered, or says out loud why it is not.

Andrew 2026-08-05: *"keep scouting for broken doors and lets find thier root
causes."*

## The scout that produced this

Nine hooks in ``.claude/hooks/`` are absent from ``settings.json``. Triaged:

* ``_lib.sh`` — a library, never registered by design.
* three ``post-commit-*`` / ``post-merge-*`` — invoked from git hooks, fine.
* ``post-push-audit-visibility.sh`` — header says **INTENTIONALLY UNWIRED**
  with the reason: git has no client-side post-push hook.
* ``post-push-verify-landing.sh`` — header says **SUPERSEDED**, names the file
  doing the job instead.
* **``m3-discipline-hierarchy.sh``** — "load-bearing mechanism of the
  nine-surface anti-demotion design". Dark.
* **``load-aletheia-harvest-of-andrew.sh``** — Aletheia asked for exactly this
  wiring in her own words: *"Wire it to load at compose-start."* Dark.
* **``aletheia-boot-gate-preflight.sh``** — refuses an Aletheia invocation when
  her boot files fail their canary check. Its own header calls silent
  substitution *"the single most dangerous failure mode in her architecture."*
  Dark. In BOTH trees. Never wired by either of us.

## The root cause, and why it is this file rather than three fixes

Writing a hook and registering a hook are **two places**, and nothing joins
them. Same shape as every other defect this substrate keeps producing: the
producer exists, the consumer is absent, and the gap is silent because a hook
that is never called cannot complain about not being called.

The remedy was already invented — organically, by whoever wrote those two
honest headers. ``INTENTIONALLY UNWIRED`` and ``SUPERSEDED`` are **the third
word**: not registered, not forgotten, but *deliberately not wired, and here
is why*. The convention existed and nothing enforced it, so it protected the
two hooks whose authors happened to use it and none of the others.

This check makes the convention structural. Three states, never two:

    REGISTERED   — named in settings.json
    DECLARED     — carries INTENTIONALLY UNWIRED / SUPERSEDED + a reason
    DARK         — neither, and that is a finding

A dark hook is not necessarily a bug. It is necessarily **unexamined**, and
this refuses to let it stay that way silently.

## The other direction, added 2026-08-25

Everything above walks from the DISK to the REGISTRY: for each file, is it
wired? Nothing walked the other way — for each registration, does the file
exist? — and that asymmetry had a live cost in this checkout.

``require-monitors-armed.sh`` was deleted on 2026-08-23 when the delivery
cluster was retired, because it reported the letter monitor armed
unconditionally: a self-match bug meant its own scan found its own command
line and called that an armed monitor. Deliberate removal of a gate that
lied. The retirement commit removed a phantom registration for a different
hook in the same pass and closed with *"Every registered hook now resolves
to a file that exists."*

Then merge #438 landed a branch that predated the retirement, and its copy
of ``settings.json`` brought the registration back **without** the file.
Since then every Bash tool call in this tree has run
``bash .claude/hooks/require-monitors-armed.sh`` and collected exit 127.

Three things worth keeping about that:

* **A resurrection is not an authorship.** Nobody decided to register a
  deleted hook. A merge did it, silently, from a branch that was simply
  older than the deletion — which is why remembering is not a defence and
  a check is.
* **The claim was true when written and nothing kept it true.** The
  retirement verified the property by hand and had no way to leave the
  verification running.
* **The failure is quiet by construction.** A registration pointing at
  nothing produces no gate, no error I read, and no complaint — the exact
  could-not-run-looks-like-nothing-to-say class this substrate keeps
  finding in new costumes.

So the check now has a fourth state, and it walks both directions:

    REGISTERED   — named in settings.json, file present
    DECLARED     — carries INTENTIONALLY UNWIRED / SUPERSEDED + a reason
    DARK         — on disk, neither registered nor declared
    PHANTOM      — registered, no file on disk
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Hooks invoked from git hooks or sourced as libraries rather than registered
# in settings.json. Each needs a reason, because an unexplained exemption is
# the same silent-skip this check exists to prevent.
_EXEMPT: dict[str, str] = {
    "_lib.sh": "shared library, sourced by other hooks rather than invoked",
    "_bail.sh": (
        "shared library, sourced by five command-triggered hooks so they can "
        "bail before paying for _lib.sh and a Python start on an irrelevant "
        "tool call; same case as _lib.sh, and it was reported dark only "
        "because the exemption list named its sibling and not it"
    ),
    "post-commit-audit-visibility.sh": "invoked from .git/hooks/post-commit",
    "post-commit-auto-integrate-corrections.sh": "invoked from .git/hooks/post-commit",
    "post-merge-doc-fix.sh": "invoked from .git/hooks/post-merge",
    "branch-scope-guard.sh": (
        "invoked from .git/hooks/commit-msg, installed by setup/setup-hooks.sh; "
        "it fires on every commit and has caught four scope-mismatches on "
        "2026-08-21 alone"
    ),
}

_DECLARED_PATTERN = re.compile(
    r"^#.*\b(INTENTIONALLY UNWIRED|SUPERSEDED|NOT WIRED BY DESIGN)\b",
    re.MULTILINE,
)

# Any reference to a file under .claude/hooks/ inside a registered command.
# Deliberately matches .py as well as .sh: the disk-to-registry walk globs
# only *.sh, but a registration can name either, and a phantom .py hook fails
# exactly as silently as a phantom .sh one.
_HOOK_REFERENCE = re.compile(r"\.claude[/\\]hooks[/\\]([\w.-]+\.(?:sh|py))")


def phantoms(hooks_dir: Path, settings: Path) -> tuple[list[str], str | None]:
    """Hook files named in settings.json that do not exist on disk.

    Returns ``(names, error)``. As everywhere else here, an unreadable
    settings.json yields an error rather than an empty list — "could not look"
    must never render as "looked, found nothing".

    Walks the PARSED structure rather than the raw text, and that is not a
    style preference. The first version scanned the blob, which meant a command
    written with Windows separators appears in the file with the backslash
    JSON-escaped, and a pattern looking for one backslash saw nothing. A
    phantom-registration check that goes silent on a whole class of
    registration is the very defect it was written to find, one level up. Its
    own test caught it, after it had already run green against the live tree.
    """
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [], f"cannot read {settings}: {exc}"

    named: set[str] = set()
    events = data.get("hooks", {}) if isinstance(data, dict) else {}
    for groups in events.values():
        for group in groups if isinstance(groups, list) else []:
            for hook in (group or {}).get("hooks", []):
                command = (hook or {}).get("command", "")
                if isinstance(command, str):
                    named.update(m.group(1) for m in _HOOK_REFERENCE.finditer(command))

    return sorted(name for name in named if not (hooks_dir / name).exists()), None


# A hook can be wired without appearing in settings.json. `session-init-once.sh`
# IS registered, and runs a roster of children itself — the collapse that fixed
# the Windows SessionStart deadlock (2026-08-03). Those children are wired; the
# wire simply has one more segment in it.
#
# This check did not know that, so on 2026-08-13 it reported thirteen live hooks
# as dark the moment that branch merged. Two answers were available and only one
# is honest: stamp thirteen files with INTENTIONALLY UNWIRED, which would be a
# lie written thirteen times to quiet a check — or teach the check what a wire
# looks like now. A wiring check that cannot follow an indirection reports the
# indirection as an absence.
#
# The buried cost of getting this wrong is the reason it matters: if a hook the
# launcher runs is called dark, the obvious fix is to delete it or declare it
# unwired, and either one turns a working hook off while the check goes green.
_LAUNCHERS = ("session-init-once.sh",)


def _launcher_roster(hooks_dir: Path) -> set[str]:
    """Hook names a registered launcher invokes itself."""
    names: set[str] = set()
    for launcher in _LAUNCHERS:
        path = hooks_dir / launcher
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        names.update(re.findall(r"^\s*([\w.-]+\.sh)\s*$", body, re.MULTILINE))
    names.discard("")
    return names


def classify(hooks_dir: Path, settings: Path) -> tuple[dict[str, list[str]], str | None]:
    """Return ``({state: [names]}, error)``.

    ``error`` is set — and the dict left empty — when settings.json cannot be
    read. A wiring check that cannot see the registrations must not report
    every hook as dark; "could not look" is its own answer.
    """
    try:
        registered_blob = settings.read_text(encoding="utf-8")
        json.loads(registered_blob)  # parse-check; matching is textual
    except (OSError, ValueError) as exc:
        return {}, f"cannot read {settings}: {exc}"

    # Only launchers that are themselves registered can confer wiring. An
    # unregistered launcher's roster is a list of hooks that all go dark
    # together, which is precisely the failure worth catching.
    via_launcher = (
        _launcher_roster(hooks_dir)
        if any(name in registered_blob for name in _LAUNCHERS)
        else set()
    )

    out: dict[str, list[str]] = {"REGISTERED": [], "DECLARED": [], "DARK": []}
    for path in sorted(hooks_dir.glob("*.sh")):
        name = path.name
        if name in _EXEMPT:
            continue
        if name in registered_blob or name in via_launcher:
            out["REGISTERED"].append(name)
            continue
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:2000]
        except OSError:
            # Unreadable file is DARK, not silently skipped.
            out["DARK"].append(name)
            continue
        if _DECLARED_PATTERN.search(head):
            out["DECLARED"].append(name)
        else:
            out["DARK"].append(name)
    return out, None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    hooks_dir = root / ".claude" / "hooks"
    settings = root / ".claude" / "settings.json"
    result, error = classify(hooks_dir, settings)

    if error:
        print(f"CANNOT CHECK HOOK WIRING — {error}")
        print("This is not 'all hooks wired'. Nothing was checked.")
        return 1

    ghosts, ghost_error = phantoms(hooks_dir, settings)
    if ghost_error:
        print(f"CANNOT CHECK FOR PHANTOM REGISTRATIONS — {ghost_error}")
        print("This is not 'no phantoms'. That direction was not checked.")
        return 1

    dark = result["DARK"]
    print(
        f"hooks: {len(result['REGISTERED'])} registered, "
        f"{len(result['DECLARED'])} declared-unwired, {len(dark)} dark, "
        f"{len(ghosts)} phantom"
    )

    if ghosts:
        print("")
        print("PHANTOM REGISTRATIONS — named in settings.json, no file on disk:")
        for name in ghosts:
            print(f"  - {name}")
        print("")
        print("Every tool call matching these runs `bash` against a path that does not")
        print("exist and collects exit 127. No gate runs, and nothing says so — which is")
        print("indistinguishable from a gate that looked and approved.")
        print("")
        print("Usually a merge from a branch older than the deletion. Remove the")
        print("registration, or restore the file if the deletion was the mistake.")

    if not dark and not ghosts:
        return 0
    if not dark:
        return 1

    print("")
    print("DARK HOOKS — written, not registered, and not saying why:")
    for name in dark:
        print(f"  - {name}")
    print("")
    print("A hook that is never called cannot complain about not being called.")
    print("Either register it in .claude/settings.json, or put a header line on it:")
    print("")
    print("    # INTENTIONALLY UNWIRED (<date>): <why, concretely>")
    print("")
    print("The second option is a real answer, not a dodge — two hooks already")
    print("use it correctly. What is refused is leaving the question unasked.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
