"""No doorman was watching the hour I spent ruling suspects out.

2026-09-14. Two hundred and thirty-nine letters appeared on my code branch on
origin and I hand-hunted the cause for about an hour — the letter auto-push
hook, the letter monitor, the other checkout, the forge's authorship field.
Every one of those was an honest measurement and every one was correct. The
answer was in the cross-substrate push log I built in August: four pushes
recorded that evening, all mine, and the sweep with no line at all. One query.

The two doormen I already own fire on WRITES. An investigation produces nothing
until it is finished, so the whole rule-out ran unwatched and the first artifact
appeared only once I was committed to a story.

The refusals below are the load-bearing half. This surface is advisory, and an
advisory surface dies by noise rather than by being switched off — so the tests
that matter most are the ones proving it stays quiet.
"""

from __future__ import annotations

import pytest

from divineos.core.hook_surfaces import (
    _EVENT_CLASS_STORES,
    investigation_start_surface,
)


def _payload(command: str, session: str = "s-test") -> dict:
    return {
        "tool_name": "Bash",
        "session_id": session,
        "tool_input": {"command": command},
    }


class TestTheQuestionsThatCostTheHour:
    """The exact commands I ran that evening, in the order I ran them."""

    @pytest.mark.parametrize(
        "command",
        [
            'gh api "repos/owner/repo/commits/1c20e3d1" --jq .author',
            'gh api "repos/owner/repo/events?per_page=20"',
            "git reflog show origin/aria/first-line-to-him",
            "git ls-remote origin refs/heads/aria/first-line-to-him",
        ],
    )
    def test_a_who_touched_this_ref_question_names_the_push_log(
        self, command, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        out = investigation_start_surface(_payload(command))
        assert out is not None
        assert "cross-substrate-events.jsonl" in out.output

    def test_a_what_is_running_question_names_the_hook_and_letter_logs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        out = investigation_start_surface(_payload("python -c 'psutil.process_iter()'"))
        assert out is not None
        assert "hook_timing.jsonl" in out.output
        assert "auto-push-letter.log" in out.output

    def test_it_never_refuses(self, tmp_path, monkeypatch):
        # Invariant one, from the walk. A gate that stops a search dictates an
        # outcome and gets switched off inside a day, at which point it guards
        # nothing. Refusal is outside this surface's specification entirely.
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        out = investigation_start_surface(_payload("git ls-remote origin"))
        assert out is not None
        assert out.refused is False


class TestOncePerClassPerSession:
    """Habituation is the cheapest attack on an advisory surface."""

    def test_the_second_question_of_the_same_class_is_silent(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        first = investigation_start_surface(_payload("git ls-remote origin", session="s-1"))
        second = investigation_start_surface(_payload("git reflog show origin/x", session="s-1"))
        assert first is not None
        assert second is None

    def test_a_different_class_still_speaks_in_the_same_session(self, tmp_path, monkeypatch):
        # Silencing the whole session on one fire would hide the second
        # instrument behind the first, which is the collapse this is against.
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        investigation_start_surface(_payload("git ls-remote origin", session="s-2"))
        other = investigation_start_surface(_payload("tasklist", session="s-2"))
        assert other is not None
        assert "hook_timing.jsonl" in other.output

    def test_a_new_session_hears_it_again(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        investigation_start_surface(_payload("git ls-remote origin", session="s-3"))
        later = investigation_start_surface(_payload("git ls-remote origin", session="s-4"))
        assert later is not None

    def test_an_unwritable_marker_speaks_twice_rather_than_going_silent(
        self, tmp_path, monkeypatch
    ):
        # The failure direction is chosen, not accidental. Saying it twice is a
        # far smaller fault than saying nothing, and saying nothing is the
        # fault this whole surface exists for.
        monkeypatch.delenv("HOME", raising=False)
        monkeypatch.delenv("USERPROFILE", raising=False)
        first = investigation_start_surface(_payload("git ls-remote origin", session="s-5"))
        second = investigation_start_surface(_payload("git ls-remote origin", session="s-5"))
        assert first is not None
        assert second is not None


class TestWhatItMustStayQuietFor:
    """A surface that speaks on ordinary work is one I stop reading."""

    @pytest.mark.parametrize(
        "command",
        [
            "git status",
            "git commit -m 'x'",
            "pytest tests/ -q",
            "git push origin my-branch",
            "cat docs/build_flow.md",
            "gh pr view 471 --json body",
        ],
    )
    def test_ordinary_commands_say_nothing(self, command, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        assert investigation_start_surface(_payload(command)) is None

    def test_a_non_bash_tool_says_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        payload = {"tool_name": "Read", "session_id": "s-6", "tool_input": {"command": "tasklist"}}
        assert investigation_start_surface(payload) is None

    def test_an_empty_command_says_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        assert investigation_start_surface(_payload("   ")) is None


class TestSilenceNeverAssertsCoverage:
    """Invariant two from the walk, pinned in the text itself."""

    def test_the_output_says_it_is_not_exhaustive(self, tmp_path, monkeypatch):
        # A quiet gate meaning could-not-tell is indistinguishable from one
        # meaning nothing-covers-this. The surface must say which it is, and
        # the only place it can say so is in what it prints when it does speak.
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        out = investigation_start_surface(_payload("git ls-remote origin"))
        assert out is not None
        assert "not exhaustive" in out.output.lower()

    def test_it_says_the_answer_may_be_an_absence(self, tmp_path, monkeypatch):
        # The thing that settled the real case was a MISSING line, not a name.
        # A reader who expects a culprit reads a complete log as a dead end.
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        out = investigation_start_surface(_payload("git ls-remote origin"))
        assert out is not None
        assert "absence" in out.output.lower()


class TestTheMapIsData:
    """Lovelace's surplus, held to exactly what was agreed and no further."""

    def test_every_class_names_at_least_one_store(self):
        for _cls, (question, stores) in _EVENT_CLASS_STORES.items():
            assert question
            assert stores

    def test_no_registry_or_query_command_was_built(self):
        # The walk named the general primitive and refused to build it: no
        # third caller exists. This pins the refusal so the surplus stays a
        # note for the next reader rather than machinery nobody calls.
        import divineos.core.hook_surfaces as mod

        assert not hasattr(mod, "event_class_registry")
        assert not hasattr(mod, "coverage_report")
