"""Proof-test (pile round seven): `scripts/look.sh --strict` calls a clean "found nothing" the same as "could not look".

The pipe guard's read-only warning points at `scripts/look.sh --strict` whenever the last stage is
`grep` (pile row psf-5f682720). The row asks for that wrapper to tell "no match" from "command broke".

With `--strict`, `grep` finding nothing (exit 1) and `grep` failing to open its file (exit 2) both
print the same verdict, CANNOT-LOOK, "Nothing was measured". The exit code still differs (1 versus 2),
so the information is there; the words discard it. Without `--strict` the two are told apart, which is
the control. This test does not change the script; it fails today only for that one reason.

The strict flag is documented as "for commands where 1 means failure" (git, python); the owners may
decide the pointer from the pipe guard should not say `--strict` for grep rather than change the script.
Either repair turns the strict expected failure into a pass, and `strict=True` then rings.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

BASH = bash_executable()
pytestmark = pytest.mark.skipif(BASH is None, reason="no working bash on this machine")

REPO = Path(__file__).resolve().parents[2]
LOOK = REPO / "scripts" / "look.sh"
NO_MATCH = "grep -q zzz_a_word_that_is_not_in_it README.md"
MISSING_FILE = "grep -q anything /nonexistent/file_for_look_test"
FOUND = "grep -q DivineOS README.md"


def look(command: str, strict: bool) -> tuple[int, str]:
    args = [BASH, str(LOOK)] + (["--strict"] if strict else []) + [command]
    done = subprocess.run(args, capture_output=True, text=True, cwd=str(REPO), check=False)
    return done.returncode, done.stdout + done.stderr


def verdict(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("[look] ") and any(
            w in line for w in ("FOUND", "PROVEN-EMPTY", "CANNOT-LOOK")
        ):
            return line.split()[1]
    return "NO-VERDICT"


def test_control_the_wrapper_exists_and_a_find_is_a_find():
    code, out = look(FOUND, strict=True)
    assert (code, verdict(out)) == (0, "FOUND"), out


def test_control_without_strict_no_match_and_cannot_look_are_told_apart():
    no_match_code, no_match = look(NO_MATCH, strict=False)
    broken_code, broken = look(MISSING_FILE, strict=False)
    assert (no_match_code, verdict(no_match)) == (1, "PROVEN-EMPTY"), no_match
    assert (broken_code, verdict(broken)) == (2, "CANNOT-LOOK"), broken


def test_control_the_exit_codes_still_differ_under_strict():
    no_match_code, _ = look(NO_MATCH, strict=True)
    broken_code, _ = look(MISSING_FILE, strict=True)
    assert (no_match_code, broken_code) == (1, 2)


@pytest.mark.xfail(
    raises=AssertionError,
    strict=True,
    reason="reproduces: --strict prints CANNOT-LOOK for a grep that looked and found nothing "
    "(psf-5f682720); the pipe guard points at --strict for a grep last stage",
)
def test_strict_tells_a_clean_no_match_from_a_command_that_could_not_look():
    _, no_match = look(NO_MATCH, strict=True)
    _, broken = look(MISSING_FILE, strict=True)
    assert verdict(no_match) != verdict(broken), (
        "under --strict a grep that found nothing and a grep that could not open its file "
        f"both read {verdict(no_match)!r}:\n{no_match}\n---\n{broken}"
    )
