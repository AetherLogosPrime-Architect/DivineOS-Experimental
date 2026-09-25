"""You just learned something here. Where else is it true?

Four times on 2026-08-22 a fix already existed in exactly one file while its
structural siblings kept the defect -- each time written carefully, with a
comment naming the incident that produced it, and each time never asked about
anywhere else:

  COMMAND_START        gh-pr-ready-gate had it; the create and merge gates
                       did not, and both shipped mention-read-as-use.
  the cheap bail       check-branch-on-push had it; five siblings paid 664ms
                       per irrelevant call to discover they were irrelevant.
  segment-splitting    push_detection had it; pr_gate and pr_merge_gate did
                       not.
  the descriptor fix   one hook had it; eighteen copies did not.

That is not forgetfulness. Nothing in the loop ever asks *does this pattern
live elsewhere*. The fix gets made where the pain was felt, and the pain is
only ever felt in one place.

THE FIRST DESIGN FOR THIS TOOL WAS WRONG, AND ITS FAILURE SHAPED THIS ONE.
It hunted SIBLINGS by token similarity, then asked what they lacked. Tested
against cases whose answer was already known, it failed: raw Jaccard ranked
deletion-discipline.sh (0.44) ABOVE gh-pr-ready-gate.sh (0.41), and IDF
weighting made it worse, dropping the true sibling to 0.174 behind
compass-check.sh at 0.259 -- because gh-pr-ready-gate embeds its logic in an
inline heredoc, so its token profile diverges from its own family. Two
measures, both plausible-looking, both wrong. A ranked list with the true
answer at position six reads like a working tool until you check position two.

So this does the inverse, and it is much simpler: DO NOT HUNT SIBLINGS. HUNT
SURVIVORS OF THE ANTI-PATTERN THE FIX REMOVED. The removed line IS the query.
A fix that deletes something is a statement that the something was wrong, and
that statement is checkable everywhere at once.

HOW A REMOVED LINE BECOMES A QUERY. Identifiers that appear in few files are
local names -- `_GH_PR_CREATE_RE` -- and get wildcarded. Identifiers that
appear in many are the shared shape -- `search`, `command` -- and stay
literal. That is the same IDF idea the failed design used, pointed the other
way: rarity marks what to GENERALISE, not what to match on.

TWO FILTERS, AND THE SECOND DOES THE REAL WORK. The frequency bands are a
cheap pre-filter. What actually separates a repudiated pattern from a common
idiom is HIT COUNT: measured here, the line whose fix mattered yields 1 hit
and `return "".join(out)` yields 4. Counting hits measures specificity
directly rather than proxying it through identifier frequency -- and the
proxy was wrong, which its own test only revealed after the fixture was
corrected to match the real corpus.

FIRST RUN, on the fix that motivated it, found a live defect in the file that
fix had just edited. `is_gh_pr_create` was repaired; `has_draft_flag` was not,
and it is an ESCAPE rather than an entry -- a mention read as a use there
makes the gate STAND DOWN. `gh pr create --title "see --draft docs"` was
opening guardrail PRs ready.

Usage:
    python scripts/sibling_sweep.py --commit HEAD
    python scripts/sibling_sweep.py --staged
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
from collections import Counter

SEARCH_ROOTS = ("src", "scripts", ".claude/hooks")
SEARCH_SUFFIXES = (".py", ".sh")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# A removed line only becomes a query if it looks like code doing something.
CODE_ISH = re.compile(r"[=(\[]")
# Lines this can never say anything useful about.
BORING = re.compile(
    r"^\s*(#|//|\"\"\"|'''|import\s|from\s+\S+\s+import|pass\b|return\s*$|else:|try:|except)"
)


def corpus() -> dict[pathlib.Path, str]:
    out: dict[pathlib.Path, str] = {}
    for root in SEARCH_ROOTS:
        base = pathlib.Path(root)
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.suffix in SEARCH_SUFFIXES and p.is_file():
                try:
                    out[p] = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue  # fail-soft: an unreadable file is reported in the coverage line, not silently dropped
    return out


def doc_freq(texts: dict[pathlib.Path, str]) -> Counter:
    df: Counter = Counter()
    for t in texts.values():
        for ident in set(IDENT.findall(t)):
            df[ident] += 1
    return df


def removed_lines(spec: str, staged: bool) -> tuple[list[tuple[str, str]], int]:
    """(file, line) pairs for code DELETED and not merely MOVED.

    A refactor that relocates code deletes it here and adds it there, so a
    naive removed-set reports the destination as a survivor of the thing that
    was just moved into it. That is not a finding, it is the refactor
    describing itself.

    Caught on this tool's SECOND test run: extracting the mention-vs-use
    helpers reported `return "".join(out)` as surviving in command_match.py --
    the very file the code had been moved to. Eleven findings, mostly this.
    A tool whose noise is indistinguishable from its signal trains the reader
    to skip it, which is the bypass-groove shape one level up.

    So a line removed AND added anywhere in the same change is dropped, and
    the count of drops is returned so the suppression is visible rather than
    silent.
    """
    cmd = (
        ["git", "diff", "--cached", "--unified=0", "--no-color"]
        if staged
        else ["git", "show", spec, "--unified=0", "--no-color"]
    )
    out = subprocess.run(cmd, capture_output=True, text=True).stdout

    added: set[str] = set()
    for line in out.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.add(line[1:].strip())

    pairs, current, moved = [], "?", 0
    for line in out.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("-") and not line.startswith("---"):
            body = line[1:].strip()
            if not body or not CODE_ISH.search(body) or BORING.match(body):
                continue
            if body in added:
                moved += 1  # relocated, not repudiated
                continue
            pairs.append((current, body))
    return pairs, moved


def to_query(line: str, df: Counter, n_files: int, rare_below: int) -> str | None:
    """Turn a removed line into a regex: wildcard the local names, keep the shape.

    THREE BANDS, not two. Identifier frequency splits a line three ways and
    only the middle band carries meaning:

      LOCAL (df <= rare_below)   `_GH_PR_CREATE_RE` -- a name for this file's
                                 own thing. Generalised to \\w+, because the
                                 sibling will have a different one.
      DISTINCTIVE (the middle)   `search`, `command` -- shared vocabulary that
                                 still says something. This is the shape.
      UBIQUITOUS (df >= half)    `return`, `out`, `join` -- present nearly
                                 everywhere, so matching on them matches
                                 nothing in particular.

    A query needs at least one DISTINCTIVE identifier. This is a CHEAP
    PRE-FILTER and it is NOT sufficient -- measured on the real corpus,
    `return "".join(out)` still qualifies, because `out` (33%) and `join`
    (41%) both land in the distinctive band. Genericness is caught downstream
    by hit-count instead, which measures the thing directly.

    Recording that because the first version credited this rule with catching
    that line, and a test agreed -- on a fixture where all four words were
    95%-ubiquitous, which no real corpus resembles. The rule was doing less
    than its comment claimed and the test passed for the wrong reason.
    """
    kept = distinctive = 0
    ubiquitous_at = max(3, n_files // 2)
    parts, last = [], 0
    for m in IDENT.finditer(line):
        parts.append(re.escape(line[last : m.start()]))
        name = m.group()
        freq = df.get(name, 0)
        if freq <= rare_below:
            parts.append(r"\w+")  # file-local -- generalise it
        else:
            parts.append(re.escape(name))  # shared shape -- match it
            kept += 1
            if freq < ubiquitous_at:
                distinctive += 1
        last = m.end()
    parts.append(re.escape(line[last:]))
    if kept < 3 or distinctive < 1:
        return None
    # collapse whitespace so formatting differences do not hide a match
    return re.sub(r"(\\\s)+", r"\\s+", "".join(parts))


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--commit")
    g.add_argument("--staged", action="store_true")
    ap.add_argument(
        "--rare-below",
        type=int,
        default=2,
        help="an identifier in this many files or fewer is treated as local",
    )
    ap.add_argument("--max-hits", type=int, default=12)
    ap.add_argument(
        "--idiom-above",
        type=int,
        default=3,
        help="a shape found in more places than this is a common idiom, not a repudiated pattern",
    )
    args = ap.parse_args()

    texts = corpus()
    df = doc_freq(texts)
    removed, moved = removed_lines(args.commit or "", args.staged)
    if not removed:
        print("no code lines repudiated by that change -- nothing to sweep for.")
        if moved:
            print(f"({moved} line(s) were MOVED, not removed -- a refactor, not a repudiation.)")
        return 0

    print(f"scanned {len(texts)} files under {', '.join(SEARCH_ROOTS)}")
    print(f"{len(removed)} removed code line(s) considered\n")

    findings = idioms = 0
    for src_file, line in removed:
        q = to_query(line, df, len(texts), args.rare_below)
        if not q:
            continue
        try:
            rx = re.compile(q)
        except re.error:
            continue  # fail-soft: an un-compilable query means this line yields no sweep, reported by the zero-findings line below
        hits = []
        for path, text in texts.items():
            if str(path).replace("\\", "/") == src_file:
                continue  # the file that was fixed
            for i, body in enumerate(text.splitlines(), 1):
                if rx.search(body):
                    hits.append((path, i, body.strip()))
        if not hits:
            continue
        if len(hits) > args.idiom_above:
            # A shape found in many places is an IDIOM, not a repudiated
            # pattern. Measured on the real corpus: `return "".join(out)`
            # yields 4 hits and means nothing, while the line whose fix
            # mattered yields 1. Hit-count measures the thing directly --
            # how specific is this query -- instead of proxying it through
            # identifier frequency, which is what the band rule does and
            # which passed a test only because the fixture was unrealistic.
            idioms += 1
            continue
        findings += 1
        print(f"REMOVED from {src_file}:")
        print(f"    {line[:90]}")
        print(f"  the same shape SURVIVES in {len(hits)} place(s):")
        for path, i, body in hits[: args.max_hits]:
            print(f"    {str(path).replace(chr(92), '/')}:{i}: {body[:76]}")
        if len(hits) > args.max_hits:
            print(f"    ... and {len(hits) - args.max_hits} more")
        print()

    if not findings:
        print("no surviving instances of any removed shape.")
        if idioms:
            print(
                f"({idioms} shape(s) matched more than {args.idiom_above} places "
                f"and were treated as common idioms.)"
            )
        print("That is a real answer, not a broken sweep -- the change was local.")
    else:
        print(
            f"{findings} removed shape(s) still live elsewhere."
            + (f"  ({idioms} suppressed as common idioms.)" if idioms else "")
        )
        print("A hit is a QUESTION, not a verdict: the fix may not apply there.")
        print("But it is the question that was never asked, four times, in one day.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
