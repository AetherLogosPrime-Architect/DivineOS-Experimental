"""The repo normalizes line endings on commit, and nothing tested that.

Written 2026-08-17, after the fourth time this session I raised a CRLF worry
and measured it wrong. The worry was never the real problem — `.gitattributes`
declares `text eol=lf` for every text type here, so a CRLF working copy is
converted at commit-write and the blob that lands in the repo is LF. Every
honest measurement came back zero because the protection was already working.

What was actually missing: any test of the protection. Delete `.gitattributes`
or drop a line from it and the whole suite still passes, while Windows editors
quietly start committing CRLF. The only thing that has ever caught real damage
here was shellcheck's SC1017 firing incidentally on one file type — a coverage
accident, not a guard.

These drive a real git repository rather than asserting on the text of
`.gitattributes`, because the question is what git DOES with the file, not
what the file says. A test that greps the config would pass just as happily
if git ignored it.

The `test_the_detector_can_see_crlf_at_all` case is the point of the whole
module and is deliberately first. Every other assertion here reports an
ABSENCE, and an absence-report from an uncalibrated instrument is worthless —
that is exactly how four readings went wrong: the measurement had degraded
into something that could not detect CRLF, and returned a confident number
saying there was none. So the counter proves it can find CRLF in a buffer
known to contain it before any test is allowed to conclude there is none.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

CRLF = b"\r\n"
REPO_ROOT = Path(__file__).resolve().parent.parent


def count_crlf(blob: bytes) -> int:
    return blob.count(CRLF)


def test_the_detector_can_see_crlf_at_all() -> None:
    """Calibration. Without this, every assertion below is unfalsifiable."""
    assert count_crlf(b"a\r\nb\r\n") == 2
    assert count_crlf(b"a\nb\n") == 0
    assert count_crlf(b"") == 0


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True, timeout=30
    )
    return r.stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real repo carrying this project's actual .gitattributes AND its
    line-ending config.

    ``core.autocrlf`` is pinned to false because that is what this repo sets
    locally, and because leaving it inherited makes the whole module lie. This
    machine's SYSTEM config sets ``autocrlf=true``, which converts every text
    file on commit whether or not a rule names it — so a fresh temp repo
    passed the LF assertions for a reason that had nothing to do with
    ``.gitattributes``, and would have kept passing if the file were deleted.

    Found by the control case below on the first run, which is the entire
    argument for having a control case: five green tests were green for the
    wrong reason and only the one expecting a NON-conversion could see it.
    """
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t.t")
    _git(r, "config", "user.name", "t")
    _git(r, "config", "core.autocrlf", "false")
    (r / ".gitattributes").write_bytes((REPO_ROOT / ".gitattributes").read_bytes())
    _git(r, "add", ".gitattributes")
    _git(r, "commit", "-q", "--no-verify", "-m", "attrs")
    return r


def _commit_crlf_file(repo: Path, name: str) -> bytes:
    """Write a CRLF file, commit it, return the bytes git actually stored."""
    payload = b"#!/bin/bash\r\necho one\r\necho two\r\n"
    (repo / name).write_bytes(payload)
    assert count_crlf(payload) == 3, "the fixture itself must contain CRLF"
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "--no-verify", "-m", f"add {name}")
    r = subprocess.run(
        ["git", "show", f"HEAD:{name}"], cwd=repo, capture_output=True, check=True, timeout=30
    )
    return r.stdout


@pytest.mark.parametrize("name", ["run.sh", "mod.py", "notes.md", "conf.toml", "data.json"])
def test_crlf_working_copy_is_stored_as_lf(repo: Path, name: str) -> None:
    """The blob is what other machines get. It must be LF regardless of the
    editor that wrote the working copy."""
    blob = _commit_crlf_file(repo, name)
    assert count_crlf(blob) == 0, f"{name} was committed with CRLF"
    assert blob.count(b"\n") == 3, "content must survive the conversion intact"


def test_a_type_without_an_eol_rule_is_not_silently_converted(repo: Path) -> None:
    """Guards the assertion above from meaning nothing.

    If git were normalizing everything by default, the passes above would not
    be evidence that .gitattributes is doing any work. An extension with no
    rule keeps its CRLF, which shows the conversion is rule-driven.
    """
    blob = _commit_crlf_file(repo, "payload.bin")
    assert count_crlf(blob) == 3, "conversion is happening for reasons other than the rules"


def test_every_text_type_this_repo_writes_has_an_eol_rule() -> None:
    """The rules only protect the extensions they name. This pins the list, so
    adding a new text type without a rule fails here rather than surfacing as
    a mystery CRLF diff later."""
    attrs = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
    for ext in ("sh", "py", "md", "yml", "yaml", "toml", "json", "cfg", "ini"):
        assert f"*.{ext} text eol=lf" in attrs, f"*.{ext} has no line-ending rule"
