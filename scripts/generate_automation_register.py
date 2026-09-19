"""Generate the automation register — what runs by itself, and whether it
actually runs.

Andrew 2026-07-31: "this house has lots of hidden rooms.. so it needs a
good inventorying as well so you know everything you have... sorted..
cataloged easy to maintain and search with drilldowns if needed as well.
basically a loadout, and a separate list to include everything that is
automated. so it doesnt crowd you out"

WHY SEPARATE FROM LOADOUT.md. The loadout describes the house — rooms,
subsystems, where things live. Automations number 97+ and would drown
every other section if merged in. Two documents, two jobs.

WHY GENERATED, NOT HAND-WRITTEN. LOADOUT.md was last touched 2026-07-17
and had drifted by the time it mattered. A hand-maintained inventory of a
moving system is a promise to go stale. This one is rebuilt from reality
on demand, so it cannot quietly diverge.

WHY THE WIRED COLUMN IS THE WHOLE POINT. On 2026-07-31 a survey found
four hooks that were installed, executable, and described themselves as
running automatically — and were invoked by nothing. Two more had been
orphaned by a stale post-commit dispatcher. Twenty-one operator
corrections had accumulated because one of them silently did nothing.

A register that merely LISTED automations would have shown all of them as
present and implied they worked — the same failure, repeated in
documentation form. So every entry carries whether it is actually
reachable, and the switched-off ones are surfaced at the TOP rather than
buried in a table. An inventory that cannot tell you what is dark is
decoration.

Related substrate: knowledge f9b635d5 (thought-arm amputation) names the
adjacent failure — tools I own but stop reaching for. Same root, one
layer up: this register is for tools that stopped reaching for THEMSELVES.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = ROOT / ".claude" / "hooks"
SETTINGS = ROOT / ".claude" / "settings.json"
GIT_HOOKS = ROOT / ".git" / "hooks"
OUTPUT = ROOT / "docs" / "AUTOMATION_REGISTER.md"


def _first_purpose_line(path: Path) -> str:
    """Pull a one-line purpose from a hook's header comment.

    Takes the first comment line after the shebang that reads like a
    description rather than boilerplate. Falls back to a visible marker so
    a missing description shows up rather than rendering as blank.
    """
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "(unreadable)"
    for raw in lines[1:14]:
        line = raw.strip()
        if not line.startswith("#"):
            continue
        text = line.lstrip("#").strip()
        if not text or text.startswith("shellcheck") or text.startswith("!"):
            continue
        # Strip a leading "<Event> hook —" prefix; the event is its own column.
        text = re.sub(r"^\w+\s+hook\s*[—–-]\s*", "", text, flags=re.IGNORECASE).strip()
        text = text.replace("|", "\\|")
        if len(text) > 4:
            return text[:150]
    return "(no description in header)"


def _registered_commands() -> dict[str, list[str]]:
    """Map hook-filename -> the events it is registered under in settings."""
    out: dict[str, list[str]] = {}
    try:
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return out
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                m = re.search(r"([\w.-]+\.sh)", hook.get("command", ""))
                if m:
                    out.setdefault(m.group(1), []).append(event)
    return out


def _caller_text() -> str:
    """Text of everything that could invoke a hook outside settings.json.

    Installed git hooks, repo scripts, setup scripts, and other hooks.
    The post-commit dispatcher is the notable one — it globs rather than
    naming each hook, which is why glob prefixes are handled separately.
    """
    parts: list[str] = []
    dirs = [GIT_HOOKS, ROOT / "scripts", ROOT / "setup", HOOKS_DIR]
    for d in dirs:
        if not d.exists():
            continue
        for p in d.iterdir():
            if p.is_file():
                try:
                    parts.append(p.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    continue
    return "\n".join(parts)


def _mainline_ref() -> str | None:
    """The ref every branch must agree to measure against, or None.

    Read from the remote's published head rather than hardcoded, for the same
    reason the merge driver reads it there: the default branch is a fact the
    remote already states, and a second configuration key is a second thing to
    set correctly in two checkouts.

    None when the remote head is unset -- ordinary in a fresh clone. The caller
    then falls back to the old branch-local behaviour and the register becomes
    branch-dependent again, which is the bug rather than a new one, and the
    header says so out loud rather than letting a silently-different file look
    identical.
    """
    try:
        out = subprocess.run(
            ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )
    except OSError:
        return None
    ref = (out.stdout or "").strip()
    return ref or None


def _git_last_touched(rel: str, mainline: str | None) -> str:
    """Last commit date for a path, resolved against the MAIN LINE.

    WHY NOT THE CURRENT BRANCH, which is what this did until 2026-09-19 and
    which made the whole register collide with itself forever.

    Asking `git log` without a ref resolves against HEAD. So two branches
    carrying byte-identical hooks but forked on different days generated
    different registers and then refused to merge -- seven of the ten stuck
    branches collided here, and one collided on nothing else at all. The file
    was history-dependent by construction and no merge driver could fix that,
    because there was nothing to reconcile: both sides were correct about
    different histories.

    Aria found the mechanism and measured the damage: main's own checked-in
    register does not reproduce from a clean worktree at main -- seventy lines
    differ. I had claimed the opposite and cited a regenerate-and-diff as proof,
    having run it in the tree that produced the file, on the same branch. A
    photograph checked against itself.

    Pinning to the main line makes every branch produce the same bytes, and it
    keeps the meaning rather than discarding it: WHEN DID THIS LAST CHANGE ON
    THE MAIN LINE is the question the staleness drilldown was always asking.

    A PATH THAT EXISTS ONLY ON A BRANCH has no main-line commit, and gets the
    same marker from every branch -- which is the property that matters. It
    reads as not-yet-on-main rather than as undated, and it stops being that
    the moment it merges.
    """
    args = ["git", "log", "-1", "--format=%as"]
    if mainline:
        args.append(mainline)
    args += ["--", rel]
    try:
        out = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )
    except OSError:
        return "—"
    date = (out.stdout or "").strip()
    if date:
        return date
    # Empty with a mainline ref means the path is not on the main line yet.
    # Empty without one means git could not answer at all; both are "—" today,
    # and they are different facts, so they get different markers.
    return "not on main" if mainline else "—"


def collect() -> list[dict]:
    """Scan every automation and resolve whether anything actually calls it."""
    hooks = sorted(HOOKS_DIR.glob("*.sh"), key=lambda p: p.name)
    registered = _registered_commands()
    callers = _caller_text()
    glob_prefixes = set(re.findall(r"([a-z0-9-]+)-\*\.sh", callers))
    # Resolved ONCE per run rather than per path. Asking per row would let the
    # answer change mid-file if anything moved underneath, which is the same
    # class of inconsistency this whole change exists to remove.
    mainline = _mainline_ref()

    rows = []
    for h in hooks:
        name = h.name
        events = registered.get(name, [])
        if events:
            wired, via = True, ", ".join(sorted(set(events)))
        elif any(name.startswith(g + "-") for g in glob_prefixes):
            wired, via = True, "glob-dispatch (post-commit)"
        elif name in callers:
            wired, via = True, "called by another script"
        else:
            wired, via = False, "NOTHING CALLS THIS"
        rows.append(
            {
                "name": name,
                "wired": wired,
                "via": via,
                "purpose": _first_purpose_line(h),
                "touched": _git_last_touched(f".claude/hooks/{name}", mainline),
            }
        )

    return rows


def build(rows: list[dict]) -> str:
    """Render the register from already-collected rows."""
    orphans = [r for r in rows if not r["wired"]]
    by_event: dict[str, list[dict]] = {}
    for r in rows:
        if r["wired"]:
            by_event.setdefault(r["via"], []).append(r)

    L: list[str] = []
    L.append("# Automation register")
    L.append("")
    L.append(
        "**Generated** by `scripts/generate_automation_register.py`. Do not hand-edit — regenerate."
    )
    L.append("")
    L.append(
        "Companion to [LOADOUT.md](../LOADOUT.md). The loadout describes the "
        "house; this lists what runs by itself. Kept separate so that 90+ "
        "automations do not crowd out every other room."
    )
    L.append("")
    L.append(
        f"**{len(rows)} automations — {len(rows) - len(orphans)} wired, "
        f"{len(orphans)} switched off.**"
    )
    L.append("")
    L.append("---")
    L.append("")

    L.append("## Switched off")
    L.append("")
    L.append(
        "Present, executable, invoked by nothing. This section is first on "
        "purpose. On 2026-07-31 four hooks were found in exactly this state, "
        "one of which had silently let 21 operator corrections accumulate. A "
        "register that only listed automations would have shown them as "
        "present and implied they worked."
    )
    L.append("")
    if orphans:
        L.append("| automation | last touched | purpose |")
        L.append("|---|---|---|")
        for r in orphans:
            L.append(f"| `{r['name']}` | {r['touched']} | {r['purpose']} |")
        L.append("")
        L.append(
            "Being listed here is not automatically a defect — a retired hook "
            "that says so in its own header is honest. The question for each "
            "is whether it CLAIMS to run automatically. If it does and "
            "nothing calls it, that is the bug."
        )
    else:
        L.append("None. Every automation present is reachable.")
    L.append("")
    L.append("---")
    L.append("")

    L.append("## Wired, by trigger")
    L.append("")
    L.append(
        "Sorted by when each fires. Drilldown: open any row's file for its "
        "full header, rationale, and falsifier."
    )
    L.append("")
    for event in sorted(by_event):
        entries = sorted(by_event[event], key=lambda r: r["name"])
        L.append(f"### {event}  ({len(entries)})")
        L.append("")
        L.append("| automation | last touched | purpose |")
        L.append("|---|---|---|")
        for r in entries:
            L.append(f"| `{r['name']}` | {r['touched']} | {r['purpose']} |")
        L.append("")

    L.append("---")
    L.append("")
    L.append("## Regenerating")
    L.append("")
    L.append("```bash")
    L.append("python scripts/generate_automation_register.py")
    L.append("```")
    L.append("")
    L.append(
        "`--check` exits non-zero when the file has drifted, for wiring into "
        "a pre-commit or CI step. It compares this tree against its own "
        "committed copy, so it cannot see branch-dependence."
    )
    L.append("")
    L.append(
        "`--check-reproduces` takes the measurement `--check` structurally "
        "cannot: it builds a clean worktree at the main line, runs THAT "
        "tree's own copy of this generator, and diffs the result against the "
        "copy committed there. Two sides from two sources. It exits 0 when "
        "the register reproduces, 1 when it does not, and **2 when it could "
        "not look at all** — a missing main-line ref, a worktree that would "
        "not build. Could-not-look is never reported as either answer."
    )
    L.append("")
    L.append(
        "Run after adding, removing, or rewiring any automation. The wired "
        "column is computed from settings.json, the installed git hooks, and "
        "glob-dispatch prefixes — it reflects what is actually reachable, "
        "not what is supposed to be."
    )
    L.append("")
    return "\n".join(L)


# Three outcomes, not two, and the third is the reason this exists.
#
# A check with a pass and a fail has nowhere to put "I could not look," so
# could-not-look gets filed as one of the two -- and in every instance we have
# found, it gets filed as the reassuring one. Aether's --check was quoted as
# proof of reproducibility it could not establish; my own probe for this
# feature happily reported on the contents of a directory that had failed to
# be created. Same shape twice in one day.
REPRODUCES = 0
DRIFTED = 1
COULD_NOT_CHECK = 2


def _second_tree_path() -> Path:
    """Where the clean worktree goes, and why it is deliberately SHORT.

    The first run of this check put the second tree under the session
    scratchpad, roughly 120 characters deep. On Windows, `git worktree add`
    got 70% of the way through the checkout, failed on the first letter
    filename that crossed the limit, and left a half-built tree behind --
    while the probe standing next to it cheerfully answered questions about
    the directory that did not exist. The length is not incidental; every
    other working copy in this house already sits at a short path and nobody
    had written down why.

    Overridable, because a short writable root is a property of the machine
    rather than of this repository.
    """
    override = os.environ.get("DIVINEOS_REPRO_WORKTREE")
    if override:
        return Path(override)
    anchor = Path(ROOT.anchor) if ROOT.anchor else Path("/tmp")
    return anchor / "divineos-repro-wt"


def _check_reproduces() -> int:
    """Regenerate in a clean tree at the main line and diff against it.

    THE POINT IS THAT THE TWO SIDES COME FROM DIFFERENT SOURCES. `--check`
    regenerates in the tree that produced the committed file, on the branch
    that produced it, so any field resolved from branch history agrees with
    itself by construction -- a photograph checked against itself. This runs
    the OTHER tree's own copy of the generator, against the copy committed in
    that tree, and nothing either side knows comes from here.

    That independence is why it found something: main's committed register
    did not rebuild from main, and all seventy differing lines were the one
    branch-dependent column. A same-tree check reported clean throughout.
    """
    # --against <ref> checks a branch BEFORE it merges, which is when the
    # answer is still cheap to act on. It also makes the reproduces-clean
    # verdict demonstrable: with the ref pinned to the main line and the main
    # line currently drifted, this check could never have returned that answer
    # at all, and an instrument that has never produced one of its outcomes is
    # untested in that direction.
    if "--against" in sys.argv:
        at = sys.argv.index("--against") + 1
        if at >= len(sys.argv):
            print("could not check: --against needs a ref")
            return COULD_NOT_CHECK
        mainline = sys.argv[at]
    else:
        mainline = _mainline_ref()
    if mainline is None:
        # The fixed point is read from the remote's published head, which a
        # fresh CI checkout frequently does not set. Without it the generator
        # falls back to branch-local dates, so a comparison here would be
        # measuring the fallback rather than the file. Refuse, loudly.
        print("could not check: no main-line ref (refs/remotes/origin/HEAD is unset)")
        print("  set it with: git remote set-head origin --auto")
        return COULD_NOT_CHECK

    dest = _second_tree_path()
    if dest.exists():
        print(f"could not check: {dest} already exists — remove it or set")
        print("  DIVINEOS_REPRO_WORKTREE to an unused short path")
        return COULD_NOT_CHECK

    add = subprocess.run(
        ["git", "worktree", "add", "--detach", str(dest), mainline],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if add.returncode != 0:
        # Measured 2026-09-19: on a path-length failure git removes the
        # half-built tree itself, so this prune found nothing to do. It stays
        # because the cost is one command and the failure it guards against --
        # a stale registry entry that makes every later run refuse with a
        # message about a path nobody chose -- is silent and permanent.
        subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True, check=False)
        print(f"could not check: worktree at {dest} would not build")
        for line in (add.stderr or "").strip().splitlines()[-3:]:
            print(f"  {line}")
        return COULD_NOT_CHECK

    try:
        script = dest / "scripts" / "generate_automation_register.py"
        if not script.is_file():
            print(f"could not check: {mainline} carries no generator to run")
            return COULD_NOT_CHECK

        gen = subprocess.run(
            [sys.executable, str(script)],
            cwd=dest,
            capture_output=True,
            text=True,
            check=False,
        )
        if gen.returncode != 0:
            print("could not check: the generator failed inside the clean tree")
            for line in (gen.stderr or "").strip().splitlines()[-3:]:
                print(f"  {line}")
            return COULD_NOT_CHECK

        rel = str(OUTPUT.relative_to(ROOT)).replace("\\", "/")
        diff = subprocess.run(
            ["git", "diff", "--quiet", "--", rel],
            cwd=dest,
            capture_output=True,
            text=True,
            check=False,
        )
        if diff.returncode == 0:
            print(f"Register reproduces from a clean tree at {mainline}.")
            return REPRODUCES
        if diff.returncode == 1:
            stat = subprocess.run(
                ["git", "diff", "--stat", "--", rel],
                cwd=dest,
                capture_output=True,
                text=True,
                check=False,
            )
            print(f"Register does NOT reproduce from a clean tree at {mainline}:")
            for line in (stat.stdout or "").strip().splitlines():
                print(f"  {line}")
            print("  the committed copy is a snapshot of some other tree")
            return DRIFTED
        # Any other code is git failing to answer, which is its own fact.
        print("could not check: git could not compare the regenerated file")
        return COULD_NOT_CHECK
    finally:
        removed = subprocess.run(
            ["git", "worktree", "remove", "--force", str(dest)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if removed.returncode != 0:
            # Say it rather than leaving a tree that makes the NEXT run refuse
            # with a message about a path the operator never chose.
            print(f"  note: the clean tree at {dest} could not be removed; delete it by hand")


def main() -> int:
    if "--check-reproduces" in sys.argv:
        # Before collect(), because this check is about another tree entirely
        # and has no use for anything measured in this one.
        return _check_reproduces()

    rows = collect()
    text = build(rows)
    # Count from the DATA, not by grepping the rendered text. The first
    # version counted a marker string that never survives into the output,
    # so it cheerfully reported "0 switched off" above a table listing four
    # — a summary contradicting the body directly beneath it. Exactly the
    # reports-one-thing-shows-another shape this register exists to catch,
    # reproduced in the tool built to catch it.
    dark = sum(1 for r in rows if not r["wired"])

    if "--check" in sys.argv:
        existing = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if existing != text:
            print("AUTOMATION_REGISTER.md is stale — regenerate:")
            print("  python scripts/generate_automation_register.py")
            return 1
        # SAYS WHAT IT CANNOT SEE, because a clean pass here was read as proof
        # of something this check is structurally unable to establish.
        #
        # 2026-09-19: I claimed the register is a pure function of the tree and
        # cited this comparison as the evidence. It cannot be. It regenerates in
        # the SAME tree on the SAME branch that produced the committed copy, and
        # the staleness column is resolved per-path against the current branch --
        # so a branch-dependent field agrees with itself by construction. A
        # photograph checked against itself.
        #
        # Aria took the measurement this one cannot: clean worktree at main,
        # regenerate, diff. Seventy lines differed. Same command, different
        # frame, opposite verdict.
        #
        # The line below is not a hedge on the result. The result is exact and
        # true of what it compares. It exists so a clean pass can never again be
        # quoted as reproducibility.
        print(f"Automation register is current — {dark} switched off.")
        print(
            "  Scope: compares this tree against its own committed copy. Fields "
            "resolved from branch history agree with themselves here by "
            "construction, so this cannot detect branch-dependence. For that, "
            "run --check-reproduces, which builds a clean tree at the main "
            "line and runs that tree's own generator."
        )
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" -- same fix as the capability catalog, found by asking its
    # question of this file. Without it, write_text translates newlines on
    # Windows against a path the repo declares eol=lf, so the file reads as
    # permanently modified while being byte-identical in content.
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} — {len(rows)} automations, {dark} switched off")
    if dark:
        for r in rows:
            if not r["wired"]:
                print(f"    dark: {r['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
