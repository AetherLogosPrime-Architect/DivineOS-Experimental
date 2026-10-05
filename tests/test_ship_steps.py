"""The two checks ship refuses on, each driven by a planted case it must catch.

confirm_in: only Aletheia's own CONFIRMS title for THIS pr at THIS head, and
only when her letter in the letters folder carries the same line (her caution,
2026-10-02: "a quoted confirm isn't a confirm").

floor_proven: a head counts as floor-only only when its tree equals the
three-way merge of the confirmed commit and main, proven in a real repository.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from divineos.core.ship_steps import confirm_in, floor_proven

HEAD = "9a02f835395f9b6298dba85e1f76f92d7338d1c1"
LETTER = "aletheia-to-aether-2026-10-02-four-confirmed.md"


@dataclass
class F:
    round_id: str
    actor: str
    title: str
    description: str


@pytest.fixture
def letters(tmp_path: Path) -> Path:
    d = tmp_path / "letters"
    d.mkdir()
    (d / LETTER).write_text(
        SIGNED.format(verb="CONFIRMS", pr=578, sha="9a02f8353"), encoding="utf-8"
    )
    return d


# Her real signed shape, as written in every confirm in family/letters.
SIGNED = "> {verb}: #{pr} at {sha}. — Aletheia Sophia Risner, 2026-10-03\n"


def _finding(**kw) -> F:
    base = dict(
        round_id="round-aaaaaaaaaaaa",
        actor="aletheia",
        title="CONFIRMS: #578 at 9a02f8353.",
        description=f"Transcribed verbatim from Aletheia's letter {LETTER}.",
    )
    base.update(kw)
    return F(**base)


def test_her_own_confirm_at_this_head_counts(letters):
    v = confirm_in([_finding()], 578, HEAD, letters)
    assert v.ok and v.confirm.letter == LETTER


def test_a_confirm_for_another_pr_is_never_offered(letters):
    v = confirm_in([_finding(title="CONFIRMS: #579 at 9a02f8353.")], 578, HEAD, letters)
    assert not v.ok and "#579" not in v.reason


def test_a_confirm_at_an_older_head_does_not_count(letters):
    v = confirm_in([_finding(title="CONFIRMS: #578 at 91fc4a310.")], 578, HEAD, letters)
    assert not v.ok


def test_a_finding_typed_as_someone_else_does_not_count(letters):
    v = confirm_in([_finding(actor="aether")], 578, HEAD, letters)
    assert not v.ok


def test_a_finding_whose_letter_lacks_the_line_is_refused(letters):
    (letters / LETTER).write_text("I have not read #578 yet.\n", encoding="utf-8")
    v = confirm_in([_finding()], 578, HEAD, letters)
    assert not v.ok and "no letter of hers" in v.reason


def test_a_confirm_quoted_in_someone_elses_letter_does_not_count(letters):
    quoted = "aether-to-aletheia-2026-10-02-relay.md"
    (letters / quoted).write_text("> CONFIRMS: #578 at 9a02f8353.\n", encoding="utf-8")
    v = confirm_in([_finding(description=f"from {quoted}")], 578, HEAD, letters)
    assert not v.ok


def test_a_confirm_she_withdrew_does_not_count(letters):
    # Aletheia 2026-10-03: a letter withdrawing #554 and quoting the old line
    # returned True. Her withdrawal, in any of her letters, wins.
    (letters / "aletheia-to-aether-2026-10-04-withdrawn.md").write_text(
        "My confirm below is WITHDRAWN; it read:\n"
        "CONFIRMS: #578 at 9a02f8353.\n" + SIGNED.format(verb="WITHDRAWN", pr=578, sha="9a02f8353"),
        encoding="utf-8",
    )
    v = confirm_in([_finding()], 578, HEAD, letters)
    assert not v.ok and "withdraws" in v.reason


def test_a_withdrawal_of_another_pr_or_head_does_not_touch_this_one(letters):
    (letters / "aletheia-to-aether-2026-10-04-other.md").write_text(
        SIGNED.format(verb="WITHDRAWN", pr=579, sha="9a02f8353")
        + SIGNED.format(verb="WITHDRAWN", pr=578, sha="91fc4a310"),
        encoding="utf-8",
    )
    assert confirm_in([_finding()], 578, HEAD, letters).ok


def test_a_quoted_line_without_her_signature_does_not_count(letters):
    (letters / LETTER).write_text(
        "You asked about this one; the old line was\n> CONFIRMS: #578 at 9a02f8353.\n",
        encoding="utf-8",
    )
    assert not confirm_in([_finding()], 578, HEAD, letters).ok


def test_every_matching_line_is_read_not_only_the_first(letters):
    # Her #560 case: an old head confirmed first, the new head below it.
    (letters / LETTER).write_text(
        SIGNED.format(verb="CONFIRMS", pr=578, sha="1776a8816")
        + SIGNED.format(verb="CONFIRMS", pr=578, sha="9a02f8353"),
        encoding="utf-8",
    )
    assert confirm_in([_finding()], 578, HEAD, letters).ok


def test_every_real_confirm_she_has_written_still_reads():
    from divineos.core.ship_steps import _signed_heads

    real = Path(__file__).resolve().parents[1] / "family" / "letters"
    lines = [
        ln
        for f in sorted(real.glob("aletheia-to-*.md"))
        for ln in f.read_text(encoding="utf-8").splitlines()
        if ln.startswith("> CONFIRMS: #")
    ]
    if not lines:
        pytest.skip("no letters of hers in this checkout")
    for ln in lines:
        pr = int(re.match(r"> CONFIRMS: #(\d+)", ln).group(1))
        assert _signed_heads(ln, "CONFIRMS", pr), ln


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "a.txt").write_text("base\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "base")
    _git(r, "checkout", "-q", "-b", "pr")
    (r / "pr.txt").write_text("the reviewed change\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "reviewed")
    _git(r, "checkout", "-q", "main")
    (r / "main.txt").write_text("main moved\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "main moved")
    _git(r, "update-ref", "refs/remotes/origin/main", "main")
    _git(r, "checkout", "-q", "pr")
    return r


def test_the_confirmed_head_itself_is_floor(repo):
    assert floor_proven(repo, "pr", "pr").ok


def test_a_clean_catch_up_is_floor(repo):
    confirmed = _git(repo, "rev-parse", "pr")
    _git(repo, "merge", "-q", "--no-edit", "main")
    v = floor_proven(repo, confirmed, "HEAD")
    assert v.ok, v.reason


def test_a_regenerated_register_is_tolerated(repo):
    confirmed = _git(repo, "rev-parse", "pr")
    _git(repo, "merge", "-q", "--no-edit", "--no-commit", "main")
    (repo / "docs").mkdir()
    (repo / "docs" / "AUTOMATION_REGISTER.md").write_text("regenerated\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "merge + register")
    assert floor_proven(repo, confirmed, "HEAD").ok


def test_one_authored_line_in_the_catch_up_is_refused(repo):
    confirmed = _git(repo, "rev-parse", "pr")
    _git(repo, "merge", "-q", "--no-edit", "--no-commit", "main")
    (repo / "pr.txt").write_text("the reviewed change, quietly edited\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "merge + a sneaked edit")
    v = floor_proven(repo, confirmed, "HEAD")
    assert not v.ok and "pr.txt" in v.reason


def test_a_half_done_merge_is_refused_not_judged(repo):
    # Aletheia 2026-10-02: mid-merge it answered "head is the confirmed commit".
    confirmed = _git(repo, "rev-parse", "pr")
    _git(repo, "merge", "-q", "--no-edit", "--no-commit", "main")
    v = floor_proven(repo, confirmed, "HEAD")
    assert not v.ok and "MERGE_HEAD" in v.reason


def test_a_half_done_merge_in_a_worktree_is_refused_too(repo, tmp_path):
    # In a worktree .git is a pointer file, so a fixed repo/".git" path is blind.
    wt = tmp_path / "wt"
    _git(repo, "worktree", "add", "-q", "--detach", str(wt), "pr")
    confirmed = _git(wt, "rev-parse", "HEAD")
    _git(wt, "merge", "-q", "--no-edit", "--no-commit", "main")
    v = floor_proven(wt, confirmed, "HEAD")
    assert not v.ok and "MERGE_HEAD" in v.reason


def test_an_uncommitted_edit_is_refused_not_judged(repo):
    confirmed = _git(repo, "rev-parse", "pr")
    (repo / "pr.txt").write_text("edited but not committed\n")
    v = floor_proven(repo, confirmed, "HEAD")
    assert not v.ok and "uncommitted" in v.reason


def test_a_merge_of_a_branch_that_is_not_main_is_refused(repo):
    # Aria's cold read, 2026-10-04: the tree check agrees with any honest merge,
    # so a scratch branch merged in passed as a catch-up with main.
    confirmed = _git(repo, "rev-parse", "pr")
    _git(repo, "checkout", "-q", "-b", "scratch", "main")
    (repo / "scratch.txt").write_text("never reviewed\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "unreviewed")
    _git(repo, "checkout", "-q", "pr")
    _git(repo, "merge", "-q", "--no-edit", "scratch")
    v = floor_proven(repo, confirmed, "HEAD")
    assert not v.ok and "not on main" in v.reason


def test_a_commit_on_top_of_the_confirm_is_refused(repo):
    confirmed = _git(repo, "rev-parse", "pr")
    (repo / "pr.txt").write_text("changed after review\n")
    _git(repo, "commit", "-q", "-am", "after review")
    assert not floor_proven(repo, confirmed, "HEAD").ok
