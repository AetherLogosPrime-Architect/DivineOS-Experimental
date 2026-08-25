"""A test's setup must not create a door out of its sandbox.

Guards ``scripts/check_test_link_targets.py``, which exists because a fixture
here junctioned the real ``.venv`` into a temp repo on 2026-08-25 and pytest's
temp-directory cleanup then deleted the real one through the link.

The regression test at the bottom is the point: it runs the check against this
checkout, so the class cannot come back quietly.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_test_link_targets as chk  # noqa: E402

REPO = Path(__file__).resolve().parents[1]

DESTRUCTIVE = """
import subprocess

REPO_ROOT = Path(__file__).parent.parent


def fixture(tmp_path):
    subprocess.run(["cmd", "/c", "mklink", "/J", str(tmp_path / ".venv"), str(REPO_ROOT / ".venv")])
"""

SANDBOXED = """
import os


def fixture(tmp_path):
    os.symlink(tmp_path / "real", tmp_path / "alias")
"""

EXEMPTED = """
import os

REPO_ROOT = Path(__file__).parent.parent


def fixture(tmp_path):
    # link-target-outside-tmp: points at a read-only fixture corpus that is never
    # deleted by the test and lives outside tmp on purpose
    os.symlink(REPO_ROOT / "corpus", tmp_path / "alias")
"""


def _check(monkeypatch, tmp_path, body: str) -> list[str]:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(body, encoding="utf-8")
    monkeypatch.setattr(chk, "ROOT", tmp_path)
    monkeypatch.setattr(chk, "TESTS", tests)
    return chk.findings()


def test_a_junction_to_the_repo_is_reported(monkeypatch, tmp_path):
    hits = _check(monkeypatch, tmp_path, DESTRUCTIVE)

    assert len(hits) == 1
    assert "test_sample.py" in hits[0]


def test_a_link_inside_tmp_is_fine(monkeypatch, tmp_path):
    assert _check(monkeypatch, tmp_path, SANDBOXED) == []


def test_an_exemption_with_a_real_reason_is_honoured(monkeypatch, tmp_path):
    assert _check(monkeypatch, tmp_path, EXEMPTED) == []


def test_a_thin_reason_does_not_buy_the_exemption(monkeypatch, tmp_path):
    thin = EXEMPTED.replace(
        "points at a read-only fixture corpus that is never\n    # deleted by the test and "
        "lives outside tmp on purpose",
        "fine",
    )

    assert _check(monkeypatch, tmp_path, thin) != []


def test_a_file_that_will_not_parse_is_skipped_not_crashed(monkeypatch, tmp_path):
    assert _check(monkeypatch, tmp_path, "def (((\n") == []


def test_this_checkout_is_clean():
    """The regression guard. Red on the fixture that ate the venv."""
    hits = chk.findings()

    assert hits == [], (
        f"tests creating links out of their sandbox: {hits}. A junction is not a copy "
        "and pytest's temp cleanup walks it — this repo lost a virtualenv that way."
    )
