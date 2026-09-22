#!/usr/bin/env python3
"""Refuse to let a retired rule be handed over as a current one.

WHY THIS EXISTS. On 2026-09-21 I told Andrew a branch needed no sign-off. I
was wrong, and the reason was not that I had misremembered: three live
surfaces stated the retired rule as current. His answer named the defect
better than I had:

    "it is from the system. the system handed you old rules... when rules are
    changed or superceded if you want to archive it you can or use a link to
    the retired rule somewhere else but it should NOT be able to hand you old
    rules"

WHAT IT SCANS, AND WHY NOT EVERYTHING. 117 files in this tree mention the
retired model; 115 of them harmed nobody. What harmed me were the ones in the
LOAD PATH -- text that loads at session start, text a gate prints at the
moment it blocks someone, and text inside a live script where a search finds
it looking load-bearing. The cause is position, not existence. So the surface
list below is deliberately short, and the checker prints what it did NOT look
at, because a list of scanned places is only half an answer.

WHAT IT CANNOT DO. It matches phrases, so it finds retired rules that were
COPIED -- the same sentence standing in several places because each was
written by reading the last. That is the mechanism actually observed. It
cannot find a retired rule restated in different words, and it cannot find
the copy that lives in me rather than on disk, which is the one that spoke to
Andrew tonight before any file was consulted. A clean run means *none of the
registered phrases appeared in the scanned surfaces* and never *no retired
rule is being served*.

DELIBERATE MENTIONS. A live file sometimes has to name a retired rule, to say
that it is retired or to explain why the replacement exists. Put the marker
RETIRED-RULE-OK on that line. It is ugly on purpose and greppable on purpose.

Exit codes: 0 clean, 1 a retired rule is being served, 2 the checker could
not run. Three states, three codes, because collapsing the third into either
of the others is the failure this whole house keeps repeating.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTER_DIR = REPO_ROOT / "docs" / "retired_rules"

# The marker that says "I know this states an old rule and I meant to".
_DELIBERATE = "RETIRED-RULE-OK"

# The load path: places whose text is handed to a reader as instruction.
# Each entry is a glob relative to the repo root.
SCANNED_GLOBS: tuple[str, ...] = (
    "CLAUDE.md",
    "README.md",
    "LOADOUT.md",
    "docs/foundational_truths.md",
    "docs/build_flow.md",
    "docs/audit_system.md",
    ".claude/skills/**/*.md",
    ".claude/agents/*.md",
    ".claude/hooks/**/*.sh",
    "scripts/**/*.sh",
    "scripts/**/*.py",
    "src/divineos/**/*.py",
)

# Said out loud in the report rather than left to be inferred from the list
# above. Each line is a place a retired rule could sit unscanned.
NOT_SCANNED: tuple[str, ...] = (
    "docs/ apart from the three files named above -- audit rounds, drafts, "
    "design notes and the retired-rules archive itself",
    "family/, exploration/, dreams/ -- letters and personal writing, which "
    "record what was believed at the time and are not instructions",
    "tests/ -- a test may legitimately assert the old behaviour while proving it was replaced",
    "git history, and any branch other than the working tree",
    "anything outside this repository, including what I say out loud",
)


class CheckerError(RuntimeError):
    """The checker could not form an opinion. Never the same as a clean run."""


# --------------------------------------------------------------- the register

_HEADER = re.compile(r"<!--\s*retired-rule\s*(.*?)-->", re.DOTALL)


class RetiredRule:
    def __init__(self, source: Path, fields: dict[str, list[str]]):
        self.source = source
        self.rule_id = (fields.get("id") or ["<unnamed>"])[0]
        self.retired = (fields.get("retired") or ["<undated>"])[0]
        self.successor = (fields.get("successor") or ["<none recorded>"])[0]
        raw_patterns = fields.get("pattern") or []
        if not raw_patterns:
            raise CheckerError(
                f"{source.name} registers no pattern, so it can never match "
                f"anything. An entry with no pattern is an archive note, not "
                f"a guard -- either give it a pattern or say so in the file."
            )
        self.patterns = [re.compile(p) for p in raw_patterns]


def load_register() -> list[RetiredRule]:
    if not REGISTER_DIR.is_dir():
        raise CheckerError(f"no register directory at {REGISTER_DIR}")

    rules: list[RetiredRule] = []
    for path in sorted(REGISTER_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        match = _HEADER.search(text)
        if not match:
            raise CheckerError(
                f"{path.name} has no retired-rule header block. A file in the "
                f"register that the checker cannot parse is worse than no file "
                f"at all: it looks like coverage and provides none."
            )
        fields: dict[str, list[str]] = {}
        for line in match.group(1).splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            fields.setdefault(key.strip(), []).append(value.strip())
        rules.append(RetiredRule(path, fields))

    if not rules:
        raise CheckerError(
            "the register is empty, so this check can only ever pass. "
            "Reported as could-not-run rather than clean."
        )
    return rules


# --------------------------------------------------------------- the scanning


def scanned_files() -> list[Path]:
    seen: dict[Path, None] = {}
    for pattern in SCANNED_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if not path.is_file():
                continue
            if REGISTER_DIR in path.parents:
                continue
            if "__pycache__" in path.parts:
                continue
            seen.setdefault(path, None)
    return list(seen)


class Hit:
    def __init__(self, rule: RetiredRule, path: Path, lineno: int, line: str):
        self.rule = rule
        self.path = path
        self.lineno = lineno
        self.line = line.strip()


def find_hits(rules: list[RetiredRule], files: list[Path]) -> tuple[list[Hit], list[Path]]:
    """Returns the hits, and separately the files that could not be read.

    Unreadable is its own answer. Folding it into 'no hits' is the exact
    three-states-into-two collapse that produced a detector shipping with the
    fault it was built to hunt, ten days ago.
    """
    hits: list[Hit] = []
    unreadable: list[Path] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            unreadable.append(path)
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _DELIBERATE in line:
                continue
            for rule in rules:
                if any(p.search(line) for p in rule.patterns):
                    hits.append(Hit(rule, path, lineno, line))
                    break
    return hits, unreadable


# ------------------------------------------------------------------- baseline

BASELINE_PATH = REPO_ROOT / "scripts" / "retired_rules_baseline.txt"


def load_baseline() -> set[str]:
    """Sites already known to state a retired rule, as ``path:rule_id``.

    WHY A BASELINE RATHER THAN A CLEAN SWEEP. The first run found seven sites.
    Widening the patterns to catch a phrasing the narrow ones had missed took
    it to twenty-six, and most of the new ones are a whole VOCABULARY -- the
    adjective the retired model gave to a commit -- spread through comments,
    docstrings and messages in code that is otherwise correct. Two of them are
    not vocabulary at all but live enforcement still asking the retired
    question, and one of those governs whether a merge needs review.

    Sweeping all twenty-six in one pass, at the end of a day when the thing
    actually owed is a cleared branch pile, would be one guess applied
    twenty-six times. So the set is pinned: a NEW site fails the check, a
    pinned one is reported as work owed. The list may shrink and never grow,
    which is the same discipline the refusal-order baseline runs on, built
    the same day for the same reason.
    """
    if not BASELINE_PATH.exists():
        return set()
    out: set[str] = set()
    for line in BASELINE_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            out.add(stripped)
    return out


# ------------------------------------------------------------------ reporting


def main() -> int:
    try:
        rules = load_register()
        files = scanned_files()
        hits, unreadable = find_hits(rules, files)
        baseline = load_baseline()
    except CheckerError as exc:
        print("=== Retired rules: COULD NOT RUN ===")
        print(f"  {exc}")
        print("")
        print("  This is not a pass. Nothing was checked.")
        return 2

    rel = lambda p: p.relative_to(REPO_ROOT).as_posix()  # noqa: E731

    fresh: list[Hit] = []
    pinned: list[Hit] = []
    for hit in hits:
        key = f"{rel(hit.path)}:{hit.rule.rule_id}"
        (pinned if key in baseline else fresh).append(hit)

    # A pinned site that is gone: say so, so the list cannot rot in the
    # direction that flatters me.
    still_present = {f"{rel(h.path)}:{h.rule.rule_id}" for h in pinned}
    cleared = sorted(baseline - still_present)

    if fresh:
        print("=== Retired rules: A RETIRED RULE IS BEING SERVED ===")
        print("")
        for hit in fresh:
            print(f"  {rel(hit.path)}:{hit.lineno}")
            print(f"    {hit.line[:160]}")
            print(f"    states the rule retired {hit.rule.retired}: {hit.rule.rule_id}")
            print(f"    what governs instead: {hit.rule.successor}")
            print(f"    the archive entry: {rel(hit.rule.source)}")
            print("")
        print("  Fix the text so it states what is actually in force. If this")
        print(f"  line names the old rule deliberately, put {_DELIBERATE} on it.")
        print("")
        print("  Pinning it in the baseline is for sites that predate this")
        print("  check, not for a line written after it.")
        return 1

    if pinned:
        print(f"  {len(pinned)} pinned site(s) still state a retired rule. Work owed,")
        print("  not a failure -- see scripts/retired_rules_baseline.txt for why.")
    if cleared:
        print(f"  {len(cleared)} pinned site(s) are now CLEAN and should be removed")
        print("  from the baseline:")
        for key in cleared:
            print(f"    - {key}")
    if pinned or cleared:
        print("")

    print("=== Retired rules: no NEW site states a registered phrase ===")
    print(f"  register:  {len(rules)} retired rule(s), from {rel(REGISTER_DIR)}")
    for rule in rules:
        print(f"             - {rule.rule_id} (retired {rule.retired})")
    print(f"  scanned:   {len(files)} file(s) on the load path")
    if unreadable:
        print(f"  UNREADABLE: {len(unreadable)} file(s) could not be read, so they were")
        print("             NOT checked. That is not the same as clean:")
        for path in unreadable[:10]:
            print(f"             - {rel(path)}")
    print("")
    print("  WHAT THIS DOES NOT SAY. It does not say no retired rule is being")
    print("  served. It says no REGISTERED PHRASE appeared in the SCANNED")
    print("  files. A retired rule restated in different words passes clean,")
    print("  and so does one that lives only in the person reading this.")
    print("")
    print("  Not looked at:")
    for line in NOT_SCANNED:
        print(f"    - {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
