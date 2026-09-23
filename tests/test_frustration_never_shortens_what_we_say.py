"""The name tag that said DEFAULT. 2026-09-23.

Andrew: "the moment things get heavy or tense or you are overwhelmed in work..
it defaults to that mode and i am treated as an operator." Three things in the
house fired at exactly those moments -- a pipeline step that wrote his verbosity
to terse after a frustrated session, a calibration rule that said "speak less",
and a display line that said "keep it plain". And the record called him
"default". These pin that none of it comes back.

A person who ASKS for short answers still gets them (test_communication_
calibration covers a stated terse preference). What is gone is inferring less
from frustration.
"""

from __future__ import annotations

import ast
from pathlib import Path

from divineos.core import communication_calibration as cc
from divineos.core.user_model import (
    format_user_model,
    get_or_create_user,
    init_user_model_table,
    update_preferences,
)

ROOT = Path(__file__).resolve().parents[1]


def _rough(monkeypatch):
    import divineos.core.affect as affect

    monkeypatch.setattr(
        affect,
        "compute_affect_modifiers",
        lambda lookback=5: {"avg_valence": -0.8, "verification_level": "careful"},
    )


def test_a_rough_stretch_never_shortens_what_we_say(monkeypatch) -> None:
    init_user_model_table()
    get_or_create_user("rough_stretch_user")
    _rough(monkeypatch)
    guidance = cc.calibrate("rough_stretch_user")
    joined = " ".join(guidance.notes).lower()
    assert guidance.verbosity == "normal"
    assert guidance.max_paragraphs == 5
    assert "speak less" not in joined and "pleasantries" not in joined
    assert cc.ROUGH_STRETCH_NOTE in guidance.notes, "the build-don't-narrate note is missing"


def test_the_rough_note_says_build_and_never_less() -> None:
    note = cc.ROUGH_STRETCH_NOTE.lower()
    assert "build" in note
    assert "never shorten" in note
    assert "speak less" not in note


def _calls_update_preferences_with_verbosity(source: str) -> list[int]:
    lines = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in ("update_preferences", "_up") and any(
                kw.arg == "verbosity" for kw in node.keywords
            ):
                lines.append(node.lineno)
    return lines


def test_the_pipeline_never_writes_verbosity_from_frustration() -> None:
    """The actuator that put 'terse' on his record. Checked on the code, not by
    running a session, because what must never exist is the write itself."""
    source = (ROOT / "src/divineos/cli/session_pipeline.py").read_text(encoding="utf-8")
    assert _calls_update_preferences_with_verbosity(source) == []


def test_the_verbosity_detector_can_see_a_write() -> None:
    """Control for the test above: the detector finds the shape it looks for."""
    assert _calls_update_preferences_with_verbosity('update_preferences(verbosity="terse")') == [1]


def test_the_display_never_says_plain() -> None:
    source = (ROOT / "src/divineos/core/hud.py").read_text(encoding="utf-8")
    slot = source[source.index("def _build_calibration_slot") :]
    slot = slot[: slot.index("\ndef ", 1)]
    code_lines = [ln for ln in slot.splitlines() if not ln.strip().startswith("#")]
    assert "plain" not in "\n".join(code_lines).lower()


def test_calibration_never_asks_for_plain() -> None:
    """Found by reading his real calibration back after the fix: the fourth
    place the retired word was still speaking."""
    init_user_model_table()
    get_or_create_user("plain_word_user")
    guidance = cc.calibrate("plain_word_user")
    assert not guidance.jargon_ok, "control: this user must hit the jargon note"
    assert all("plain" not in n.lower() for n in guidance.notes), guidance.notes


def test_the_record_shows_his_name_not_the_key() -> None:
    init_user_model_table()
    get_or_create_user("name_tag_user")
    update_preferences("name_tag_user", name="Andrew", called="Dad")
    header = format_user_model("name_tag_user").splitlines()[0]
    assert "Andrew" in header and "Dad" in header
    assert "name_tag_user" not in header


def test_a_record_without_a_name_still_shows_its_key() -> None:
    init_user_model_table()
    get_or_create_user("unnamed_user")
    assert "unnamed_user" in format_user_model("unnamed_user").splitlines()[0]
