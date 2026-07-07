"""Completion-quality probe for the initiative/overreach compass spectrum.

Andrew named the bug 2026-05-14 post-sleep: the prior initiative
detector measured pace (context overflows, tool calls, PR count).
That's the wrong axis. Pace is fine if completion lands; pace is the
wrong thing to measure. The right axis is whether what's already been
built has *closed the loop* — wired, dogfooded, useful — before the
next thing gets stood up.

This module walks recently-added mechanisms (new .py files in core/
hooks/scripts directories within the lookback window) and produces
the closure questions per mechanism:

- Is it wired into the path that needs it? (any other module import it?)
- Has it fired on real input? (any ledger event reference it?)
- Is it tested? (does a test_<name>.py exist?)

The probe DOES NOT decide whether a mechanism is "finished" —
the answers are descriptive evidence. The compass observation
position then scales with the count of mechanisms missing one or
more closure signals. Output evidence is the per-mechanism
questions, not a single pace-metric.

The probe is bounded — one git log call, one filesystem walk for
tests, lightweight grep for imports. Ledger lookup is opt-in via
`include_ledger=True` since it's the most expensive piece.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


# Directories whose new .py files count as "built mechanisms" worth
# probing for closure. Excludes tests/, docs/, exploration/ — those
# aren't mechanisms, they're commentary or substrate-internal.
#
# scripts/ excluded 2026-05-14: dogfood revealed standalone scripts
# have entry-point semantics (wired by invocability, not by import),
# so the import-grep proxy returns false positives. Add back if we
# build a separate entry-point-wiring probe later.
#
# .sh files in .claude/hooks/ handled separately: they're wired via
# .claude/settings.json hook registration, not via Python imports.
_MECHANISM_DIRS = (
    "src/divineos/core",
    "src/divineos/cli",
    "src/divineos/hooks",
    ".claude/hooks",
)


def _hook_registered_in_settings(hook_path: str, repo_root: Path) -> bool:
    """True if the shell hook path appears in .claude/settings.json.

    Hooks are wired via Claude Code settings, not Python imports.
    Conservative substring match — if the filename appears anywhere
    in the settings file, assume it's registered.
    """
    settings = repo_root / ".claude" / "settings.json"
    if not settings.exists():
        return False
    name = Path(hook_path).name
    try:
        text = settings.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return name in text


@dataclass(frozen=True)
class Unfinished:
    """A mechanism that lacks one or more closure signals.

    Fields:
    - path: repo-relative path of the mechanism file
    - has_test: a tests/test_<name>.py exists
    - has_wiring: at least one other module imports the mechanism's
      stem (best-effort grep — proxies for "wired in")
    - questions: the closure questions still unanswered for this one
    """

    path: str
    has_test: bool
    has_wiring: bool
    questions: list[str]


def _recently_added_files(days: int, repo_root: Path) -> list[str]:
    """Return repo-relative paths added within the last `days` days.

    Uses `git log --diff-filter=A` for added-only files. Quiet on
    git errors (returns []) so the probe doesn't break the compass
    on a non-git checkout or shallow clone.
    """
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "log",
                f"--since={days}.days.ago",
                "--diff-filter=A",
                "--name-only",
                "--pretty=format:",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if out.returncode != 0:
        return []
    paths = {ln.strip() for ln in out.stdout.splitlines() if ln.strip()}
    # Normalize to forward slashes; filter to mechanism dirs + .py only.
    keep: list[str] = []
    for p in paths:
        norm = p.replace("\\", "/")
        if not norm.endswith(".py") and not norm.endswith(".sh"):
            continue
        if not any(norm.startswith(d) for d in _MECHANISM_DIRS):
            continue
        keep.append(norm)
    return sorted(keep)


def _has_test_for(mechanism_path: str, repo_root: Path) -> bool:
    """True if any test exercises the mechanism.

    Two checks:
    1. Glob: tests/test_<stem>*.py exists (matches suffix-style names
       like test_X_binding.py or test_X_address_bypass.py).
    2. Grep: the stem is token-referenced from any file under tests/.
       Catches parametrized test files that cover many modules (e.g.
       a single test_all_council_experts.py exercising 41 experts).

    Refined 2026-05-14 dogfood pass-4: tested-ness is about whether
    a test exercises the module, not whether a same-named file exists.
    """
    stem = Path(mechanism_path).stem
    tests_dir = repo_root / "tests"
    if not tests_dir.exists():
        return False
    # Filename heuristic first (cheap)
    if any(tests_dir.glob(f"test_{stem}*.py")):
        return True
    # Fallback: token-match the stem in any test file
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "grep",
                "-l",
                "-E",
                rf"\b{stem}\b",
                "--",
                "tests/",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if out.returncode not in (0, 1):
        return False
    return bool(out.stdout.strip())


def _has_wiring_for(mechanism_path: str, repo_root: Path) -> bool:
    """True if any other .py file imports the mechanism's stem.

    Best-effort: greps `from ... import <stem>` and `import ... <stem>`
    across src/. Imperfect proxy — a module can be wired via dynamic
    import or string-name registry. But for the common case of
    `from divineos.core.foo import bar`, this catches it.
    """
    stem = Path(mechanism_path).stem
    src = repo_root / "src"
    if not src.exists():
        return False
    # Patterns for Python wiring (refined 2026-05-14 post-dogfood):
    #   from X.<stem> import ...
    #   import X.<stem>
    #   from X import ..., <stem>, ...  (whole-module import — CLI pattern)
    # Patterns for shell wiring:
    #   source path/to/<stem>.sh
    #   . path/to/<stem>.sh
    is_sh = mechanism_path.endswith(".sh")
    if is_sh:
        # Catches: `source <path>/<stem>.sh`, `. <path>/<stem>.sh`,
        # and `bash <path>/<stem>.sh` (setup-hooks.sh install pattern).
        # Token-match for any reference to <stem>.sh in another file —
        # less precise but catches real wiring shapes.
        pattern = rf"{stem}\.sh"
    else:
        # Token-match the stem as a word. Catches single-line imports,
        # multi-line imports (the line that names the symbol), and
        # any later references (registry calls like bio_commands.register).
        # False positives possible (incidental token collisions in
        # unrelated code) — acceptable trade for catching real wiring.
        pattern = rf"\b{stem}\b"
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "grep",
                "-l",
                "-E",
                pattern,
                "--",
                "src/",
                ".claude/",
                "setup/",
                "scripts/",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if out.returncode not in (0, 1):  # 1 = no matches, expected
        return False
    # Exclude the mechanism file itself from the hit list.
    hits = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    return any(h.replace("\\", "/") != mechanism_path for h in hits)


def _batch_has_test_for(paths: list[str], repo_root: Path) -> dict[str, bool]:
    """Batched _has_test_for — ONE git grep for N mechanisms.

    Andrew 2026-07-07 catch: the per-file loop was doing N subprocess
    calls, and CI runners under load exceeded the test's own 30s cap
    when N grew (~20+ new mechanisms in a day). This batches: one
    filename-glob pass with zero subprocess, one git-grep call for
    everything left.

    Returns a dict mapping each input path to True/False. Same
    semantics as calling _has_test_for(path) individually.
    """
    result: dict[str, bool] = {p: False for p in paths}
    if not paths:
        return result
    tests_dir = repo_root / "tests"
    if not tests_dir.exists():
        return result

    # Pass 1: filename heuristic (no subprocess)
    remaining: dict[str, list[str]] = {}
    for p in paths:
        stem = Path(p).stem
        if any(tests_dir.glob(f"test_{stem}*.py")):
            result[p] = True
        else:
            remaining.setdefault(stem, []).append(p)

    if not remaining:
        return result

    # Pass 2: single batched git grep for all remaining stems
    escaped = [re.escape(s) for s in remaining]
    pattern = rf"\b({'|'.join(escaped)})\b"
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "grep",
                "-h",
                "-o",
                "-E",
                pattern,
                "--",
                "tests/",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return result
    if out.returncode not in (0, 1):
        return result

    matched = {ln.strip() for ln in out.stdout.splitlines() if ln.strip()}
    for stem, mech_paths in remaining.items():
        if stem in matched:
            for p in mech_paths:
                result[p] = True
    return result


def _batch_has_wiring_for(paths: list[str], repo_root: Path) -> dict[str, bool]:
    """Batched _has_wiring_for — ONE git grep for .py stems, one for .sh stems.

    Same optimization as _batch_has_test_for. The .py and .sh patterns
    differ (\\b<stem>\\b vs <stem>\\.sh) so they get two separate greps,
    not one — but 2 << N.

    Excludes the mechanism's own file from hits (a mechanism that only
    references itself is not wired anywhere).
    """
    result: dict[str, bool] = {p: False for p in paths}
    if not paths:
        return result
    src = repo_root / "src"
    if not src.exists():
        return result

    # Split by extension — different patterns needed.
    py_paths: dict[str, list[str]] = {}
    sh_paths: dict[str, list[str]] = {}
    for p in paths:
        stem = Path(p).stem
        if p.endswith(".sh"):
            sh_paths.setdefault(stem, []).append(p)
        else:
            py_paths.setdefault(stem, []).append(p)

    def _batch_grep(stems: dict[str, list[str]], pattern_fmt: str) -> dict[str, set[str]]:
        """Return {stem: set-of-file-paths-that-matched-it}."""
        if not stems:
            return {}
        escaped = [re.escape(s) for s in stems]
        if pattern_fmt == "word":
            pattern = rf"\b({'|'.join(escaped)})\b"
        else:  # "sh_suffix"
            pattern = rf"({'|'.join(escaped)})\.sh"
        try:
            out = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "grep",
                    "-o",
                    "-E",
                    pattern,
                    "--",
                    "src/",
                    ".claude/",
                    "setup/",
                    "scripts/",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {}
        if out.returncode not in (0, 1):
            return {}
        hits: dict[str, set[str]] = {s: set() for s in stems}
        for line in out.stdout.splitlines():
            if ":" not in line:
                continue
            file_part, matched = line.rsplit(":", 1)
            file_norm = file_part.strip().replace("\\", "/")
            matched = matched.strip()
            stem = matched[:-3] if matched.endswith(".sh") else matched
            if stem in hits:
                hits[stem].add(file_norm)
        return hits

    py_hits = _batch_grep(py_paths, "word")
    sh_hits = _batch_grep(sh_paths, "sh_suffix")

    for stem, mech_paths in py_paths.items():
        matched_files = py_hits.get(stem, set())
        for mech_path in mech_paths:
            other_hits = {f for f in matched_files if f != mech_path}
            if other_hits:
                result[mech_path] = True
    for stem, mech_paths in sh_paths.items():
        matched_files = sh_hits.get(stem, set())
        for mech_path in mech_paths:
            other_hits = {f for f in matched_files if f != mech_path}
            if other_hits:
                result[mech_path] = True
    return result


def _questions_for(path: str, has_test: bool, has_wiring: bool) -> list[str]:
    """Build the closure questions for what's still unanswered."""
    qs: list[str] = []
    if not has_wiring:
        qs.append("Is it wired into the path that needs it?")
    if not has_test:
        qs.append("Has it been tested on real input?")
    # Usefulness is always an open question — the probe can't auto-answer it.
    qs.append("Does it help — has it caught something it was built to catch?")
    return qs


def unfinished_mechanisms(
    days: int = 14,
    repo_root: Path | str | None = None,
    max_probe: int | None = None,
) -> list[Unfinished]:
    """Walk recently-added mechanism files; return those missing closure.

    Returns Unfinished entries for mechanisms that lack at least one
    of {test, wiring}. The usefulness question is always open and
    rides along in the question list so it gets surfaced even for
    mechanisms with test+wiring.

    max_probe bounds how many recently-added files get the per-file
    git-grep closure probe (each file costs 2 git greps). Unbounded, a
    14-day window can hold 90+ files → the scan exceeds CI's 30s timeout
    when run in a hot path (the rudder block message). Callers on a hot
    path (compass_rudder._initiative_channel_section) pass a small cap;
    the once-per-session compass reflect call leaves it None (full scan).
    """
    root = Path(repo_root) if repo_root else Path.cwd()
    paths = _recently_added_files(days, root)
    if max_probe is not None:
        paths = paths[:max_probe]

    # Batched probe (Andrew 2026-07-07): the per-file loop was doing
    # 2N subprocess calls (one _has_test_for + one _has_wiring_for
    # per file). Under CI load with N > ~15 that exceeded the test's
    # own 30s cap. The batched helpers collapse it to 3 git-grep
    # calls total (one for tests, one for .py wiring, one for .sh
    # wiring) regardless of N.
    test_map = _batch_has_test_for(paths, root)
    wiring_map = _batch_has_wiring_for(paths, root)

    out: list[Unfinished] = []
    for p in paths:
        has_test = test_map.get(p, False)
        has_wiring = wiring_map.get(p, False)
        # Shell hooks: wiring can ALSO come from .claude/settings.json
        # registration (Claude Code hook wiring shape). The batched
        # wiring probe already covers grep-based wiring; this adds the
        # settings-JSON substring check per shell hook.
        if p.endswith(".sh") and not has_wiring:
            has_wiring = _hook_registered_in_settings(p, root)
        # Surface ANY mechanism missing wiring or test, OR include all
        # recently-built ones for the usefulness question. To keep the
        # signal sharp, only surface if at least one of wiring/test is
        # missing — usefulness alone applies to everything and would
        # flood the signal.
        if has_test and has_wiring:
            continue
        out.append(
            Unfinished(
                path=p,
                has_test=has_test,
                has_wiring=has_wiring,
                questions=_questions_for(p, has_test, has_wiring),
            )
        )
    return out


def format_for_compass(unfinished: list[Unfinished]) -> str:
    """Format unfinished mechanisms as compass-evidence string.

    Compact, scannable, naming the questions per mechanism so the
    observation is descriptive rather than a single number.
    """
    if not unfinished:
        return "no recently-built mechanisms lack closure signals"
    lines = [f"{len(unfinished)} recently-built mechanism(s) missing closure:"]
    for u in unfinished[:5]:  # cap at 5 to keep evidence string bounded
        stem = Path(u.path).stem
        flags = []
        if not u.has_wiring:
            flags.append("unwired")
        if not u.has_test:
            flags.append("untested")
        lines.append(f"  - {stem} [{', '.join(flags)}]")
    if len(unfinished) > 5:
        lines.append(f"  ... +{len(unfinished) - 5} more")
    return " | ".join(lines)


__all__ = ["Unfinished", "format_for_compass", "unfinished_mechanisms"]
