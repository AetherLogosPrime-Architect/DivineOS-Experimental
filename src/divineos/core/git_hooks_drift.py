"""Do the installed git hooks still say what setup/setup-hooks.sh would write?

Both ways, per hook, and it never overwrites. 2026-10-04: Aria's install was
older than her setup, so two checks never ran in her house; mine differed in
both directions (commit-msg lacked setup's merge-resolution check, pre-push had
a deletion skip setup lacked). The session-start guard looked for one marker in
one hook and saw neither. A reinstall loses whatever only the install had, so
which side is right is left to whoever reads the report. hook_layer.py is the
instrument for the Claude hooks; this one is for the git hooks.
Draft: docs/drafts/installed_hooks_match_setup_draft_2026-10-04.md.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# `cat > "$HOOKS_DIR/pre-push" << 'EOF'` ... `EOF`
_HEREDOC = re.compile(
    r"cat\s*>\s*\"?\$\{?\w+\}?/([\w-]+)\"?\s*<<-?\s*['\"]?(\w+)['\"]?\n(.*?)\n\2\n", re.S
)


@dataclass(frozen=True)
class HookDrift:
    name: str
    state: str  # "match" | "missing" | "differs"
    only_in_setup: tuple[str, ...] = ()
    only_installed: tuple[str, ...] = ()


@dataclass(frozen=True)
class DriftReport:
    hooks: tuple[HookDrift, ...] = ()
    not_judged: tuple[str, ...] = ()
    could_not_read: str = ""

    @property
    def drifted(self) -> tuple[HookDrift, ...]:
        return tuple(h for h in self.hooks if h.state != "match")


def setup_hooks(setup_text: str) -> dict[str, str]:
    """Each hook setup writes, by name, as the text it writes."""
    return {name: body for name, _, body in _HEREDOC.findall(setup_text)}


def _lines_only_in(a: list[str], b: list[str]) -> tuple[str, ...]:
    rest = list(b)
    out = []
    for line in a:
        if line in rest:
            rest.remove(line)
        elif line.strip():
            out.append(line)
    return tuple(out)


def compare(setup_text: str, hooks_dir: Path) -> DriftReport:
    wanted = setup_hooks(setup_text)
    if not wanted:
        return DriftReport(could_not_read="setup writes no hooks this check can read")
    results = []
    for name, body in wanted.items():
        path = hooks_dir / name
        if not path.is_file():
            results.append(HookDrift(name, "missing"))
            continue
        have = path.read_text(encoding="utf-8", errors="replace").strip()
        want = body.strip()
        if have == want:
            results.append(HookDrift(name, "match"))
            continue
        h, w = have.splitlines(), want.splitlines()
        results.append(HookDrift(name, "differs", _lines_only_in(w, h), _lines_only_in(h, w)))
    others: list[str] = []
    if hooks_dir.is_dir():
        others = sorted(
            p.name
            for p in hooks_dir.iterdir()
            if p.is_file() and not p.name.endswith(".sample") and p.name not in wanted
        )
    return DriftReport(tuple(results), tuple(others))


def check_repo(repo: Path) -> DriftReport:
    try:
        setup_text = (repo / "setup" / "setup-hooks.sh").read_text(encoding="utf-8")
        common = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return DriftReport(could_not_read=f"{type(exc).__name__}: {exc}")
    return compare(setup_text, Path(common) / "hooks")


def render(report: DriftReport, show: int = 3) -> str:
    """Nothing when every hook matches; otherwise which way each one differs."""
    if report.could_not_read:
        return f"## GIT HOOKS vs SETUP: could not read ({report.could_not_read}). Not a match."
    if not report.drifted:
        return ""
    lines = ["## GIT HOOKS vs SETUP: the installed hooks are not what setup writes", ""]
    for h in report.drifted:
        if h.state == "missing":
            lines.append(f"- {h.name}: MISSING. Setup writes it; it is not installed.")
            continue
        lines.append(
            f"- {h.name}: differs. {len(h.only_in_setup)} line(s) setup has that the "
            f"install lacks, {len(h.only_installed)} the install has that setup lacks."
        )
        lines += [f"    setup only:   {line.strip()[:110]}" for line in h.only_in_setup[:show]]
        lines += [f"    install only: {line.strip()[:110]}" for line in h.only_installed[:show]]
    lines += [
        "",
        "Nothing was overwritten. A reinstall (bash setup/setup-hooks.sh) loses every",
        "install-only line, so move those into setup first if they should stay.",
        "A hook that comes back after drifting has its first real run ahead of it, and",
        "that run is its first test (Aria's broke four ways on its first job).",
    ]
    if report.not_judged:
        lines.append(f"Not judged (setup does not write them): {', '.join(report.not_judged)}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    text = render(check_repo(Path(sys.argv[1] if len(sys.argv) > 1 else ".")))
    if text:
        print(text)
