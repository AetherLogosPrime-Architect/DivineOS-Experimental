"""Integrating a correction reads dot-directories and always says why it refuses.

Draft: docs/drafts/integrate_reads_dot_directories_and_says_why_it_refuses_draft_2026-11-09.md
Walk: walk-3dcd78d91542.

Found 2026-11-09 marking off Dad's oldest asks: evidence naming real
`.claude/hooks/...` files was refused as absent, and the refusal line was
blank. The path pattern started matching after the leading dot, the verifier's
own file rule had no dot in its character class, and the explainer re-typed
integrate()'s checks by hand and left the existence check out.

Every pass-case here points at something that exists in this checkout, taken
from git, so nothing here is satisfied by typing.
"""

import subprocess
from pathlib import Path

import pytest

from divineos.core import andrew_correction_tracker as act
from divineos.core import closure_verification as cv

REPO = Path(__file__).resolve().parents[1]
EXTENSIONS = (".py", ".md", ".sh", ".sql", ".toml", ".yaml", ".yml", ".json")
SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/._-")

# Real files under dot-directories, named by the failure that started this.
REAL_DOT_FILES = (
    ".claude/hooks/work-item-doorman.sh",
    ".claude/hooks/lib/remedy_allowlist.sh",
)


@pytest.fixture(autouse=True)
def _isolate_home(monkeypatch, tmp_path):
    monkeypatch.setattr(act, "divineos_home", lambda: tmp_path)
    monkeypatch.chdir(REPO)
    yield


def _tracked_paths() -> list[str]:
    done = subprocess.run(
        ["git", "-C", str(REPO), "ls-files"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if done.returncode != 0:
        pytest.skip("git could not list files; this would assert nothing about the pattern")
    return [p for p in done.stdout.splitlines() if p.endswith(EXTENSIONS) and set(p) <= SAFE]


def test_every_tracked_file_is_extracted_whole_including_dot_directories():
    """A rule over every real file, not a list of the cases I remember."""
    paths = _tracked_paths()
    assert any(p.startswith(".claude/") for p in paths), "the probe found no dot-directory file"
    missed = [p for p in paths if p not in act._candidate_pointers(f"fixed in {p} and done")]
    assert missed == [], f"{len(missed)} real paths were not extracted whole, e.g. {missed[:3]}"


def test_the_shape_check_and_the_extractor_agree_on_every_tracked_file():
    """One definition of a file path, used by both (Deming)."""
    disagree = [
        p
        for p in _tracked_paths()
        if act._has_structural_artifact(f"fixed in {p} and done") is not True
    ]
    assert disagree == []


@pytest.mark.parametrize("path", REAL_DOT_FILES)
def test_evidence_naming_a_real_dot_directory_file_is_found(path):
    assert (REPO / path).is_file(), f"the probe file is gone: {path}"
    state, detail = act.artifact_reality(f"The doorman lives in {path} and is wired")
    assert state == "found", detail


def test_a_made_up_dot_directory_file_is_still_not_found():
    state, _ = act.artifact_reality("It lives in .claude/hooks/nothing_here_at_all.sh somewhere")
    assert state == "not-found"


@pytest.mark.parametrize("citation", ["../x.py", "a/../x.py", "../../etc/x.py"])
def test_a_path_that_climbs_out_of_the_repo_is_not_a_file_citation(citation):
    assert cv._RE_FILE.match(citation) is None


def test_the_verifier_accepts_a_dot_directory_file_citation():
    assert cv._RE_FILE.match(".claude/hooks/work-item-doorman.sh") is not None
    assert cv._RE_FILE.match("src/divineos/core/ledger.py:12") is not None


def test_a_refusal_for_a_missing_pointer_names_what_was_looked_up():
    cid = act.file_correction("a row to refuse")
    evidence = "It lives in .claude/hooks/nothing_here_at_all.sh somewhere"
    ok, reason = act.integrate_verdict(cid, evidence)
    assert ok is False
    assert ".claude/hooks/nothing_here_at_all.sh" in reason
    assert act.explain_integrate_refusal(cid, evidence) == reason


def test_whenever_integrate_refuses_the_reason_is_never_empty():
    """The invariant: integrate() False implies a named reason, for every way to refuse."""
    cid = act.file_correction("a row for the refusal sweep")
    done_id = act.file_correction("a row that is already closed")
    assert act.integrate(done_id, f"landed in {REAL_DOT_FILES[0]} and is wired") is True
    cases = [
        (cid, ""),
        (cid, "too short"),
        (cid, "I learned and will do better next time around, honestly"),
        (cid, "Sorted out in .claude/hooks/nothing_here_at_all.sh, done"),
        (done_id, f"again, landed in {REAL_DOT_FILES[0]} and is wired"),
        (99999, f"landed in {REAL_DOT_FILES[0]} and is wired"),
    ]
    for correction_id, evidence in cases:
        ok, reason = act.integrate_verdict(correction_id, evidence)
        assert ok is False, (correction_id, evidence)
        assert reason.strip(), f"blank reason for {(correction_id, evidence)!r}"
        assert act.integrate(correction_id, evidence) is False
        assert act.explain_integrate_refusal(correction_id, evidence) == reason


def test_integrate_and_its_verdict_never_disagree_on_a_pass():
    cid = act.file_correction("a row that should integrate")
    evidence = f"The doorman holds in {REAL_DOT_FILES[0]} and {REAL_DOT_FILES[1]}"
    ok, reason = act.integrate_verdict(cid, evidence)
    assert (ok, reason) == (True, "")
    assert act.integrate(cid, evidence) is True


def test_an_absolute_path_under_the_real_checkout_is_found():
    """Aether's cold read, 2026-11-09: the real root, not a made-up one."""
    posix = REPO.as_posix()
    for root in (posix, str(REPO)):
        state, detail = act.artifact_reality(
            f"changed {root}/src/divineos/core/closure_verification.py to read dots"
        )
        assert state == "found", (root, detail)


def test_an_absolute_path_through_a_folder_name_with_a_space_is_found(tmp_path, monkeypatch):
    """This machine's own root is 'C:/DIVINE OS/...'; the token was cut at the space."""
    checkout = tmp_path / "A FOLDER WITH SPACES" / "Some-Checkout"
    target = checkout / "src" / "pkg" / "thing.py"
    target.parent.mkdir(parents=True)
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.chdir(checkout)
    for root in (checkout.as_posix(), str(checkout)):
        state, detail = act.artifact_reality(f"changed {root}/src/pkg/thing.py to fix it")
        assert state == "found", (root, detail)


def test_the_root_is_only_stripped_from_the_front_of_a_path(tmp_path, monkeypatch):
    """A made-up file under the real root is still not found, with the tokens named."""
    monkeypatch.chdir(tmp_path)
    state, detail = act.artifact_reality(f"changed {tmp_path.as_posix()}/src/not_there.py to fix")
    assert state == "not-found"
    assert "not_there.py" in detail


def test_the_command_never_prints_a_blank_refusal():
    """What Dad saw: 'Refused correction #287:' and nothing after it."""
    import click
    from click.testing import CliRunner

    from divineos.cli.andrew_correction_commands import register

    cli = click.Group()
    register(cli)
    cid = act.file_correction("a row to refuse through the command")
    result = CliRunner().invoke(
        cli,
        [
            "andrew-correction",
            "integrate",
            str(cid),
            "--evidence",
            "Sorted in .claude/hooks/nothing_here_at_all.sh ok",
            "--expect-text",
            "a row to refuse through",
        ],
    )
    assert result.exit_code != 0
    text = result.output
    line = next(ln for ln in text.splitlines() if ln.startswith("Refused correction"))
    assert line.split(":", 1)[1].strip(), f"blank reason printed: {line!r}"
