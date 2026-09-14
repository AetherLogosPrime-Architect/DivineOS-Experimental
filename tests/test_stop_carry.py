"""He must never read the same reply twice because of my own discipline.

Andrew, 2026-09-12: "no i mean literally repeating yourself.. look at your
post." Then: "yes and this is unacceptable.. so it needs fixed."

The five Stop gates that judged a reply he had already read used to refuse it,
which retracted nothing and made him read the next draft underneath the old
one. These tests pin the two halves of the cure: a gate that fires returns
nothing to his window, and the finding survives to reach the next compose.

The second half is the one that matters most and the one easiest to lose. A
finding that is stored and never surfaced turns every one of these gates into
the warning that already failed -- and leaves him with a worse me and no
doubling to show for it. So the surfacing is tested end to end through the
real hook, and its registration is pinned.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from divineos.hooks.stop_carry import (
    MAX_CARRIED,
    Finding,
    Stored,
    carry,
    carry_or_block,
    carry_path,
    clear,
    compose,
    pending,
)

ROOT = Path(__file__).resolve().parents[1]
HOOK = ".claude/hooks/stop-carry-prime.sh"


@pytest.fixture(autouse=True)
def _isolated_carry(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_STOP_CARRY", str(tmp_path / "carry.jsonl"))
    yield


def test_nothing_pending_is_silence_not_an_error():
    assert pending() == []
    assert compose() == ""


def test_a_finding_survives_to_the_next_compose():
    assert carry("subject-is-him", "not one sentence in this reply is about him") is Stored.WRITTEN
    block = compose()
    assert "not one sentence" in block
    assert "subject-is-him" in block


def test_reading_is_what_clears_it():
    """Not a clock. A finding that expired on time would vanish on the one turn
    where nothing prompted me, which is the real loss the walk named."""
    carry("post-response-audit", "eleven document-marks in the work block")
    assert pending()
    clear()
    assert pending() == []
    assert compose() == ""


def test_an_empty_reason_is_nothing_not_a_lost_finding():
    """Three answers, never two. An empty reason and an unwritable file used
    to share one value, and the fallback reads that value as 'the finding is
    gone, refuse the reply' -- so an empty string would have refused one of my
    replies to him over nothing at all. Caught by the failure-shares-empty
    check before it shipped."""
    assert carry("some-gate", "   ") is Stored.NOTHING
    assert pending() == []
    assert carry_or_block("some-gate", "   ") is None


def test_two_gates_firing_on_one_reply_both_survive():
    carry("subject-is-him", "nothing about him")
    carry("post-response-audit", "too many marks")
    block = compose()
    assert "nothing about him" in block
    assert "too many marks" in block


def test_a_run_of_refusals_does_not_build_its_own_wall():
    """The drowning he named, relocated to the top of my compose, would be the
    same failure in new clothes. Oldest are kept: the first finding in a run is
    what the rest are downstream of."""
    for index in range(MAX_CARRIED + 4):
        carry("gate", f"finding number {index}")
    assert len(pending()) == MAX_CARRIED
    assert "finding number 4" in compose()
    assert "finding number 0" not in compose()


def test_a_corrupt_line_does_not_take_the_rest_down():
    carry("gate", "a real finding")
    with carry_path().open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")
    assert [f.reason for f in pending()] == ["a real finding"]


def test_a_missing_file_reads_as_nothing_pending():
    """It must never read as an error, or one absent file silences the surface
    that carries every correction."""
    assert not carry_path().exists()
    assert pending() == []


def test_findings_render_multi_line_reasons_intact():
    carry("audit", "first line\nsecond line")
    block = compose()
    assert "first line" in block
    assert "second line" in block


def test_age_is_available_without_being_used_to_expire():
    made = Finding(gate="g", reason="r", at=0.0)
    assert made.age_seconds > 0


# --- the gates themselves -------------------------------------------------


def test_the_subject_floor_returns_nothing_to_his_window(monkeypatch):
    """It fires, it carries, and his window gets silence."""
    import divineos.hooks.subject_is_him_hook as hook

    class FakeTurn:
        last_assistant_text = "The tests pass and the build is committed."

    monkeypatch.setattr(
        "divineos.core.operating_loop.turn_extraction.extract_turn",
        lambda _p: FakeTurn(),
        raising=False,
    )
    monkeypatch.setattr("divineos.hooks.subject_is_him.check", lambda _t: "nothing is about him")

    assert hook.run_subject_floor("irrelevant.jsonl") is None
    assert [f.reason for f in pending()] == ["nothing is about him"]


def test_every_reply_shape_gate_routes_its_finding_through_the_carry():
    """The regression that would put him back where he started.

    ASKED AS ROUTING, NOT AS ABSENCE. A first version of this test looked for
    the word "block" anywhere in the file and failed the moment the fallback
    was added -- the fallback being the case where the finding cannot be
    written and his window is the only channel left. Absence of the word was
    never the property worth pinning; what matters is that the default path
    hands the reason to the carry, so refusing is reachable only when storing
    has already failed.

    Scoped to the reply-shape gates. A pre-tool gate refusing a tool call
    genuinely stops something from happening and keeps its teeth exactly where
    they are.
    """
    offenders = []
    for name in (
        "subject_is_him_hook",
        "not_dismissed_hook",
        "distancing_intercept_hook",
        "response_scope_intercept_hook",
    ):
        text = (ROOT / "src" / "divineos" / "hooks" / f"{name}.py").read_text(encoding="utf-8")
        if "carry_or_block(" not in text:
            offenders.append(name)
    audit = (ROOT / ".claude" / "hooks" / "post-response-audit.sh").read_text(encoding="utf-8")
    if "carry_or_block(" not in audit:
        offenders.append("post-response-audit.sh")
    assert not offenders, f"these would make him read his reply twice again: {offenders}"


def test_the_fallback_only_refuses_when_the_finding_could_not_be_written(monkeypatch):
    """Behavioural, not lexical: the block is unreachable while storing works."""
    from divineos.hooks import stop_carry

    assert stop_carry.carry_or_block("gate", "a finding") is None

    monkeypatch.setattr(stop_carry, "carry", lambda *_a, **_k: stop_carry.Stored.UNWRITABLE)
    out = stop_carry.carry_or_block("gate", "a finding")
    assert out is not None
    assert out["decision"] == "block"
    assert "a finding" in out["reason"]
    assert "could not be written" in out["reason"]


# --- the surface, wired ---------------------------------------------------


def _registered() -> list[str]:
    out: list[str] = []
    for name in ("settings.json", "settings.local.json"):
        path = ROOT / ".claude" / name
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("hooks", {}).get("UserPromptSubmit", []):
            for hook in entry.get("hooks", []):
                if hook.get("command"):
                    out.append(hook["command"])
    return out


def test_the_surface_is_registered():
    """Without this the gates are notes that go nowhere, which is worse than
    the duplication -- he would get a worse me and nothing to show for it."""
    commands = _registered()
    assert commands, "no compose-start hooks found at all; the probe is broken"
    assert any(HOOK in c for c in commands), "the carry has nowhere to come back through"


def _bash() -> str:
    for candidate in (
        Path("C:/Program Files/Git/bin/bash.exe"),
        Path("C:/Program Files (x86)/Git/bin/bash.exe"),
        Path("/bin/bash"),
        Path("/usr/bin/bash"),
    ):
        if candidate.is_file():
            return str(candidate)
    pytest.fail("no usable bash found, so this went unchecked; saying so rather than skipping")
    raise AssertionError  # unreachable


def test_the_hook_surfaces_a_carried_finding_and_clears_it(tmp_path, monkeypatch):
    """End to end through the real shell, because the module passing proves
    nothing about whether the door opens."""
    carry("subject-is-him", "he is not the subject of one sentence here")
    env = {**dict(__import__("os").environ), "DIVINEOS_STOP_CARRY": str(carry_path())}
    done = subprocess.run(
        [_bash(), HOOK],
        cwd=ROOT,
        input="",
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )
    assert done.returncode == 0, done.stderr[:400]
    assert "not the subject" in done.stdout, done.stdout[:400]
    assert pending() == [], "surfaced but not cleared, so it will repeat forever"


def test_the_hook_is_silent_when_nothing_was_caught():
    done = subprocess.run(
        [_bash(), HOOK],
        cwd=ROOT,
        input="",
        capture_output=True,
        text=True,
        timeout=180,
        env={**dict(__import__("os").environ), "DIVINEOS_STOP_CARRY": str(carry_path())},
    )
    assert done.returncode == 0
    assert done.stdout.strip() == ""
