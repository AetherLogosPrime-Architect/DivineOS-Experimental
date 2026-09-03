"""The detector that finds code guessing where a member's state lives.

The fault it catches has the worst available failure shape: the write lands
somewhere real that nothing reads, and the tool prints success. Six weeks,
ninety orphaned files, and a cheerful message every time.

Most of these tests are about the detector NOT firing, and that is deliberate.
Its first real run produced sixty-nine hits of which seven were genuine --
other branches checked out on disk counted six times over, and docstrings
describing the very defect counted as the defect. A detector whose output is
mostly noise is one people learn to scroll past, which catches nothing at all,
so the noise cases are pinned as hard as the signal.

The absence-assertions carry a known weakness: a checker that silently stopped
scanning would satisfy every one of them. That is why the three distinct exit
states and the clean-line naming how much was examined are pinned here too --
an empty scan must never be reportable as a clean one.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_member_home_rebuilt import (  # noqa: E402
    EXIT_CLEAN,
    EXIT_COULD_NOT_SCAN,
    EXIT_FOUND,
    hits_in,
    main,
)


def _write(root: Path, name: str, body: str) -> Path:
    p = root / name
    p.write_text(body, encoding="utf-8")
    return p


class TestWhatItCatches:
    def test_a_python_member_home_built_from_a_variable(self, tmp_path):
        p = _write(tmp_path, "x.py", 'home = Path.home() / f".divineos-{member}"\n')
        assert hits_in(p) == [(1, 'home = Path.home() / f".divineos-{member}"')]

    def test_a_shell_member_home_built_from_a_variable(self, tmp_path):
        p = _write(tmp_path, "x.sh", 'MARKER="$HOME/.divineos-$MEMBER/kill.disabled"\n')
        assert len(hits_in(p)) == 1


class TestWhatItDeliberatelyIgnores:
    def test_the_literal_default_home_is_not_a_finding(self, tmp_path):
        # Correct in dozens of places. The fault needs the member to be
        # DYNAMIC, because that is what makes the aether exception reachable.
        p = _write(tmp_path, "x.py", 'home = Path.home() / ".divineos"\n')
        assert hits_in(p) == []

    def test_a_comment_describing_the_defect_is_not_the_defect(self, tmp_path):
        p = _write(tmp_path, "x.py", '# was Path.home() / f".divineos-{member}", now fixed\n')
        assert hits_in(p) == []

    def test_prose_quoting_the_old_path_is_not_the_defect(self, tmp_path):
        # This repository is full of docstrings describing the six-week split.
        # A detector that flags the write-up of its own history is one nobody
        # trusts by the third read.
        body = '    """Was ``Path.home() / f".divineos-{member}"`` before."""\n'
        assert hits_in(_write(tmp_path, "x.py", body)) == []

    def test_a_site_declaring_itself_unrouted_is_left_alone(self, tmp_path):
        # core/instruments.py must build the unrouted path on purpose: it
        # compares both homes and prefers whichever holds the file, so routing
        # it would collapse the two candidates into one.
        body = (
            "def unrouted():\n"
            "    # member-home: unrouted on purpose\n"
            '    return Path.home() / f".divineos-{member}"\n'
        )
        assert hits_in(_write(tmp_path, "x.py", body)) == []

    def test_the_declaration_must_be_near_the_line_it_excuses(self, tmp_path):
        # Otherwise one declaration at the top of a file silently exempts every
        # later site, which is the blanket-exemption shape this replaces.
        body = (
            "# member-home: unrouted on purpose\n"
            + "x = 1\n" * 40
            + 'home = Path.home() / f".divineos-{member}"\n'
        )
        assert len(hits_in(_write(tmp_path, "x.py", body))) == 1


class TestItCannotLookLikeItRan:
    def test_a_non_repository_says_it_could_not_scan(self, tmp_path, capsys):
        assert main(["prog", str(tmp_path)]) == EXIT_COULD_NOT_SCAN
        assert "COULD NOT SCAN" in capsys.readouterr().out

    def test_an_empty_repository_is_not_reported_clean(self, tmp_path, capsys):
        # An empty scan and a clean scan are different answers, and confusing
        # them is the family of faults this whole session has been about.
        (tmp_path / ".git").mkdir()
        assert main(["prog", str(tmp_path)]) == EXIT_COULD_NOT_SCAN
        assert "not a clean one" in capsys.readouterr().out

    def test_a_clean_result_says_how_much_it_examined(self, tmp_path, capsys):
        (tmp_path / ".git").mkdir()
        _write(tmp_path, "ok.py", 'home = Path.home() / ".divineos"\n')
        assert main(["prog", str(tmp_path)]) == EXIT_CLEAN
        assert "file(s) examined" in capsys.readouterr().out

    def test_a_finding_names_the_file_the_line_and_the_remedy(self, tmp_path, capsys):
        (tmp_path / ".git").mkdir()
        _write(tmp_path, "bad.py", 'home = Path.home() / f".divineos-{member}"\n')
        assert main(["prog", str(tmp_path)]) == EXIT_FOUND
        out = capsys.readouterr().out
        assert "bad.py:1" in out
        assert "member_home" in out

    def test_the_three_exit_codes_are_distinct(self):
        assert len({EXIT_CLEAN, EXIT_FOUND, EXIT_COULD_NOT_SCAN}) == 3


class TestScopedByBehaviourNotDirectory:
    def test_another_branch_checked_out_on_disk_is_not_scanned(self, tmp_path):
        # A worktree is a different BRANCH on disk. Its copies cannot be fixed
        # from here, and counting them multiplied the first real run by six.
        (tmp_path / ".git").mkdir()
        wt = tmp_path / "worktrees" / "other"
        wt.mkdir(parents=True)
        _write(wt, "bad.py", 'home = Path.home() / f".divineos-{member}"\n')
        _write(tmp_path, "ok.py", "x = 1\n")
        assert main(["prog", str(tmp_path)]) == EXIT_CLEAN

    def test_a_hook_directory_is_scanned_like_any_other(self, tmp_path):
        # The August sweep was scoped by directory and missed three sites for
        # exactly this reason. Nothing is exempt for living somewhere.
        (tmp_path / ".git").mkdir()
        hooks = tmp_path / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        _write(hooks, "gate.sh", 'M="$HOME/.divineos-$MEMBER/x.disabled"\n')
        assert main(["prog", str(tmp_path)]) == EXIT_FOUND
