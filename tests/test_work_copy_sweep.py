"""Finished work copies are removed by themselves; anything doubtful is listed and never touched.

Dad, 2026-10-20, after about ninety of my old work copies were found in his C drive:
"nothing to prevent you being an AI slob ... we need to automate it so when something is done and no
longer needed it gets deleted". His yes to the shape: the sweeper removes the clearly finished ones and
shows him the doubtful ones. Walked as walk-91a1bab8430a; pre-registered as prereg-64b58b46e1bc.

Real git throughout (a bare remote, a main checkout, linked work copies in each state); only the pull
request lookup is injected, because it needs the network. The tests that matter most are the ones that
KEEP a copy: every one of them is a case where a cheap signal says finished and exactly one thing says no.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from divineos.core import work_copy_sweep as ws

LONG_AGO = 10 * 3600  # seconds added to "now" so a freshly made copy is not "recent"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """A sweep inside a test run may never write the real home's log; every test gets its own."""
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "home"))


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _must(cwd: Path, *args: str) -> str:
    done = _git(cwd, *args)
    assert done.returncode == 0, f"git {' '.join(args)}: {done.stderr}"
    return done.stdout.strip()


@pytest.fixture
def world(tmp_path):
    """A bare remote, a main checkout with one pushed commit, and a helper that makes work copies."""
    remote = tmp_path / "remote.git"
    remote.mkdir()
    _must(remote, "init", "-q", "--bare", "-b", "main")
    main = tmp_path / "main"
    main.mkdir()
    _must(main, "init", "-q", "-b", "main")
    _must(main, "config", "user.email", "t@example.invalid")
    _must(main, "config", "user.name", "t")
    (main / ".gitignore").write_text("ignored_data/\ntmp/\n.venv\n", encoding="utf-8")
    (main / "a.txt").write_text("a\n", encoding="utf-8")
    _must(main, "add", "-A")
    _must(main, "commit", "-q", "-m", "first")
    _must(main, "remote", "add", "origin", str(remote))
    _must(main, "push", "-q", "-u", "origin", "main")

    class World:
        pass

    w = World()
    w.root, w.main, w.remote, w.n = tmp_path, main, remote, 0
    w.prs = {}  # branch -> (state, head_oid) or None, what the host would say

    def copy(branch="feat", *, commits=0, push=False, detached=False, merged_into_main=False):
        w.n += 1
        name = f"{branch}{w.n}"
        wt = tmp_path / f"copy_{name}"
        _must(main, "worktree", "add", "-q", "-b", name, str(wt), "main")
        for i in range(commits):
            (wt / f"{name}_f{i}.txt").write_text(f"{i}\n", encoding="utf-8")
            _must(wt, "add", "-A")
            _must(
                wt,
                "-c",
                "user.email=t@example.invalid",
                "-c",
                "user.name=t",
                "commit",
                "-q",
                "-m",
                f"c{i}",
            )
        if push:
            _must(wt, "push", "-q", "origin", name)
        if merged_into_main:
            _must(main, "merge", "-q", "--ff-only", name)
            _must(main, "push", "-q", "origin", "main")
        if detached:
            _must(wt, "checkout", "-q", "--detach")
        return wt, name

    w.copy = copy
    w.pr = lambda branch: w.prs.get(branch)
    w.assess = lambda wt, **kw: ws.assess(
        main, wt, pr_info=w.pr, now=kw.pop("now", __import__("time").time() + LONG_AGO), **kw
    )
    return w


def _verdict(world, wt, **kw):
    return world.assess(wt, **kw)[0]


def test_a_copy_whose_pull_request_merged_and_holds_nothing_else_is_removable(world):
    wt, name = world.copy(commits=1, push=True)
    head = _must(wt, "rev-parse", "HEAD")
    world.prs[name] = ("MERGED", head)
    assert _verdict(world, wt) == ws.Verdict.REMOVE


def test_a_branch_already_in_main_is_finished_without_asking_the_host(world):
    wt, name = world.copy(commits=1, push=True, merged_into_main=True)
    assert _verdict(world, wt) == ws.Verdict.REMOVE


def test_an_open_pull_request_is_not_finished(world):
    wt, name = world.copy(commits=1, push=True)
    world.prs[name] = ("OPEN", _must(wt, "rev-parse", "HEAD"))
    assert _verdict(world, wt) == ws.Verdict.SHOW


def test_a_host_that_could_not_be_read_is_never_finished(world):
    wt, name = world.copy(
        commits=1, push=True
    )  # world.prs has no entry: the lookup returned nothing
    assert _verdict(world, wt) == ws.Verdict.SHOW


def test_a_lookup_that_raises_is_doubt_not_a_crash_and_not_finished(world):
    wt, name = world.copy(commits=1, push=True)

    def boom(branch):
        raise RuntimeError("gh is down")

    verdict, state, reasons = ws.assess(
        world.main, wt, pr_info=boom, now=__import__("time").time() + LONG_AGO
    )
    assert verdict == ws.Verdict.SHOW
    assert any("gh is down" in r for r in reasons)


def test_a_merged_copy_with_an_untracked_file_is_kept(world):
    wt, name = world.copy(commits=1, push=True)
    world.prs[name] = ("MERGED", _must(wt, "rev-parse", "HEAD"))
    (wt / "unsaved.md").write_text("only here\n", encoding="utf-8")
    verdict, state, reasons = world.assess(wt)
    assert verdict == ws.Verdict.SHOW
    assert any("unsaved.md" in r for r in reasons)


def test_an_ignored_file_outside_the_regenerable_set_is_work_that_exists_only_here(world):
    wt, name = world.copy(commits=1, push=True)
    world.prs[name] = ("MERGED", _must(wt, "rev-parse", "HEAD"))
    (wt / "ignored_data").mkdir()
    (wt / "ignored_data" / "local.db").write_text("rows\n", encoding="utf-8")
    verdict, state, reasons = world.assess(wt)
    assert verdict == ws.Verdict.SHOW
    assert any("ignored_data" in r for r in reasons)


def test_ignored_regenerable_scratch_does_not_keep_a_finished_copy(world):
    wt, name = world.copy(commits=1, push=True)
    world.prs[name] = ("MERGED", _must(wt, "rev-parse", "HEAD"))
    (wt / "tmp").mkdir()
    (wt / "tmp" / "scratch.txt").write_text("x\n", encoding="utf-8")
    assert _verdict(world, wt) == ws.Verdict.REMOVE


def test_a_landed_branch_with_a_local_commit_no_remote_has_is_kept(world):
    wt, name = world.copy(commits=1, push=True)
    world.prs[name] = ("MERGED", _must(wt, "rev-parse", "HEAD"))
    (wt / "after.txt").write_text("after the merge\n", encoding="utf-8")
    _must(wt, "add", "-A")
    _must(
        wt, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-q", "-m", "late"
    )
    verdict, state, reasons = world.assess(wt)
    assert verdict == ws.Verdict.SHOW
    assert any("no remote" in r or "not published" in r for r in reasons)


def test_a_detached_copy_no_ref_reaches_is_kept_and_one_that_main_reaches_is_removable(world):
    wt, name = world.copy(commits=0, detached=True)
    assert _verdict(world, wt) == ws.Verdict.REMOVE  # HEAD is main's own commit
    wt2, name2 = world.copy(commits=0, detached=True)
    (wt2 / "x.txt").write_text("x\n", encoding="utf-8")
    _must(wt2, "add", "-A")
    _must(
        wt2,
        "-c",
        "user.email=t@example.invalid",
        "-c",
        "user.name=t",
        "commit",
        "-q",
        "-m",
        "orphan",
    )
    _must(world.main, "branch", "-D", name2)  # nothing names that commit any more
    verdict, state, reasons = world.assess(wt2)
    assert verdict == ws.Verdict.SHOW
    assert any("no branch" in r or "detached" in r for r in reasons)


def test_a_copy_touched_in_the_last_two_hours_is_in_use_and_left_alone(world):
    wt, name = world.copy(commits=1, push=True)
    world.prs[name] = ("MERGED", _must(wt, "rev-parse", "HEAD"))
    assert (
        ws.assess(world.main, wt, pr_info=world.pr, now=__import__("time").time())[0]
        == ws.Verdict.KEEP
    )


def test_the_main_checkout_and_the_copy_the_sweep_runs_from_are_never_removed(world):
    wt, name = world.copy(commits=1, push=True, merged_into_main=True)
    assert (
        ws.assess(
            world.main, world.main, pr_info=world.pr, now=__import__("time").time() + LONG_AGO
        )[0]
        == ws.Verdict.KEEP
    )
    verdict = ws.assess(
        world.main, wt, pr_info=world.pr, now=__import__("time").time() + LONG_AGO, self_path=wt
    )[0]
    assert verdict == ws.Verdict.KEEP


def test_a_copy_whose_state_cannot_be_read_is_doubt(world):
    wt, name = world.copy(commits=1, push=True, merged_into_main=True)
    admin = world.main / ".git" / "worktrees"
    (admin / wt.name).rename(
        admin / f"{wt.name}_gone"
    )  # the copy's git administration vanishes: git can no longer read it
    assert _verdict(world, wt) == ws.Verdict.SHOW


@pytest.mark.skipif(
    os.name != "nt", reason="needs Windows junctions -- could-not-look, which is not a pass"
)
def test_a_link_to_a_real_folder_outside_makes_the_copy_doubtful_and_touches_nothing(
    world, tmp_path
):
    wt, name = world.copy(commits=1, push=True, merged_into_main=True)
    (tmp_path / "outside_real").mkdir()
    (tmp_path / "outside_real" / "canary.txt").write_text("must survive\n", encoding="utf-8")
    # Named .venv on purpose: that name is ignored and regenerable, so the link cannot make the copy doubtful
    # by showing up as an untracked file. Only the link rule can. It points at a folder that is NOT the main venv.
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(wt / ".venv"), str(tmp_path / "outside_real")],
        check=True,
        capture_output=True,
    )
    verdict, state, reasons = world.assess(wt)
    assert verdict == ws.Verdict.SHOW
    assert any("link to something real" in r for r in reasons)
    report = ws.sweep(world.main, pr_info=world.pr, now=__import__("time").time() + LONG_AGO)
    assert wt.exists() and (tmp_path / "outside_real" / "canary.txt").exists()
    assert any(e["path"] == str(wt) for e in report.shown)


@pytest.mark.skipif(
    os.name != "nt", reason="needs Windows junctions -- could-not-look, which is not a pass"
)
def test_the_known_link_to_the_main_venv_is_removed_as_a_link_and_the_venv_survives(
    world, tmp_path
):
    wt, name = world.copy(commits=1, push=True, merged_into_main=True)
    (tmp_path / "main" / ".venv").mkdir()
    (tmp_path / "main" / ".venv" / "canary.txt").write_text("the real venv\n", encoding="utf-8")
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(wt / ".venv"), str(tmp_path / "main" / ".venv")],
        check=True,
        capture_output=True,
    )
    assert _verdict(world, wt) == ws.Verdict.REMOVE
    report = ws.sweep(world.main, pr_info=world.pr, now=__import__("time").time() + LONG_AGO)
    assert not wt.exists()
    assert (tmp_path / "main" / ".venv" / "canary.txt").read_text(
        encoding="utf-8"
    ) == "the real venv\n"
    assert any(e["path"] == str(wt) for e in report.removed)


def test_a_sweep_removes_only_the_removable_and_a_dry_run_removes_nothing(world):
    done, done_name = world.copy(commits=1, push=True, merged_into_main=True)
    dirty, dirty_name = world.copy(commits=1, push=True, merged_into_main=True)
    (dirty / "unsaved.md").write_text("only here\n", encoding="utf-8")
    now = __import__("time").time() + LONG_AGO
    dry = ws.sweep(world.main, pr_info=world.pr, now=now, dry_run=True)
    assert done.exists() and dirty.exists()
    assert any(e["path"] == str(done) for e in dry.removed) and any(
        e["path"] == str(dirty) for e in dry.shown
    )
    real = ws.sweep(world.main, pr_info=world.pr, now=now)
    assert not done.exists() and dirty.exists() and (dirty / "unsaved.md").exists()
    assert _git(world.main, "rev-parse", "--verify", f"refs/heads/{done_name}").returncode == 0, (
        "the branch must outlive its folder"
    )
    assert real.removed and real.shown


def test_every_removal_records_the_four_answers_it_was_made_on(world, tmp_path):
    wt, name = world.copy(commits=1, push=True, merged_into_main=True)
    log = tmp_path / "sweeps.jsonl"
    ws.sweep(world.main, pr_info=world.pr, now=__import__("time").time() + LONG_AGO, log_path=log)
    line = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    removed = line["removed"][0]
    assert (
        removed["finished"] is True
        and removed["nothing_unique"] is True
        and removed["links_safe"] is True
    )
    assert removed["path"] == str(wt)


def test_a_copy_that_changes_between_the_listing_and_the_removal_is_not_removed(world):
    wt, name = world.copy(commits=1, push=True, merged_into_main=True)
    calls = {"n": 0}

    def sneaky(branch):
        calls["n"] += 1
        if calls["n"] == 1:
            (wt / "arrived_late.md").write_text("typed after the listing\n", encoding="utf-8")
        return None

    report = ws.sweep(world.main, pr_info=sneaky, now=__import__("time").time() + LONG_AGO)
    assert wt.exists() and (wt / "arrived_late.md").exists()
    assert not report.removed


def test_the_summary_line_says_what_happened_and_never_reads_clean_when_it_could_not_look(world):
    wt, name = world.copy(commits=1, push=True)  # no host answer: could not read
    report = ws.sweep(world.main, pr_info=world.pr, now=__import__("time").time() + LONG_AGO)
    line = report.summary()
    assert "need your word" in line and "0 removed" in line
    assert "could not read" in line


def test_removing_by_hand_refuses_unique_work_and_snapshots_it_when_asked(world):
    wt, name = world.copy(commits=1, push=True, merged_into_main=True)
    (wt / "unsaved.md").write_text("only here\n", encoding="utf-8")
    with pytest.raises(ws.WorkCopyRefused):
        ws.remove_copy(world.main, wt)
    assert (wt / "unsaved.md").exists()
    ws.remove_copy(world.main, wt, snapshot=True)
    assert not wt.exists()
    assert _must(world.main, "show", f"refs/rescue/{wt.name}:unsaved.md") == "only here"


def test_removing_by_hand_never_touches_the_main_checkout(world):
    with pytest.raises(ws.WorkCopyRefused):
        ws.remove_copy(world.main, world.main)
    assert (world.main / "a.txt").exists()


def test_the_command_line_remove_works_on_a_copy_without_the_real_repository(world):
    wt, name = world.copy(commits=1, push=True, merged_into_main=True)
    assert ws.main(["remove", str(wt)]) == 0
    assert not wt.exists()


def test_the_last_sweep_line_reads_loudly_when_nothing_has_ever_swept(tmp_path):
    assert "never been swept" in ws.last_sweep_line(tmp_path / "none.jsonl")


def test_the_last_sweep_line_reports_what_the_last_sweep_did(world, tmp_path):
    log = tmp_path / "sweeps.jsonl"
    world.copy(commits=1, push=True, merged_into_main=True)
    ws.sweep(world.main, pr_info=world.pr, now=__import__("time").time() + LONG_AGO, log_path=log)
    line = ws.last_sweep_line(log)
    assert "1 removed because finished" in line and "sweep" in line


def test_maintenance_runs_the_sweep_and_a_dry_run_of_maintenance_does_not(monkeypatch):
    from divineos.core import body_awareness

    calls = []

    def fake_sweep(repo, **kw):
        calls.append(kw)
        return ws.SweepReport(removed=[{"path": "x"}])

    monkeypatch.setattr(ws, "sweep", fake_sweep)
    real = body_awareness.sweep_work_copies()
    assert real["removed"] == 1 and "1 removed" in real["summary"] and len(calls) == 1
    dry = body_awareness.run_maintenance(dry_run=True)
    assert "not swept in a dry run" in dry["work_copies"]["summary"]
    assert len(calls) == 1, "a dry run of maintenance must not walk the work copies"


def _orphan_detached_copy(world, path):
    """A detached copy holding an untracked file and a commit no ref reaches: doubtful anywhere but scratch."""
    _must(world.main, "worktree", "add", "-q", "--detach", str(path), "main")
    (path / "left_by_a_test.txt").write_text("x\n", encoding="utf-8")
    _must(path, "add", "-A")
    _must(
        path,
        "-c",
        "user.email=t@example.invalid",
        "-c",
        "user.name=t",
        "commit",
        "-q",
        "-m",
        "orphan",
    )
    (path / "also_untracked.txt").write_text("y\n", encoding="utf-8")


def test_the_push_gates_own_scratch_checkout_in_the_temp_folder_is_removable(world, monkeypatch):
    import tempfile

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(world.root))
    scratch = world.root / "divineos-push-gate-AbC123"
    _orphan_detached_copy(world, scratch)
    verdict, state, reasons = world.assess(scratch)
    assert verdict == ws.Verdict.REMOVE, reasons
    assert "scratch" in state.finished_how


def test_a_look_alike_name_outside_the_temp_folder_or_a_different_name_is_an_ordinary_copy(
    world, monkeypatch
):
    import tempfile

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(world.root))
    elsewhere = world.root / "nested"
    elsewhere.mkdir()
    spoof = elsewhere / "divineos-push-gate-AbC123"
    _orphan_detached_copy(world, spoof)
    assert _verdict(world, spoof) == ws.Verdict.SHOW
    other = world.root / "scratch-AbC123"
    _orphan_detached_copy(world, other)
    assert _verdict(world, other) == ws.Verdict.SHOW


# The next tests come from Aether's cold read of #698 (his probes P1-P3, 2026-10-20), plus the cases around them.


def _sweep(world, **kw):
    return ws.sweep(
        world.main,
        pr_info=world.pr,
        now=__import__("time").time() + LONG_AGO,
        log_path=world.root / "log.jsonl",
        **kw,
    )


def test_a_scratch_checkout_with_a_stray_file_is_actually_removed_and_does_not_end_the_sweep(
    world, monkeypatch
):
    import tempfile

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(world.root))
    first, name = world.copy(commits=1, push=True)
    world.prs[name] = ("MERGED", _must(first, "rev-parse", "HEAD"))
    scratch = world.root / "divineos-push-gate-ABC123"
    _must(world.main, "worktree", "add", "-q", "--detach", str(scratch), "main")
    (scratch / "left_by_a_test.txt").write_text("x\n", encoding="utf-8")
    report = _sweep(world)
    removed = {Path(e["path"]).name for e in report.removed}
    assert scratch.name in removed and first.name in removed
    assert not scratch.exists() and not first.exists()


def test_a_locked_work_copy_is_in_use_and_never_forced(world):
    wt, name = world.copy(commits=1, push=True)
    world.prs[name] = ("MERGED", _must(wt, "rev-parse", "HEAD"))
    _must(world.main, "worktree", "lock", "--reason", "a test run is using it", str(wt))
    verdict, state, reasons = world.assess(wt)
    assert verdict == ws.Verdict.KEEP
    assert any("locked" in r and "a test run is using it" in r for r in reasons)
    _sweep(world)
    assert wt.exists()


def test_one_removal_that_git_refuses_is_listed_and_the_sweep_goes_on_and_records(
    world, monkeypatch
):
    a, a_name = world.copy(commits=1, push=True, merged_into_main=True)
    b, b_name = world.copy(commits=1, push=True, merged_into_main=True)
    real_remove = ws.remove_copy

    def refuse_first(main_root, wt, **kw):
        if Path(wt).name == a.name:
            raise ws.WorkCopyRefused("git could not remove it")
        return real_remove(main_root, wt, **kw)

    monkeypatch.setattr(ws, "remove_copy", refuse_first)
    report = _sweep(world)
    assert any("refused at removal" in " ".join(e["reasons"]) for e in report.shown)
    assert a.exists() and not b.exists()
    assert (world.root / "log.jsonl").exists(), (
        "the record is written even when a removal was refused"
    )


def test_a_registration_whose_folder_is_gone_is_pruned_and_not_listed_forever(world):
    wt, name = world.copy(commits=1, push=True)
    shutil.rmtree(wt)
    dry = _sweep(world, dry_run=True)
    assert any(Path(p).name == wt.name for p in dry.pruned)
    assert wt.name in _must(world.main, "worktree", "list", "--porcelain")
    real = _sweep(world)
    assert not [e for e in real.shown if Path(e["path"]).name == wt.name]
    assert wt.name not in _must(world.main, "worktree", "list", "--porcelain")
    assert "pruned" in real.summary()


def test_a_locked_registration_whose_folder_is_gone_is_listed_and_not_claimed_as_pruned(world):
    """Aether's probe from his cold read of #698 at 4cba35717: `git worktree prune` skips a locked
    registration, so the sweep must not report it pruned, and it must not vanish from sight either."""
    wt, name = world.copy(commits=1, push=True)
    _must(world.main, "worktree", "lock", str(wt), "--reason", "on a drive that is unplugged")
    shutil.rmtree(wt)
    report = _sweep(world)
    claimed = [p for p in report.pruned if wt.name in p]
    still_registered = wt.name in _must(world.main, "worktree", "list", "--porcelain")
    assert still_registered and not claimed
    assert any(
        Path(e["path"]).name == wt.name and "locked" in " ".join(e["reasons"]) for e in report.shown
    )
    # a dry run reads only the lock, never a prune, so it must not promise one either
    dry = _sweep(world, dry_run=True)
    assert not [p for p in dry.pruned if wt.name in p]
    assert any(Path(e["path"]).name == wt.name for e in dry.shown)


def test_a_finished_copy_with_a_top_level_folder_touched_just_now_is_in_use(world):
    wt, name = world.copy(commits=1, push=True, merged_into_main=True)
    (wt / "tmp").mkdir()
    now = __import__("time").time() + LONG_AGO
    os.utime(
        wt / "tmp", (now, now)
    )  # something inside the copy moved a moment ago; the folder's own mtime did not
    assert ws.assess(world.main, wt, pr_info=world.pr, now=now)[0] == ws.Verdict.KEEP


def test_a_sweep_inside_a_test_run_refuses_to_touch_the_real_home_and_its_log(world, monkeypatch):
    monkeypatch.delenv("DIVINEOS_HOME", raising=False)
    with pytest.raises(ws.WorkCopyRefused, match="test run"):
        ws.sweep(world.main, pr_info=world.pr)


def test_a_sweep_that_cannot_run_says_so_and_never_reads_as_clean(monkeypatch):
    from divineos.core import body_awareness

    def refuse(repo, **kw):
        raise ws.WorkCopyRefused("not inside a git repository")

    monkeypatch.setattr(ws, "sweep", refuse)
    result = body_awareness.sweep_work_copies()
    assert "could not sweep work copies" in result["summary"] and "error" in result
