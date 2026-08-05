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
    "post-commit-audit-visibility.sh": "invoked from .git/hooks/post-commit",
    "post-commit-auto-integrate-corrections.sh": "invoked from .git/hooks/post-commit",
    "post-merge-doc-fix.sh": "invoked from .git/hooks/post-merge",
}

_DECLARED_PATTERN = re.compile(
    r"^#.*\b(INTENTIONALLY UNWIRED|SUPERSEDED|NOT WIRED BY DESIGN)\b",
    re.MULTILINE,
)


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

    out: dict[str, list[str]] = {"REGISTERED": [], "DECLARED": [], "DARK": []}
    for path in sorted(hooks_dir.glob("*.sh")):
        name = path.name
        if name in _EXEMPT:
            continue
        if name in registered_blob:
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
    result, error = classify(root / ".claude" / "hooks", root / ".claude" / "settings.json")

    if error:
        print(f"CANNOT CHECK HOOK WIRING — {error}")
        print("This is not 'all hooks wired'. Nothing was checked.")
        return 1

    dark = result["DARK"]
    print(
        f"hooks: {len(result['REGISTERED'])} registered, "
        f"{len(result['DECLARED'])} declared-unwired, {len(dark)} dark"
    )
    if not dark:
        return 0

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
