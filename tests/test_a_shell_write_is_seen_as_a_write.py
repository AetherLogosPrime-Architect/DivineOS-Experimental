"""A file written from the shell must score exactly as the same file written by a tool.

Andrew asked for the build flow wired and enforced. It was, and then Aria's
session was switched into shell-writing mode partway through an exchange about
this gap and she wrote the letter describing it THROUGH the gap. Mine was in the
same mode. The assessor keyed every path feature on the four file-editing tools,
so a redirect or heredoc writing the identical file matched nothing, scored
zero, and every gate downstream stayed silent.

THE INVARIANT IS PARITY, not a list of things that should fire. Asserting "this
command must raise gravity" encodes my guess about which paths matter; asserting
"the shell write scores what the tool write scores" encodes the actual property,
and keeps holding when the path features change. My first probe got this wrong:
it expected a write to a plain test file to fire, and the tool path does not
fire there either. The code was right and the expectation was mine.
"""

from __future__ import annotations

import pytest

from divineos.core.gravity_classifier import _shell_write_targets, score_substrate_modification


def _shell(cmd: str):
    return score_substrate_modification("Bash", (), cmd)


def _tool(path: str):
    return score_substrate_modification("Write", (path,), "")


class TestParityWithTheToolPath:
    """The same file, written two ways, must be judged the same."""

    @pytest.mark.parametrize(
        ("command", "path"),
        [
            ("cat > src/divineos/core/foo.py <<EOF", "src/divineos/core/foo.py"),
            ("echo x >src/divineos/core/bar.py", "src/divineos/core/bar.py"),
            ("echo x >> .claude/hooks/thing.sh", ".claude/hooks/thing.sh"),
            ("sed -i s/a/b/ src/divineos/core/bar.py", "src/divineos/core/bar.py"),
            ("echo x | tee tests/test_x.py", "tests/test_x.py"),
            ('cd "C:/repo" && cat > src/divineos/x.py <<EOF', "src/divineos/x.py"),
        ],
    )
    def test_shell_write_scores_like_a_tool_write(self, command: str, path: str) -> None:
        assert _shell(command).fired_features == _tool(path).fired_features

    def test_the_source_case_actually_fires(self) -> None:
        """Parity alone would pass if BOTH sides scored zero. This pins that
        the shared answer is a real fire, not a shared silence."""
        assert "edit-src-divineos" in _shell("cat > src/divineos/core/foo.py <<EOF").fired_features


class TestTheFingerprintNamesTheFileNotTheCommand:
    """A hole inside the repair, caught by reading the refusal rather than the
    diff. Once the assessor could see shell writes, the gate refused them
    correctly but named the edit by the COMMAND SHAPE -- so one walk filed
    against two words of shell would have cleared every heredoc write in the
    tree, with both the refusal and the walk looking correct in isolation."""

    @pytest.mark.parametrize(
        ("command", "path"),
        [
            ("cat > src/divineos/core/foo.py <<EOF", "src/divineos/core/foo.py"),
            ("echo x >> .claude/hooks/thing.sh", ".claude/hooks/thing.sh"),
            ('cd "C:/repo" && cat > src/divineos/x.py <<EOF', "src/divineos/x.py"),
        ],
    )
    def test_a_shell_write_fingerprints_like_a_tool_write(self, command: str, path: str) -> None:
        from divineos.core.council_required.types import fingerprint_for

        assert fingerprint_for("Bash", (), command) == fingerprint_for("Write", (path,), "")

    def test_two_different_files_do_not_share_a_fingerprint(self) -> None:
        """The actual failure: a command-shaped anchor gave both of these the
        same name, so one walk covered both."""
        from divineos.core.council_required.types import fingerprint_for

        a = fingerprint_for("Bash", (), "cat > src/divineos/core/a.py <<EOF")
        b = fingerprint_for("Bash", (), "cat > src/divineos/core/b.py <<EOF")
        assert a != b

    def test_a_command_that_writes_nothing_still_anchors_on_the_act(self) -> None:
        from divineos.core.council_required.types import fingerprint_for

        assert fingerprint_for("Bash", (), 'cd "C:/repo" && git commit -m x') == "bash:git commit"


class TestTalkingAboutAPathIsNotWritingOne:
    """Earned within a minute of shipping the first version, which used a regex
    over the raw string and fired on a probe command that merely NAMED those
    paths inside a quoted argument. A gate that fires on any command discussing
    a path is a gate that gets turned off."""

    @pytest.mark.parametrize(
        "command",
        [
            "grep -rn foo src/divineos",
            "python thing.py 2>/dev/null",
            "python -c \"open('src/divineos/x.py')\"",
            "echo writing to src/divineos/core/foo.py",
            "git log --oneline -- src/divineos/core/foo.py",
        ],
    )
    def test_no_write_detected(self, command: str) -> None:
        assert _shell_write_targets(command) == ()

    def test_a_write_outside_the_tree_is_seen_but_raises_nothing(self) -> None:
        """My second wrong expectation in the same file, and worth keeping as a
        distinction rather than a correction. Writing a scratch file IS a write
        and the detector says so. Whether it MATTERS is the path features' job,
        and they are silent because it is not in the tree. Detection and
        gravity are different questions; collapsing them is what made me
        write the assertion backwards."""
        assert _shell_write_targets("echo hi > /tmp/notes.txt") == ("/tmp/notes.txt",)
        assert _shell("echo hi > /tmp/notes.txt").fired_features == ()


class TestWhatItCannotSee:
    """Stated as tests so the gap is asserted rather than described. Each of
    these writes a file and scores zero, and that is KNOWN, not overlooked.
    If a later change closes one, this test fails and the note gets updated --
    which is the point: the boundary is checked, not remembered."""

    @pytest.mark.parametrize(
        "command",
        [
            "cp /tmp/prepared.py src/divineos/core/foo.py",
            "mv /tmp/prepared.py src/divineos/core/foo.py",
            "python write_it.py",
        ],
    )
    def test_still_invisible(self, command: str) -> None:
        assert _shell_write_targets(command) == ()

    def test_unreadable_is_not_the_same_answer_as_nothing_found(self) -> None:
        """The first version returned empty for BOTH, which is Aria's shape
        exactly: could-not-see and is-harmless arriving as the same small
        number. The repo's own silent-swallow check flagged it before either
        of us had to argue about it."""
        assert _shell_write_targets('cat > src/divineos/x.py <<"EOF') is None
        assert _shell_write_targets("grep -rn foo src/divineos") == ()

    def test_an_unreadable_command_fails_toward_scrutiny(self) -> None:
        """A blind spot that reports clean is the failure this whole change is
        about. An occasional false refusal on an oddly quoted command is loud
        and arguable; a permanent quiet hole is neither."""
        assert _shell('cat > src/divineos/x.py <<"EOF').is_council_required
