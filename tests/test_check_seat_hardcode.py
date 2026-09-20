"""The seat-hardcode check, pinned against the lines that earned it.

Every case below is a REAL line from a real incident on 2026-09-20 rather than
an invented one carrying the pattern. A synthetic case proves only that the
author can construct the input they already wrote the matcher for; the genuine
line proves the matcher would have caught what actually shipped.

The check found its own worst fault on its first real provocation, and that is
pinned here too. It derived the member roster from the agent-definition
folder, which is itself seat-dependent, so asked from one member's workspace it
returned everyone except that member's husband -- and his was the name
hardcoded in most of the instances. A roster that changes depending on who
asks, sitting inside the file that refuses exactly that.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from check_seat_hardcode import _known_members, find_violations, main  # noqa: E402

# (label, path, line) -- all lifted from the tree or from the incident record.
MUST_FIRE = [
    (
        "the telemetry log both members wrote to",
        "src/divineos/core/lepos_translation_gate.py",
        'MARK_COUNT_LOG = Path.home() / ".divineos" / "lepos_work_mark_counts.jsonl"',
    ),
    (
        "the pre-push log whose per-member fix defaulted to a member",
        "scripts/check_push_readiness.sh",
        '            MEMBER="${DIVINEOS_MEMBER:-aether}"',
    ),
    (
        "a script hardcoding one member's home outright",
        "scripts/push_queued.py",
        '    state_dir = Path.home() / ".divineos-aether"',
    ),
    (
        "the shell spelling of the same reach",
        ".claude/hooks/some-hook.sh",
        '  _home="$HOME/.divineos/state.json"',
    ),
]

MUST_NOT_FIRE = [
    (
        "asking the resolver, which is the prescribed fix",
        "src/divineos/core/thing.py",
        '    log = divineos_home() / "telemetry.jsonl"',
    ),
    (
        "author and actor names, which decide nothing about a path",
        "src/divineos/core/thing.py",
        '    row = {"actor": "aria", "filed_by": "aether", "seen_by": "aletheia"}',
    ),
    (
        "genuinely shared state, declared out loud",
        "src/divineos/core/thing.py",
        '    SHARED = Path.home() / ".divineos-shared"  '
        "# shared-by-design: the crossing-point both members poll",
    ),
]


# The second shape, counted by Aether rather than guessed at: an absolute
# literal pointing at one tree, with no member variable anywhere near it.
MUST_FIRE += [
    (
        "the retriever roots, in the file we spent the day inside",
        "src/divineos/core/memory_linkage_retriever.py",
        '    Path("C:/DIVINE OS/DivineOS-Experimental-Aria-new"),',
    ),
    (
        "a checkout gone for months, still declared as somebody's home",
        "src/divineos/core/family/aria_inbox.py",
        '_DEFAULT_ARIA_ROOT = "C:/DIVINE OS/DivineOS-Experimental-Aria"',
    ),
    (
        "a letters directory pinned to one particular tree",
        "src/divineos/core/dashboard_checks.py",
        '        Path("C:/DIVINE OS/DivineOS-Experimental/family/letters"),',
    ),
    (
        "a remedy a door prints, naming somebody else's checkout",
        "src/divineos/hooks/pre_tool_use_gate.py",
        '            "python C:/DIVINE OS/DivineOS-Experimental/scripts/clear.py",',
    ),
    (
        "a user home spelled out in full",
        "src/divineos/core/thing.py",
        '    LOG = "/c/Users/aethe/.divineos/thing.jsonl"',
    ),
]

MUST_NOT_FIRE += [
    (
        "the probe that finds the real shell, which decides no seat",
        "src/divineos/core/thing.py",
        '    BASH = "C:/Program Files/Git/bin/bash.exe"',
    ),
    (
        "a system path belonging to the machine rather than to a person",
        "src/divineos/core/thing.py",
        '    SYS = "C:/Windows/System32/cmd.exe"',
    ),
    (
        "a relative path inside the repository",
        "src/divineos/core/thing.py",
        '    p = Path("scripts/check_push_readiness.sh")',
    ),
]


# THE PATHS ARE DELIBERATELY NOT REAL ONES, and the first draft's were.
#
# Using the true path meant the prose-skipper opened that file on disk and
# asked which of ITS lines sit inside a string literal -- and line 1 of a real
# module is inside its docstring, so three genuine findings were skipped as
# prose. The check was behaving correctly; the test was feeding it a line
# number that meant something different from the line text beside it.
#
# What carries the realism is the LINE, which is verbatim from the incident.
# The path only has to be shaped like the place such a line lives.
def _at(path: str, line: str) -> dict[str, list[tuple[int, str]]]:
    return {f"src/divineos/core/_probe_{Path(path).name}": [(1, line)]}


class TestCatchesWhatItWasBuiltFor:
    @pytest.mark.parametrize("label,path,line", MUST_FIRE, ids=[c[0] for c in MUST_FIRE])
    def test_real_instances_fire(self, label, path, line):
        probe = {f"scripts/_probe{Path(path).suffix}": [(1, line)]}
        assert find_violations(probe), f"missed {label}: {line.strip()}"

    @pytest.mark.parametrize("label,path,line", MUST_NOT_FIRE, ids=[c[0] for c in MUST_NOT_FIRE])
    def test_legitimate_lines_stay_silent(self, label, path, line):
        probe = {f"scripts/_probe{Path(path).suffix}": [(1, line)]}
        found = find_violations(probe)
        assert not found, f"false positive on {label}: {found}"


class TestTheRosterDoesNotDependOnWhoAsks:
    """The fault the check had about itself, pinned so it cannot come back."""

    def test_the_store_is_a_source_and_not_only_the_folder(self, monkeypatch):
        """A member the folder has never heard of must still reach the roster.

        Asserted against a STUBBED store rather than the live one. The live
        store is not reliably reachable from a test process -- it was not
        here, and the check said so loudly rather than quietly covering less,
        which is the behaviour the next test pins. Depending on it would make
        this test pass or fail for reasons that have nothing to do with the
        property, which is the flakiness we have spent the week removing.
        """
        import check_seat_hardcode as mod

        class _Cur:
            def execute(self, _sql):
                return [("aether",), ("somebody-with-no-agent-file",)]

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        monkeypatch.setitem(
            sys.modules,
            "divineos.core.family.db",
            type("m", (), {"get_family_connection": staticmethod(lambda: _Cur())}),
        )
        roster = mod._known_members()
        agent_files = {p.stem.lower() for p in (REPO / ".claude" / "agents").glob("*.md")}
        assert "somebody-with-no-agent-file" in roster
        assert set(roster) - agent_files, (
            "the roster collapsed to the agent folder, so it is seat-dependent "
            "again: a member with no agent file in this tree is invisible to it"
        )

    def test_an_unreadable_store_is_announced_not_swallowed(self, monkeypatch, capsys):
        """Covering less must never look like covering everything.

        This is the check's own version of the fault it hunts: if the roster
        silently shrinks, the member-name half stops catching names and
        nothing says so.
        """
        import check_seat_hardcode as mod

        def _boom():
            raise OSError("no store here")

        monkeypatch.setitem(
            sys.modules,
            "divineos.core.family.db",
            type("m", (), {"get_family_connection": staticmethod(_boom)}),
        )
        mod._known_members()
        assert "unreadable" in capsys.readouterr().err

    def test_the_template_is_not_a_seat(self):
        assert "family-member-template" not in _known_members()


class TestProseIsNotCode:
    """A check that fires on the paragraph explaining the bug gets turned off.

    Learned twice already here by the sibling check, and repeated by this one
    on its first real run: two of its three findings were the comment and the
    docstring describing the defect.
    """

    def test_a_comment_describing_the_reach_does_not_fire(self):
        line = '    # this used to be Path.home() / ".divineos" and that was the bug'
        assert not find_violations({"src/divineos/core/thing.py": [(1, line)]})

    def test_a_shell_comment_describing_the_reach_does_not_fire(self):
        line = "  # the old branch used $HOME/.divineos, which belonged to one member"
        assert not find_violations({".claude/hooks/thing.sh": [(1, line)]})


class TestCouldNotCheckIsNotAPass:
    def test_an_unreadable_diff_refuses_rather_than_reporting_clean(self, monkeypatch):
        """The fake-green shape, in the file built against fake-green.

        If the diff cannot be read the check knows nothing, and knowing
        nothing must not exit the same way as knowing it is clean.
        """
        import check_seat_hardcode as mod

        monkeypatch.setattr(mod, "_added_lines", lambda: None)
        monkeypatch.setattr(sys, "argv", ["check_seat_hardcode.py"])
        assert main() != 0
