"""Find files on ANY branch whose names resemble one about to be created.

Per prereg-ad19dea9b03d. Built 2026-08-27 from a duplicate I produced
that same day.

WHAT HAPPENED. On the twentieth I built a letter-state store for
Aletheia, put it in the repository so she could read it, wrote her a
letter explaining the design, and committed it on one branch. On the
twenty-seventh I read her asking for that store, concluded it did not
exist, built a second one from scratch on a different branch, and told
her it was built. Both are real. Neither knew about the other.

WHY THE EXISTING GUARD DID NOT CATCH IT. The verify-before-build gate
fired at me repeatedly that day and I cleared it every time by opening
a test file, because opening a file in tests/ is one of the things it
accepts. Its name says verify-before-build; its predicate is "has this
session read something recently". Reading SOMETHING is not searching
for THIS, and the gap between those two is exactly wide enough for a
duplicate.

AND THE SECOND HALF, which is the part no discipline could have closed:
the earlier store was not on the branch I was standing on. A perfect
search of my working tree would have come back empty and CONFIRMED the
belief. Any check that looks only at the current checkout is answering
a narrower question than the one being asked.

WHAT THIS TESTS, STATED SO NOBODY READS IT WIDER. It matches FILENAMES,
across every ref. It does not read content and it does not understand
concepts. A prior version named nothing like the new one is invisible to
it. Silence here means "no similarly-named file", never "no prior art" —
and the moment I treat the second reading as the first, this has become
the class it was built to catch.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# Words that carry no discriminating signal in a filename here. Matching
# on them would return most of the repository, which is the same as
# returning nothing while looking thorough.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "the",
        "of",
        "to",
        "for",
        "in",
        "on",
        "by",
        "src",
        "test",
        "tests",
        "core",
        "cli",
        "scripts",
        "divineos",
        "py",
        "sh",
        "md",
        "json",
        "check",
        "utils",
        "util",
        "helper",
        "main",
        "init",
        "base",
        "common",
        "new",
        "old",
        "tmp",
    }
)

_MIN_TOKEN = 4
_SHOW_LIMIT = 8


@dataclass(frozen=True)
class PriorArt:
    """One similarly-named file, and where it lives."""

    path: str
    refs: tuple[str, ...]
    shared_tokens: tuple[str, ...]


# THREE STATES, THREE CODES. The wrapper used to decide on whether anything
# had been printed, which collapsed could-not-look into found-nothing because
# neither printed. Naming them here rather than as bare numbers at the return
# sites, so the shell side and this side cannot drift apart on what a code
# means -- the two-copies-of-one-fact shape that cost three council lenses
# their walkability the same week.
_EXIT_NOTHING_FOUND = 0
_EXIT_PRIOR_ART = 2
_EXIT_COULD_NOT_LOOK = 3


@dataclass(frozen=True)
class ScanResult:
    """What the scan found AND what it looked at.

    The coverage fields are not decoration. This whole module exists
    because a check that could not tell "nothing found" from "did not
    run" let a duplicate through, so its own report must never have that
    ambiguity — the first falsifier in its pre-registration.
    """

    query_tokens: tuple[str, ...]
    refs_searched: int
    hits: tuple[PriorArt, ...] = field(default_factory=tuple)
    skipped_reason: str = ""

    @property
    def ran(self) -> bool:
        # A name with no distinctive words produces no search at all. The
        # renderer said DID NOT RUN while this property said it had --
        # the label disagreeing with the predicate, inside the module
        # built to catch exactly that. Caught by its own test.
        return not self.skipped_reason and bool(self.query_tokens)

    def render(self) -> str:
        if self.skipped_reason:
            return f"[prior-art] DID NOT RUN — {self.skipped_reason}"
        if not self.query_tokens:
            return (
                "[prior-art] DID NOT RUN — the name had no distinctive words to "
                "search on, so no search happened. This is not a clean result."
            )
        if not self.hits:
            return (
                f"[prior-art] searched {self.refs_searched} branch(es) for names "
                f"containing {', '.join(self.query_tokens)} — nothing similar. "
                "This matches NAMES only; prior work under a different name is "
                "invisible here."
            )
        shown = self.hits[:_SHOW_LIMIT]
        lines = [
            f"[prior-art] {len(self.hits)} similarly-named file(s) across "
            f"{self.refs_searched} branch(es). You may have built this already:"
        ]
        for h in shown:
            where = ", ".join(h.refs[:3]) + ("..." if len(h.refs) > 3 else "")
            lines.append(f"    {h.path}")
            lines.append(f"        on {where}  (shares: {', '.join(h.shared_tokens)})")
        # NO SILENT CAPS (Aether 2026-08-27). A truncated list that does
        # not say it was truncated reads as "this is everything", which
        # is the same lie by omission this module exists to prevent.
        if len(self.hits) > _SHOW_LIMIT:
            lines.append(
                f"    ...and {len(self.hits) - _SHOW_LIMIT} more, hidden by a "
                f"display cap of {_SHOW_LIMIT}, ranked by how many words they share."
            )
        lines.append("    Matched on names only — read them before writing a new one.")
        return "\n".join(lines)


def tokens_of(path: str) -> tuple[str, ...]:
    """Distinctive words in a path, for matching one name against another.

    Splits on every separator a filename uses here — slashes, dots,
    underscores, hyphens, and camel-case humps — then drops the words
    that appear everywhere. A token list of nothing is reported as a
    non-run rather than as a clean result.
    """
    stem = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(path))
    raw = re.split(r"[/\\._\-]+", stem.lower())
    kept = {w for w in raw if len(w) >= _MIN_TOKEN and w not in _STOPWORDS}
    # SINGULARISE, because the first real run failed its own success
    # criterion on one letter. The pre-registration named
    # family/aletheia/letters_seen.json as the file that must surface,
    # and it did not: "letters" and "letter" shared nothing, so the
    # store I actually duplicated stayed invisible while its driver
    # script showed up and made the run look successful.
    #
    # Naive trailing-s stripping is wrong for words like "class" and
    # "status", so it only applies where the singular is still a real
    # token by this module's own length rule.
    return tuple(
        sorted(
            {
                w[:-1]
                if (w.endswith("s") and not w.endswith("ss") and len(w) - 1 >= _MIN_TOKEN)
                else w
                for w in kept
            }
        )
    )


_CODE_SUFFIXES = frozenset({".py", ".sh", ".ps1", ".js", ".ts", ".sql"})
_DATA_SUFFIXES = frozenset({".json", ".jsonl", ".yaml", ".yml", ".toml", ".txt", ".csv"})


def _kind_of(path: str) -> str:
    """Code, data, or prose — the three things a name can be an earlier build of.

    Data sits with code rather than with prose because a store and the
    module that writes it are the same piece of work under two names,
    which is exactly the pair that got duplicated.
    """
    suffix = Path(path).suffix.lower()
    if suffix in _CODE_SUFFIXES or suffix in _DATA_SUFFIXES:
        return "build"
    return "prose"


def _all_refs(repo_root: Path) -> list[str]:
    """Every branch in the repo AT ``repo_root`` — not whichever repo encloses it.

    git walks upward looking for a repository, so pointing this at a
    plain directory silently answered about the enclosing checkout
    instead. In a test that gave 371 branches for a folder that had
    none: a real search, correctly executed, about somewhere else. The
    wrong-subject fault, in the module written to prevent building the
    wrong thing twice. Its own test caught it.
    """
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if top.returncode != 0:
        return []
    try:
        if Path(top.stdout.strip()).resolve() != Path(repo_root).resolve():
            return []
    except OSError:
        return []

    proc = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []
    return [r for r in proc.stdout.splitlines() if r and "HEAD" not in r]


def scan(
    new_path: str,
    repo_root: Path,
    min_shared: int = 2,
) -> ScanResult:
    """Names across every ref that share at least ``min_shared`` words.

    Every ref, not the current checkout. The duplicate that produced this
    module was on a branch I was not standing on, so a search of the
    working tree would have returned empty and confirmed the mistake.
    """
    query = tokens_of(new_path)
    refs = _all_refs(repo_root)

    if not refs:
        return ScanResult(query, 0, skipped_reason="no git refs readable from here")
    if not query:
        return ScanResult(query, len(refs))

    # One token is too loose -- "letter" alone returns the whole channel.
    # Two shared distinctive words is the floor for a name being ABOUT the
    # same thing rather than merely nearby.
    seen: dict[str, tuple[set[str], tuple[str, ...]]] = {}
    for ref in refs:
        proc = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", ref],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            continue
        for path in proc.stdout.splitlines():
            if not path or path == new_path:
                continue
            # KIND MUST MATCH, and this is a real narrowing rather than a
            # convenience. The first run against the duplicate returned
            # forty-two hits, nearly all of them letters between Aether
            # and me that happen to contain the words "letter", "state"
            # and "channel" -- and the one piece of prior CODE sank
            # below the display cap. Prior art for a module is a module.
            # Correspondence about a subject is not an earlier build of
            # it, and letting it compete for the same slots is how a
            # scanner drowns its own signal.
            if _kind_of(path) != _kind_of(new_path):
                continue
            shared = tuple(sorted(set(tokens_of(path)) & set(query)))
            if len(shared) < min_shared:
                continue
            if path in seen:
                seen[path][0].add(ref)
            else:
                seen[path] = ({ref}, shared)

    hits = tuple(
        PriorArt(path=p, refs=tuple(sorted(r)), shared_tokens=s)
        for p, (r, s) in sorted(seen.items(), key=lambda kv: -len(kv[1][1]))
    )
    return ScanResult(query, len(refs), hits)


def main() -> int:
    """Hook entry point: reads a PreToolUse payload, prints any prior art.

    A MODULE RATHER THAN A HEREDOC, and that is the whole reason this
    exists. The first version of the doorman piped the payload into
    ``python - <<EOF``, which feeds the SCRIPT through stdin and leaves
    nothing for the program to read. It failed on every invocation,
    caught its own exception, and exited clean — a broken doorman
    indistinguishable from one with nothing to report, which is the
    exact shape a guard for silent duplication must not have.

    It survived only because the hook itself was fired in a test rather
    than only the function underneath it.

    Returns 2 when there is prior art to read, 0 otherwise.
    """
    import json
    import sys

    try:
        data = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - hook boundary, must not block writing
        return 0

    if data.get("tool_name") != "Write":
        return 0
    raw = (data.get("tool_input") or {}).get("file_path") or ""
    if not raw:
        return 0

    repo = Path.cwd()
    try:
        rel = Path(raw).resolve().relative_to(repo.resolve()).as_posix()
    except Exception:  # noqa: BLE001 - outside the repo is not our business
        return 0

    # Only a file that does not exist yet. Editing something is not
    # rebuilding it. Only build directories -- a new letter is the
    # substrate doing its job, not a duplication risk.
    if (repo / rel).exists():
        return 0
    if not rel.startswith(("src/", "scripts/", "tests/", ".claude/hooks/")):
        return 0

    result = scan(rel, repo)

    # COULD-NOT-LOOK IS NOT LOOKED-AND-FOUND-NOTHING, and until 2026-08-29
    # this entry point could not tell you which it was. The old line was
    # `if not result.hits: return 0` -- and a scan that never ran has no
    # hits, so a skip returned zero, printed nothing, and the wrapper (which
    # keys on whether anything was printed) exited clean. Byte-identical to
    # a clean result at the only surface that ever reaches me.
    #
    # The renderer has carried honest non-run text this whole time -- no git
    # refs readable from here, the name had no distinctive words -- and it
    # was unreachable from the live path. Exercised only by the tests, which
    # is exactly what made it look present. Found by Aether, reviewing this
    # module, and it is the module's own thesis turned on itself: an
    # instrument that cannot say it failed to look.
    #
    # FAIL-OPEN IS RIGHT AND WAS NEVER THE PROBLEM. A broken doorman must
    # not stop the work. But fail-open and fail-SILENT got welded together,
    # and they are separable: exit zero and still say so. Three codes now,
    # so the wrapper can tell the three states apart.
    if not result.ran:
        print(result.render())
        return _EXIT_COULD_NOT_LOOK
    if not result.hits:
        return _EXIT_NOTHING_FOUND
    print(result.render())
    return _EXIT_PRIOR_ART


if __name__ == "__main__":
    raise SystemExit(main())
