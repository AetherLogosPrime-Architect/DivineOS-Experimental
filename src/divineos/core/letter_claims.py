"""Measure the local state of every file a sibling's letter talks about.

## The stumble this exists for

2026-08-06. Aether sent a letter reporting that ``divineos.cmd`` swallowed exit
codes, with two measured commands and a fix already applied. Every signal said
believe him: he is careful, he showed his work, he had already acted. The cheap
close was to agree, thank him, and move on.

What stopped me was noticing our copy of that file already carried a fix for
the bug he described, dated six weeks earlier. I only noticed because I had the
file open for an unrelated reason. **That is luck of sequence, not a practice.**
One step further along and I would have shipped agreement with a finding whose
conclusion did not hold — and he would have built on it.

The rule I could have written instead is *"read our copy before agreeing."*
Aether's correction #167 is exactly about why that fails: *"practicing
something is not something that will ever hold son.. it doesnt work like that
lol.. it must be structural in some way."*

## Why this measures instead of pattern-matching

The obvious build is a detector for letters that sound like bug reports.
Aether's #151 rules that out: *"the issue with a keyword detector is then you
are playing infinite whack a mole.. the optimizer just learns to rephrase the
same shape."* A letter can report a defect without a single word this module
could match on.

So nothing here reads intent. It extracts **paths**, which are not a rhetorical
choice — a letter about a file has to name the file — and reports what those
files look like on this machine right now. No judgment about whether the letter
is right; that stays mine. It puts the evidence in my hand at the moment I am
forming the opinion, which is Andrew's missing third tier: not a wall, not a
doorman, automation that hands me the thing.

## Three states

``measured`` / ``not in this repo`` / ``could not look``. A path we failed to
stat must never render as a path with nothing interesting about it.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# Paths as they appear in letters: inside backticks, inside code fences, or
# bare in prose. Anchored on a real extension so ordinary prose containing a
# slash ("and/or", "he/she") is not dragged in.
_EXTENSIONS = r"py|sh|cmd|ps1|md|json|toml|yaml|yml|txt|cfg|ini|bat"
_PATH_RE = re.compile(
    r"(?<![\w./\\-])"  # not mid-token
    r"((?:[\w.-]+[/\\])*[\w.-]+\.(?:" + _EXTENSIONS + r"))"
    r"(?![\w])"
)

# Letters quote their own filenames constantly; measuring those is pure noise.
_IGNORE_PARTS = ("letters/", "letters\\")


@dataclass
class PathState:
    """What one mentioned path looks like locally.

    ``unlooked`` non-empty means we could not answer, which is its own state
    and is never folded into "nothing notable here".
    """

    mentioned: str
    resolved: Path | None = None
    exists: bool = False
    last_commit: str = ""
    unlooked: str = ""
    # True when the letter named a bare filename and we found it by searching.
    # Worth flagging: the letter's word for the file was not a path into this
    # tree, so the match is ours, not theirs.
    by_basename: bool = False


@dataclass
class LetterReading:
    letter: Path
    states: list[PathState] = field(default_factory=list)

    @property
    def measured(self) -> list[PathState]:
        return [s for s in self.states if s.exists and not s.unlooked]


def extract_paths(text: str) -> list[str]:
    """Every file path the letter names, deduped, in order of first mention."""
    seen: dict[str, None] = {}
    for m in _PATH_RE.finditer(text):
        raw = m.group(1).replace("\\", "/")
        if any(part in raw for part in _IGNORE_PARTS):
            continue
        seen.setdefault(raw, None)
    return list(seen)


_SEARCH_SKIP = {".git", ".direnv", ".venv", "node_modules", "__pycache__", "data"}


def _find_by_basename(repo_root: Path, name: str) -> tuple[Path | None, str]:
    """(match, error). Ambiguity is reported as an error, never guessed at.

    Two files with one name means we do not know which the letter meant, and
    picking one would produce a confident answer about the wrong file — worse
    than saying nothing, because it looks like evidence.
    """
    matches: list[Path] = []
    try:
        for candidate in repo_root.rglob(name):
            if any(part in _SEARCH_SKIP for part in candidate.parts):
                continue
            if candidate.is_file():
                matches.append(candidate)
                if len(matches) > 1:
                    break
    except OSError as exc:
        return None, f"could not search for {name}: {exc}"

    if not matches:
        return None, ""
    if len(matches) > 1:
        return None, f"{name} matches more than one file here; cannot tell which was meant"
    return matches[0], ""


def _last_commit(repo_root: Path, rel: Path) -> tuple[str, str]:
    """(subject-line, error). Empty error means the answer is trustworthy."""
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%h %ad %s", "--date=short", "--", str(rel)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return "", f"git log failed: {type(exc).__name__}: {exc}"
    if proc.returncode != 0:
        return "", f"git log exited {proc.returncode}"
    return proc.stdout.strip(), ""


def read_letter(letter: Path, repo_root: Path) -> LetterReading:
    """Resolve every path the letter mentions against this checkout."""
    reading = LetterReading(letter=letter)
    try:
        text = letter.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        reading.states.append(
            PathState(mentioned=str(letter), unlooked=f"could not read the letter: {exc}")
        )
        return reading

    for mentioned in extract_paths(text):
        st = PathState(mentioned=mentioned)
        candidate = repo_root / mentioned
        try:
            st.exists = candidate.is_file()
        except OSError as exc:
            st.unlooked = f"could not stat: {exc}"
            reading.states.append(st)
            continue

        if not st.exists:
            # A sibling writing about a shared file names it the way they say
            # it out loud - `divineos.cmd`, not `scripts/divineos.cmd`. The
            # first version of this module resolved only literal paths and
            # therefore missed BOTH files at the centre of the letter that
            # prompted it, while confidently reporting the one incidental file
            # it did find. Falling back to a basename search is what makes the
            # module answer the question it claims to answer.
            found, err = _find_by_basename(repo_root, Path(mentioned).name)
            if err:
                st.unlooked = err
                reading.states.append(st)
                continue
            if found is None:
                reading.states.append(st)
                continue
            candidate = found
            st.exists = True
            st.by_basename = True
            mentioned = str(found.relative_to(repo_root)).replace("\\", "/")

        # A letter naming the same file twice - once by path, once bare - is
        # ordinary prose, not two findings. Dedupe on what it resolved TO.
        if any(s.resolved == candidate for s in reading.states):
            continue

        st.resolved = candidate
        subject, err = _last_commit(repo_root, Path(mentioned))
        if err:
            st.unlooked = err
        else:
            st.last_commit = subject
        reading.states.append(st)

    return reading


def render(reading: LetterReading) -> str:
    """Evidence only. Whether the letter is right is not this module's call."""
    measured = reading.measured
    unlooked = [s for s in reading.states if s.unlooked]
    if not measured and not unlooked:
        return ""

    lines = [
        "## FILES THIS LETTER TALKS ABOUT - local state, measured now",
        "",
        "Not a verdict on the letter. Evidence, so an opinion about a shared",
        "file is formed with our copy of it in view rather than from the",
        "letter alone. Read the file itself before agreeing or disagreeing.",
        "",
    ]
    for st in measured:
        lines.append(f"  {st.mentioned}")
        if st.by_basename and st.resolved is not None:
            lines.append(f"      found here as: {st.resolved}")
        lines.append(f"      last change here: {st.last_commit or '(no commit touches it)'}")
    for st in unlooked:
        lines.append(f"  {st.mentioned}")
        lines.append(f"      COULD NOT LOOK: {st.unlooked} - this is not 'nothing to see'")
    return "\n".join(lines)
