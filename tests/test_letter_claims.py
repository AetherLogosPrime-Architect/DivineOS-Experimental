"""Tests for the letter-claims surface.

The load-bearing test is `test_it_would_have_caught_the_stumble_it_was_built_for`.
This module exists because I nearly agreed with a sibling's bug report on faith;
what saved me was having the file open for an unrelated reason. If the module
cannot answer for a bare filename - which is how siblings actually name shared
files in prose - it does not do the thing it was built to do. The first version
could not, and reported one incidental file with confidence instead.
"""

from __future__ import annotations

import subprocess

import pytest

from divineos.core import letter_claims as lc


class TestExtraction:
    def test_finds_paths_and_bare_filenames(self):
        found = lc.extract_paths("see `scripts/foo.py` and also divineos.cmd for this")
        assert "scripts/foo.py" in found and "divineos.cmd" in found

    def test_prose_slashes_are_not_paths(self):
        assert lc.extract_paths("he/she said and/or maybe not") == []

    def test_letters_are_ignored(self):
        """A letter quoting its own filename is noise, not a finding."""
        assert lc.extract_paths("see letters/aether-to-aria-2026-01-01-x.md") == []

    def test_each_path_appears_once(self):
        assert lc.extract_paths("a.py and a.py again") == ["a.py"]


class TestReading:
    @pytest.fixture
    def repo(self, tmp_path):
        root = tmp_path / "repo"
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "shim.cmd").write_text("@echo off\n")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "add shim"],
            cwd=root,
            check=True,
        )
        return root

    def test_it_would_have_caught_the_stumble_it_was_built_for(self, repo, tmp_path):
        """A bare filename in prose must resolve. This is the whole point.

        Aether named `divineos.cmd`, not `scripts/divineos.cmd`, because that
        is how you say it out loud. Literal-path-only resolution missed both
        files the letter was actually about.
        """
        letter = tmp_path / "note.md"
        letter.write_text("shim.cmd swallows exit codes and I fixed it")
        reading = lc.read_letter(letter, repo)
        assert [s.mentioned for s in reading.measured] == ["shim.cmd"]
        assert reading.measured[0].by_basename is True
        assert "add shim" in reading.measured[0].last_commit

    def test_the_same_file_named_twice_is_one_finding(self, repo, tmp_path):
        letter = tmp_path / "n.md"
        letter.write_text("scripts/shim.cmd is broken, i.e. shim.cmd is broken")
        assert len(lc.read_letter(letter, repo).measured) == 1

    def test_ambiguous_basename_says_so_rather_than_guessing(self, repo, tmp_path):
        """A confident answer about the wrong file is worse than no answer,
        because it looks like evidence."""
        (repo / "scripts" / "sub").mkdir()
        (repo / "scripts" / "sub" / "shim.cmd").write_text("x")
        letter = tmp_path / "n.md"
        letter.write_text("shim.cmd is broken")
        reading = lc.read_letter(letter, repo)
        assert reading.measured == []
        assert "more than one file" in reading.states[0].unlooked

    def test_unknown_file_is_silent_not_an_error(self, repo, tmp_path):
        letter = tmp_path / "n.md"
        letter.write_text("nothing_here.py is fine")
        reading = lc.read_letter(letter, repo)
        assert reading.measured == [] and lc.render(reading) == ""

    def test_unreadable_letter_reports_could_not_look(self, repo, tmp_path):
        reading = lc.read_letter(tmp_path / "missing.md", repo)
        assert reading.states and "could not read the letter" in reading.states[0].unlooked

    def test_render_names_could_not_look_distinctly(self, repo, tmp_path):
        (repo / "scripts" / "sub").mkdir()
        (repo / "scripts" / "sub" / "shim.cmd").write_text("x")
        letter = tmp_path / "n.md"
        letter.write_text("shim.cmd is broken")
        out = lc.render(lc.read_letter(letter, repo))
        assert "COULD NOT LOOK" in out and "not 'nothing to see'" in out


class TestSurface:
    def _p(self, path):
        return {"tool_name": "Read", "tool_input": {"file_path": path}}

    def test_ignores_non_read_tools(self):
        from divineos.core.hook_surfaces import letter_claims_surface

        assert letter_claims_surface({"tool_name": "Edit", "tool_input": {}}) is None

    def test_ignores_files_outside_the_letter_channel(self):
        from divineos.core.hook_surfaces import letter_claims_surface

        assert letter_claims_surface(self._p("/repo/src/divineos/core/x.py")) is None

    def test_ignores_my_own_outgoing_letters(self):
        """My draft is not evidence about my own tree."""
        from divineos.core.hook_surfaces import letter_claims_surface

        assert letter_claims_surface(self._p("/x/letters/aria-to-aether-2026-01-01-a.md")) is None
