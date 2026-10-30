"""Building edits on a branch are free; the covering walk is judged at the stamp.

Dad, 2026-07-30, 2026-10-07 and 2026-10-12: the full paperwork on every single change is
brutal; make the changes, then do one walk over all of them before the REAL push. And on
2026-10-12: "a push means an actual push (like before the merge) not a draft; drafts you can
push even if it doesnt meet the standard as you may need Aletheia's help and she needs to be
able to see it". So nothing here refuses a draft push, and the stamp (station six) is where
a walk bound to an old diff is called stale.

These tests use a REAL temporary git repository and the real walk store, never mocks of the
thing under test. The design is
docs/drafts/one_walk_before_the_push_not_one_per_edit_draft_2026-10-12.md.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.cli.build_flow_commands import _walk_postdates_build
from divineos.core import council_walk as cw
from divineos.core.council_required import push_choke as pc

from _walk_helpers import apply_delivered


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A repository on a feature branch, with origin/main one commit behind it."""
    r = tmp_path / "work"
    r.mkdir()
    _git(r, "init", "-q", "--initial-branch=main")
    (r / "base.txt").write_text("base\n", encoding="utf-8")
    _git(r, "add", ".")
    _git(r, "commit", "-qm", "base")
    _git(r, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(r, "switch", "-qc", "feature")
    return r


def _commit(repo: Path, name: str, text: str = "x\n") -> None:
    (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-qm", f"add {name}")


def _closed_walk(repo: Path, scope: tuple[str, ...]) -> str:
    opened = cw.open_walk(
        "does this change hold across every file it touches", scope=scope, gravity="normal"
    )
    for lens in opened["lenses"]:
        apply_delivered(
            cw, opened["walk_id"], lens, "a finding that is long enough to count: " + lens
        )
    cw.close_walk(opened["walk_id"], repo=repo)
    return opened["walk_id"]


PUSH = "git push -u origin feature"


def test_control_the_push_detector_sees_every_spelling_of_a_push():
    """CONTROL: the tests below mean nothing if the detector cannot see a push."""
    for command in (
        "git push",
        "git push -u origin feature",
        "git -C C:/w push origin feature",
        "bash scripts/divineos_push.sh -u origin feature",
        "cd C:/w && git push origin x",
    ):
        assert pc.is_push_command(command) is True, command
    for command in ("git status", "git log --oneline", "echo git push", "git pushx"):
        assert pc.is_push_command(command) is False, command


def test_an_unparsable_line_that_mentions_a_push_is_judged_as_one():
    assert pc.is_push_command("git push $(echo origin) feature") is True


def test_a_draft_push_is_never_refused_even_with_no_walk(repo):
    """Dad, 2026-10-12: drafts are pushed even when they do not meet the standard, because
    Aletheia may be needed and has to be able to see the work."""
    _commit(repo, "a.py")
    rule = pc.branch_rule(repo, "Bash", PUSH, (), "bash:git push")
    assert rule.handled is False  # nothing here stops it; the old gate does not gate pushes


def test_a_push_on_main_is_left_to_the_old_rules(repo):
    _git(repo, "switch", "-q", "main")
    assert (
        pc.branch_rule(repo, "Bash", "git push origin main", (), "bash:git push").handled is False
    )


def test_the_target_folder_is_read_from_the_call_not_the_hook(repo, tmp_path):
    other = tmp_path / "elsewhere"
    other.mkdir()
    sub = repo / "sub"
    sub.mkdir()
    assert pc.target_dir((str(repo / "new" / "deep.py"),), "", other) == repo
    # Forward slashes, as the shell here is given. Backslashes survive the tokenizer now
    # (posix=False); the one stated limit is an UNQUOTED folder with a space in its name,
    # which lands on None, the strict direction. Quoting is the contract.
    # Quoted, as a real shell needs when the path has a space (both real checkouts live
    # under "C:/DIVINE OS/"; Aria found this test passing only where the path had none).
    here = f'"{repo.as_posix()}"'
    assert pc.target_dir((), f"cd {here} && git commit -qm x", other) == repo
    assert pc.target_dir((), f"git -C {here} commit -qm x", other) == repo
    assert pc.target_dir((), f"cd {here} && cd sub && git commit -qm x", other) == sub
    assert pc.target_dir((), f"cd {repo} && git commit -qm x", other) in (None, repo)
    assert pc.target_dir((), "git commit -qm x", other) == other
    assert pc.target_dir((), "cd /does/not/exist/anywhere && git commit -qm x", other) is None


def _passthrough_lines():
    from divineos.core.paths import divineos_home

    path = divineos_home() / "branch_edit_passthrough.log"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_a_building_edit_on_a_branch_is_free_and_leaves_one_line(repo):
    rule = pc.branch_rule(repo, "Edit", "", ("edit-src-divineos",), "edit:src/x.py")
    assert rule.handled is True and rule.exit_code == 0
    assert any("edit:src/x.py" in line for line in _passthrough_lines())


def test_a_commit_on_a_branch_is_free_too(repo):
    rule = pc.branch_rule(repo, "Bash", "git commit -qm x", ("git-commit",), "bash:git commit")
    assert rule.handled is True and rule.exit_code == 0


def test_a_substrate_write_on_a_branch_goes_back_to_the_old_strict_gate(repo):
    """The cheap attack: dress a substrate write as branch work. It must not be freed."""
    for features in (
        ("substrate-write-cli",),
        ("consolidation-cli",),
        ("edit-kiln-layer",),
        ("edit-src-divineos", "edit-kiln-layer"),
    ):
        assert pc.branch_rule(repo, "Bash", "x", features, "bash:x").handled is False, features


def test_an_edit_on_main_is_not_freed(repo):
    _git(repo, "switch", "-q", "main")
    rule = pc.branch_rule(repo, "Edit", "", ("edit-src-divineos",), "edit:src/x.py")
    assert rule.handled is False


def test_a_detached_head_counts_as_not_main(repo):
    _git(repo, "checkout", "-q", "--detach")
    assert pc.on_main(repo) is False


def test_an_unreadable_branch_is_not_freed(tmp_path, monkeypatch):
    nowhere = tmp_path / "nowhere"
    nowhere.mkdir()
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    rule = pc.branch_rule(nowhere, "Edit", "", ("edit-src-divineos",), "edit:src/x.py")
    assert rule.handled is False


HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "check-council-required.sh"


def _run_the_hook(repo: Path, tmp_path: Path, tool: str, tool_input: dict) -> tuple[int, str]:
    """Run the hook's real Python program (extracted, never copied) the way the harness does."""
    import json
    import os
    import sys

    text = HOOK.read_text(encoding="utf-8")
    opener = 'echo "$INPUT" | "$PYTHON_BIN" -c "\n'
    start = text.index(opener) + len(opener)
    program = text[start : text.index('\n"\n', start)]
    env = dict(os.environ)
    # The isolated home and ledger this test run already set (conftest) are inherited on
    # purpose: the walk a test closes lives there, and the hook must read the same store.
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    proc = subprocess.run(
        [sys.executable, "-c", program],
        input=json.dumps({"tool_name": tool, "tool_input": tool_input}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=tmp_path,
        env=env,
    )
    return proc.returncode, proc.stderr


def test_the_hook_frees_a_source_edit_on_a_branch(repo, tmp_path):
    target = repo / "src" / "divineos" / "thing.py"
    code, err = _run_the_hook(repo, tmp_path, "Edit", {"file_path": str(target)})
    assert code == 0, err


def test_control_the_hook_still_refuses_the_same_edit_on_main(repo, tmp_path):
    """CONTROL: the free pass above means nothing if the hook refuses nothing."""
    _git(repo, "switch", "-q", "main")
    target = repo / "src" / "divineos" / "thing.py"
    code, err = _run_the_hook(repo, tmp_path, "Edit", {"file_path": str(target)})
    assert code == 2, err


def test_the_hook_never_refuses_a_draft_push_even_with_no_walk(repo, tmp_path):
    _commit(repo, "a.py")
    command = f"cd {repo.as_posix()} && git push -u origin feature"
    code, err = _run_the_hook(repo, tmp_path, "Bash", {"command": command})
    assert code == 0, err


def test_the_hook_does_not_free_a_substrate_write_on_a_branch(repo, tmp_path):
    code, err = _run_the_hook(
        repo,
        tmp_path,
        "Bash",
        # not `prereg file` or `learn`: those are filing commands the build gate exempts
        {"command": f"cd {repo.as_posix()} && divineos claim 'a statement' --tier 3"},
    )
    assert code == 2, err


# --- the walk binds to the diff it covered, and amendments are a total -------------------


def test_closing_from_the_right_folder_says_it_bound(repo):
    _commit(repo, "a.py")
    opened = cw.open_walk("does this change hold across every file it touches", scope=("a.py",))
    for lens in opened["lenses"]:
        apply_delivered(
            cw, opened["walk_id"], lens, "a finding that is long enough to count: " + lens
        )
    result = cw.close_walk(opened["walk_id"], repo=repo)
    assert result["bound"] is True
    assert Path(result["bound_in"]) == repo


def test_a_walk_closed_in_the_wrong_folder_is_not_tied_to_that_folders_changes(tmp_path):
    """Aria's strong suggestion: the shell resets to the main checkout, so a walk closed there
    used to be bound to that folder's UNRELATED diff. Now it stays unbound and says so."""

    def _make(name: str, filename: str) -> Path:
        r = tmp_path / name
        r.mkdir()
        _git(r, "init", "-q", "--initial-branch=main")
        (r / "base.txt").write_text("base\n", encoding="utf-8")
        _git(r, "add", ".")
        _git(r, "commit", "-qm", "base")
        _git(r, "update-ref", "refs/remotes/origin/main", "HEAD")
        _git(r, "switch", "-qc", "feature")
        _commit(r, filename)
        return r

    work = _make("work", "a.py")
    elsewhere = _make("elsewhere", "unrelated.py")
    opened = cw.open_walk("does this change hold across every file it touches", scope=("a.py",))
    for lens in opened["lenses"]:
        apply_delivered(
            cw, opened["walk_id"], lens, "a finding that is long enough to count: " + lens
        )
    wrong = cw.close_walk(opened["walk_id"], repo=elsewhere)
    assert wrong["bound"] is False
    assert Path(wrong["bound_in"]) == elsewhere
    # and it cannot be amended from anywhere: it has no fixed origin to measure from
    with pytest.raises(cw.WalkRefused, match="walked head"):
        cw.amend_walk(
            opened["walk_id"], "a long enough sentence about what changed here", repo=work
        )


def test_a_small_follow_up_is_amended_not_rewalked(repo):
    _commit(repo, "a.py", "one\n")
    walk = _closed_walk(repo, ("a.py",))
    (repo / "a.py").write_text("one\ntwo\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-qm", "small follow-up")
    before = pc.diff_identity(repo)
    result = cw.amend_walk(
        walk, "added one line a reviewer asked for; no behaviour change", repo=repo
    )
    assert result["lines_changed"] == 1
    assert cw.coverage_for(("a.py",)).bound_diff == pc.diff_identity(repo) != ""
    assert before == pc.diff_identity(repo)


def test_an_amendment_cannot_swallow_a_large_or_wider_change(repo):
    _commit(repo, "a.py", "one\n")
    walk = _closed_walk(repo, ("a.py",))
    (repo / "a.py").write_text("\n".join(str(i) for i in range(80)) + "\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-qm", "big")
    with pytest.raises(cw.WalkRefused, match="lines"):
        cw.amend_walk(walk, "this is long enough to be a finding but the change is big", repo=repo)
    _commit(repo, "c.py")
    with pytest.raises(cw.WalkRefused):
        cw.amend_walk(walk, "this is long enough to be a finding but a new file arrived", repo=repo)


def test_amendments_add_up_from_the_original_walk_not_from_the_last_one(repo):
    """Aria's hold: three 25-line steps are each under the 30-line cap, and together they
    are 75 lines nobody walked. The cap is a TOTAL measured from where the walk closed."""
    _commit(repo, "a.py", "start\n")
    walk = _closed_walk(repo, ("a.py",))
    body = "start\n"
    for step in range(3):
        body += "".join(f"step{step} line {i}\n" for i in range(25))
        (repo / "a.py").write_text(body, encoding="utf-8")
        _git(repo, "add", "a.py")
        _git(repo, "commit", "-qm", f"step {step}")
        if step == 0:
            cw.amend_walk(
                walk, "twenty five lines of a reviewer's follow-up, no behaviour change", repo=repo
            )
        else:
            with pytest.raises(cw.WalkRefused, match="lines"):
                cw.amend_walk(
                    walk, "another twenty five lines that together are far too many", repo=repo
                )
            break


def test_an_amendment_needs_a_real_finding(repo):
    _commit(repo, "a.py", "one\n")
    walk = _closed_walk(repo, ("a.py",))
    (repo / "a.py").write_text("one\ntwo\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-qm", "small")
    with pytest.raises(cw.WalkRefused, match="finding"):
        cw.amend_walk(walk, "ok", repo=repo)


# --- the stamp (station six) is where a stale walk is called stale ------------------------


def test_the_stamp_calls_a_walk_stale_when_the_branch_changed_after_it(repo, monkeypatch):
    _commit(repo, "a.py")
    _closed_walk(repo, ("a.py",))
    monkeypatch.chdir(repo)
    coverage = cw.coverage_for(("a.py",))
    assert _walk_postdates_build("feature", coverage) is True  # CONTROL: fresh right after
    (repo / "a.py").write_text("changed after the walk\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-qm", "later")
    assert _walk_postdates_build("feature", coverage) is False


def test_main_arriving_in_the_branch_does_not_make_the_walk_stale_at_the_stamp(repo, monkeypatch):
    """Aria's catch-up merge: main moves under every push. By the clock rule that merge is a
    commit after the walk and the stamp refused clean branches; by identity it is nothing."""
    _commit(repo, "a.py")
    _closed_walk(repo, ("a.py",))
    monkeypatch.chdir(repo)
    coverage = cw.coverage_for(("a.py",))
    _git(repo, "switch", "-q", "main")
    (repo / "other.txt").write_text("someone else's work\n", encoding="utf-8")
    _git(repo, "add", "other.txt")
    _git(repo, "commit", "-qm", "main moves")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "switch", "-q", "feature")
    _git(repo, "merge", "-q", "--no-edit", "origin/main")
    assert _walk_postdates_build("feature", coverage) is True


def test_an_unreadable_branch_is_could_not_check_at_the_stamp_never_fresh(repo, monkeypatch):
    _commit(repo, "a.py")
    _closed_walk(repo, ("a.py",))
    monkeypatch.chdir(repo)
    coverage = cw.coverage_for(("a.py",))
    assert _walk_postdates_build("no-such-branch", coverage) is None
