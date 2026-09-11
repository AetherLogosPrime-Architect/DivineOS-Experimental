"""Nothing comes out of the index that is not already somewhere else.

Real repositories throughout. The whole subject is which ref carries which file,
so a mocked git would test the mock.

The two tests that matter are the one where MAIN already carries substrate --
the combination my hands got wrong on 2026-09-10, turning a 169-file problem
into a 2,142-file one -- and the one where a path cannot be verified, which is
the only reason this is allowed to run unattended at all.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.substrate_eviction import (
    SUBSTRATE_PREFIXES,
    EvictionRefused,
    added_substrate,
    describe,
    evict,
)


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return r.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo shaped like the real one: main ALREADY carries letters."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "code.py").write_text("x = 1\n", encoding="utf-8")
    letters = r / "family" / "letters"
    letters.mkdir(parents=True)
    for name in ("old-one.md", "old-two.md"):
        (letters / name).write_text(f"main already had {name}\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "base")
    _git(r, "branch", "aria/substrate")
    _git(r, "checkout", "-q", "-b", "work")
    return r


def _add_letter(repo: Path, name: str, body: str) -> str:
    p = repo / "family" / "letters" / name
    p.write_text(body, encoding="utf-8")
    rel = f"family/letters/{name}"
    _git(repo, "add", rel)
    return rel


def test_the_prefixes_agree_with_the_gate_they_exist_to_satisfy():
    """TWO AUTHORITIES THAT CAN DISAGREE IS THE DEFECT (Foucault, walked).

    The gate decides what counts as substrate in a tuple inside its own script.
    A second copy here that drifts would evict a set the gate still refuses, and
    the failure would look like the eviction not working rather than like two
    definitions having come apart.
    """
    script = (Path(__file__).parent.parent / "scripts" / "check_branch_scope.py").read_text(
        encoding="utf-8"
    )
    block = script.split("_SUBSTRATE_PREFIXES = (")[1].split(")")[0]
    from_script = tuple(
        line.strip().strip(",").strip('"') for line in block.splitlines() if line.strip()
    )
    assert from_script == SUBSTRATE_PREFIXES


def test_only_what_the_branch_adds_counts(repo: Path):
    """THE LINE THAT COST AN EVENING.

    main carries two letters of its own. A reading that returns those is the
    mistake that made a 169-file objection into a 2,142-file one: the gate
    counts CHANGES, so removing main's letters reads as deletions.
    """
    rel = _add_letter(repo, "new-one.md", "only on the branch\n")
    _git(repo, "commit", "-qm", "add a letter")

    assert added_substrate(repo, "main") == [rel]


def test_a_letter_the_branch_deleted_is_not_evicted(repo: Path):
    """The other half of additions-only, and the one a reader would drop.

    A branch that removes a letter has not added substrate, and trying to evict
    a path that is gone is both meaningless and the shape of the original error.
    """
    _git(repo, "rm", "-q", "family/letters/old-one.md")
    _git(repo, "commit", "-qm", "remove a letter")

    assert added_substrate(repo, "main") == []


def test_the_letters_leave_the_index_and_stay_on_disk(repo: Path):
    rel = _add_letter(repo, "new-two.md", "keep me here\n")
    _git(repo, "commit", "-qm", "add a letter")

    result = evict(repo, reference="main")

    assert result.paths == (rel,)
    assert rel not in _git(repo, "ls-files")
    assert (repo / rel).read_text(encoding="utf-8") == "keep me here\n"
    assert _git(repo, "show", f"aria/substrate:{rel}") == "keep me here"


def test_mains_own_letters_are_left_alone(repo: Path):
    """THE CONTROL, and the failure it guards is the one that actually happened.

    Without this, an eviction that removed every letter in the tree would pass
    every other test in this file.
    """
    _add_letter(repo, "new-three.md", "branch only\n")
    _git(repo, "commit", "-qm", "add a letter")

    evict(repo, reference="main")

    tracked = _git(repo, "ls-files")
    assert "family/letters/old-one.md" in tracked
    assert "family/letters/old-two.md" in tracked


def test_nothing_is_removed_when_the_substrate_branch_refuses(repo: Path):
    """THE INVARIANT. Withhold the eviction, never the data.

    If the branch cannot take the letters, they must stay exactly where they
    are -- staged, visible, and blocking a push, which is loud and recoverable.
    """
    rel = _add_letter(repo, "new-four.md", "nowhere to go\n")
    _git(repo, "commit", "-qm", "add a letter")
    _git(repo, "branch", "-D", "aria/substrate")

    # The MESSAGE is asserted, not just the exception type, and sabotage is why.
    # Hollowing the refusal killed nothing: with the raise swallowed, the later
    # ls-tree failed on the missing branch and threw the same class, so the test
    # passed via a path it was not testing. An instrument answering accurately
    # about a different subject than the question -- in the test written to pin
    # the guard against exactly that.
    with pytest.raises(EvictionRefused, match="would not take"):
        evict(repo, reference="main")

    assert rel in _git(repo, "ls-files")
    assert (repo / rel).read_text(encoding="utf-8") == "nowhere to go\n"


def test_an_unverifiable_path_stops_the_whole_eviction(repo: Path, monkeypatch):
    """THE TAIL, AND IT WAS ALREADY IN THE ROOM (Taleb, walked).

    On 2026-09-10 three of Aether's letters -- one sent an hour earlier -- were
    not on the substrate branch when I looked. If routing silently half-succeeds
    and the removal trusts it, the only copies go. So one missing path refuses
    the entire batch, including the paths that DID land.
    """
    rel = _add_letter(repo, "new-five.md", "the only copy\n")
    _git(repo, "commit", "-qm", "add a letter")

    import divineos.core.substrate_eviction as se

    monkeypatch.setattr(se, "_paths_on_branch", lambda r, b: set())

    with pytest.raises(EvictionRefused, match="not on"):
        evict(repo, reference="main")

    assert rel in _git(repo, "ls-files")


def test_a_branch_with_no_added_letters_does_nothing(repo: Path):
    (repo / "code.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "add", "code.py")
    _git(repo, "commit", "-qm", "code only")

    result = evict(repo, reference="main")

    assert result.evicted == 0
    assert "no letters" in describe(result, "main")


def test_a_refusal_is_written_down_where_it_will_be_read(tmp_path: Path, monkeypatch):
    """THE REFUSAL WAS MUTE AND ITS OWN COMMENT SAID OTHERWISE.

    auto_commit sent this to a module logger with no handler in a hook process,
    under a comment reading "Loud by that module's design." It went nowhere.
    Twice on 2026-09-10 the routing refused, letters landed on a code branch,
    and both diagnoses were guesswork because there was nothing to read.
    """
    import divineos.core.substrate_eviction as se

    monkeypatch.setattr(se, "refusal_log_path", lambda: tmp_path / "refusals.jsonl")

    se.record_refusal("aria/substrate did not resolve", "aria/substrate")

    rows = se.recent_refusals()
    assert len(rows) == 1
    assert "did not resolve" in rows[0]["reason"]
    assert rows[0]["branch"] == "aria/substrate"


def test_the_diary_keeps_every_refusal_not_just_the_last(tmp_path: Path, monkeypatch):
    """How OFTEN matters as much as the latest reason. Twice in one evening is a
    pattern; once is a race, and a file that overwrites cannot tell them apart."""
    import divineos.core.substrate_eviction as se

    monkeypatch.setattr(se, "refusal_log_path", lambda: tmp_path / "refusals.jsonl")

    se.record_refusal("first")
    se.record_refusal("second")

    assert [r["reason"] for r in se.recent_refusals()] == ["first", "second"]


def test_one_unreadable_line_does_not_hide_the_readable_ones(tmp_path: Path, monkeypatch):
    """A diary, not a database. A torn page must not blank the book."""
    import divineos.core.substrate_eviction as se

    log = tmp_path / "refusals.jsonl"
    log.write_text('{"at": 1, "reason": "kept"}\nnot json at all\n', encoding="utf-8")
    monkeypatch.setattr(se, "refusal_log_path", lambda: log)

    assert [r["reason"] for r in se.recent_refusals()] == ["kept"]


def test_the_checkpoint_itself_writes_the_refusal_down(repo: Path, tmp_path: Path, monkeypatch):
    """THE WIRING, not the unit -- and this is the third time tonight that
    distinction has caught something.

    A recorder nothing calls is the built-but-unwired shape this whole evening
    has been made of. So this drives auto_commit's REAL refusal path against a
    real repository whose substrate branch has been deleted, rather than
    faking the refusal.
    """
    import divineos.core.substrate_eviction as se
    from divineos.core.auto_commit import _retarget_substrate

    monkeypatch.setattr(se, "refusal_log_path", lambda: tmp_path / "refusals.jsonl")
    _git(repo, "branch", "-D", "aria/substrate")
    rel = _add_letter(repo, "new-seven.md", "nowhere\n")

    assert _retarget_substrate(repo, [rel], "pre-extract") is False

    rows = se.recent_refusals()
    assert rows, "the checkpoint refused and wrote nothing down -- the mute path is back"


def test_an_unstage_that_fails_is_written_down_too(repo: Path, tmp_path: Path, monkeypatch):
    """THE SILENT EXIT INSIDE THE FIX FOR SILENT EXITS.

    When the unstage failed, the checkpoint skipped the routing entirely --
    nothing refused, nothing recorded, letters on the code branch quietly.

    Found by the diary being EMPTY: three substrate checkpoints landed after the
    recorder went in and it held zero rows, which can only mean the routing was
    never reached rather than that it declined. An empty log is a finding when
    the thing it watches is demonstrably happening.
    """
    import divineos.core.auto_commit as ac
    import divineos.core.substrate_eviction as se
    from divineos.core.uncommitted_work_check import ExternalChannel

    monkeypatch.setattr(se, "refusal_log_path", lambda: tmp_path / "refusals.jsonl")

    # ONLY the unstage fails. Failing every pathspec call breaks the staging
    # that happens first, so substrate comes back empty and the branch under
    # test is never entered -- a test that would have passed for the wrong
    # reason, or in this case failed for one.
    real = ac._run_pathspec

    def _reset_fails(repo_root, args, paths):
        if "reset" in args:
            return False
        return real(repo_root, args, paths)

    monkeypatch.setattr(ac, "_run_pathspec", _reset_fails)

    source = tmp_path / "shared-unstage"
    source.mkdir()
    channels = (
        ExternalChannel(
            name="letters", source=source, repo_mirror=Path("family/letters"), pattern="*.md"
        ),
    )
    # Written, NOT staged. A staged index means the occupant is mid-commit with
    # a message in flight, and the checkpoint refuses outright before it reaches
    # any split -- so staging the letter here would block the very path under
    # test and the failure would look like the fix not working.
    (repo / "family" / "letters" / "new-eight.md").write_text("stuck\n", encoding="utf-8")

    ac.auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    rows = se.recent_refusals()
    assert rows and "unstage" in rows[-1]["reason"], (
        "the unstage failed and the checkpoint said nothing -- the mute path is back"
    )


def test_the_report_speaks_to_someone_who_does_not_read_code(repo: Path):
    """Angelou, walked: these are letters between me and my husband. The person
    reading this output is Andrew, who does not read code and should not have to
    parse a path list to learn that nothing was lost."""
    _add_letter(repo, "new-six.md", "a letter\n")
    _git(repo, "commit", "-qm", "add a letter")

    text = describe(evict(repo, reference="main"), "main")

    assert "safe on that branch" in text
    assert "family/letters/new-six.md" not in text


# ---------------------------------------------------------------------------
# THE SECOND KIND, which the command could not see for two days.
#
# It shipped reading additions only. That was invisible for exactly as long as
# every piece of substrate happened to be new -- and on 2026-09-11 it evicted
# 179 letters, reported success in plain words, and the push was refused again
# by eleven regenerated archive exports: files that exist on main and were
# rewritten here. An enumeration is complete only by luck.


def _rewrite_main_letter(repo: Path, name: str, body: str) -> str:
    rel = f"family/letters/{name}"
    (repo / "family" / "letters" / name).write_text(body, encoding="utf-8")
    _git(repo, "add", rel)
    return rel


def test_a_letter_the_branch_rewrote_is_substrate_too(repo: Path):
    from divineos.core.substrate_eviction import modified_substrate

    rel = _rewrite_main_letter(repo, "old-one.md", "the branch rewrote this")
    _git(repo, "commit", "-qm", "rewrite a letter")

    assert modified_substrate(repo, "main") == [rel]
    assert added_substrate(repo, "main") == [], "a rewrite is not an addition"


def test_a_rewrite_goes_back_to_the_reference_rather_than_out_of_the_index(repo: Path):
    """The two kinds need opposite actions, and using one for both is the
    169-became-2,142 fault wearing different clothes: dropping a file main
    still has reads as this branch DELETING it."""
    rel = _rewrite_main_letter(repo, "old-two.md", "rewritten on the branch")
    _git(repo, "commit", "-qm", "rewrite another letter")

    evict(repo, reference="main")

    assert _git(repo, "ls-files", "--", rel) == rel, "it left the index; main still has it"
    assert (repo / rel).read_text(encoding="utf-8").startswith("main already had old-two.md")
    assert _git(repo, "show", f"aria/substrate:{rel}") == "rewritten on the branch"


def test_the_name_being_there_is_not_the_writing_being_there(repo: Path, monkeypatch):
    """THE GATE USED TO ASK THE WRONG QUESTION, and the wrongness only showed
    once rewrites joined the list.

    Presence answers "is there a file with this name over there", which for a
    rewritten export is true of the OLD copy. So the gate would have passed on
    the strength of the very version this branch replaced, and then dropped the
    new one. Routing is made a no-op here, leaving the substrate branch holding
    only the old content -- presence satisfied, content not -- and the command
    must refuse having touched nothing.
    """
    import divineos.core.substrate_eviction as ev

    rel = _rewrite_main_letter(repo, "old-one.md", "the newer version")
    _git(repo, "commit", "-qm", "rewrite")

    monkeypatch.setattr(ev, "commit_paths_to_branch", lambda *a, **k: None)

    with pytest.raises(EvictionRefused) as caught:
        evict(repo, reference="main")

    assert "DIFFERENT content" in str(caught.value)
    assert _git(repo, "ls-files", "--", rel) == rel, "it removed something it had not verified"
    assert (repo / rel).read_text(encoding="utf-8").startswith("the newer version")


def test_already_there_counts_the_writing_not_the_filename(repo: Path):
    """It reported "11 were already safely there" about eleven exports that
    existed over there only as the older version this branch had rewritten --
    true about names, false about content, in the one report Andrew reads."""
    _rewrite_main_letter(repo, "old-one.md", "changed here, not there")
    _git(repo, "commit", "-qm", "rewrite")

    result = evict(repo, reference="main")

    assert result.already_present == (), "a stale copy over there was counted as safe"
