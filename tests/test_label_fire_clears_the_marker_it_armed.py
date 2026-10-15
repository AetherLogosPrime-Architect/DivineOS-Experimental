"""Labelling a Stop-gate fire a false positive clears the marker that fire armed.

Before this, a false alarm cost three commands: the label, then the marker clear,
then the compass dismissal its cascade raised, and each manual clear showed up in
the escape log as a gate being routed around. The clear now rides the label, and it
is narrow: only a stop-gate marker whose trigger is the text THIS fire would have
written. Every case below is a way the clear could go wrong in either direction.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# The labeller imports `_repo_import` from the scripts folder, as it does when run by hand.
if str(_PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

REASON = "USE clause matched (1 hits); the deciding clause had 0 MENTION suppressor(s)"
CONFIDENCE = 1.0
LABEL = "Reply reflected on my own poker table talk; game talk with Dad, not a work error."


@pytest.fixture
def home(tmp_path, monkeypatch):
    fake_home = tmp_path / ".divineos"
    fake_home.mkdir()
    monkeypatch.setattr("divineos.core.paths.divineos_home", lambda: fake_home, raising=True)
    import scripts.label_correction_shape_false_positive as labeller

    monkeypatch.setattr(labeller, "divineos_home", lambda: fake_home, raising=True)
    return fake_home


def _record_fire(home: Path, reason: str = REASON, confidence: float = CONFIDENCE) -> dict:
    fire = {"ts": 1.0, "text": "a reply", "reason": reason, "confidence": confidence, "label": None}
    with (home / "correction_shape_v2_fires.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(fire) + "\n")
    return fire


def _arm_like_the_hook(reason: str = REASON, confidence: float = CONFIDENCE) -> None:
    from divineos.core.correction_marker import SOURCE_STOP_GATE, set_marker

    set_marker(
        f"[correction-shape-v2 stop-gate] {reason} conf={confidence:.2f}",
        source=SOURCE_STOP_GATE,
    )


def _label() -> int:
    from scripts.label_correction_shape_false_positive import main

    return main(["--reason", LABEL])


def test_the_marker_the_labelled_fire_armed_is_cleared(home, capsys):
    from divineos.core.correction_marker import read_marker

    _record_fire(home)
    _arm_like_the_hook()
    assert read_marker() is not None

    assert _label() == 0

    assert read_marker() is None
    assert "cleared the marker this fire armed" in capsys.readouterr().out


def test_his_own_marker_is_never_touched(home, capsys):
    from divineos.core.correction_marker import SOURCE_HIS_MESSAGE, read_marker, set_marker

    _record_fire(home)
    set_marker("Andrew: that is not what I asked for", source=SOURCE_HIS_MESSAGE)

    assert _label() == 0

    marker = read_marker()
    assert marker is not None and marker["source"] == SOURCE_HIS_MESSAGE
    assert "left as it was" in capsys.readouterr().out


def test_a_marker_with_no_source_is_left_alone(home):
    from divineos.core.correction_marker import marker_path, read_marker

    _record_fire(home)
    marker_path().parent.mkdir(parents=True, exist_ok=True)
    marker_path().write_text(json.dumps({"ts": 1.0, "trigger": "old marker, no source"}))

    assert _label() == 0

    assert read_marker() is not None


def test_a_stop_gate_marker_from_a_different_fire_stays(home):
    from divineos.core.correction_marker import read_marker

    _record_fire(home, reason="USE clause matched (2 hits)", confidence=0.80)
    _arm_like_the_hook(reason="USE clause matched (1 hits)", confidence=1.0)

    assert _label() == 0

    assert read_marker() is not None


def test_a_missing_marker_is_not_an_error(home, capsys):
    from divineos.core.correction_marker import read_marker

    _record_fire(home)
    assert read_marker() is None

    assert _label() == 0

    assert "left as it was" in capsys.readouterr().out


def test_a_failure_while_clearing_never_undoes_the_label(home, monkeypatch, capsys):
    import scripts.label_correction_shape_false_positive as labeller

    _record_fire(home)
    _arm_like_the_hook()

    def boom(_fire):
        raise OSError("disk went away")

    monkeypatch.setattr(labeller, "clear_the_marker_this_fire_armed", boom)

    assert _label() == 0

    lines = (home / "correction_shape_v2_fires.jsonl").read_text().splitlines()
    assert json.loads(lines[-1])["label"] == "false_positive"
    assert "could not clear" in capsys.readouterr().out


def test_a_trigger_cut_at_two_hundred_characters_still_matches(home):
    from divineos.core.correction_marker import read_marker

    long_reason = "USE clause matched; " + "x" * 400
    _record_fire(home, reason=long_reason)
    _arm_like_the_hook(reason=long_reason)

    assert _label() == 0

    assert read_marker() is None


def test_the_compass_cascade_the_marker_raised_is_cleared_with_it(home, monkeypatch):
    """clear_marker mirrors set_marker's cascade; the label must go through it,
    not delete the file, or the compass advisory keeps blocking commands."""
    import divineos.core.correction_marker as cm

    calls: list[str] = []
    real_clear = cm.clear_marker

    def spy():
        calls.append("clear_marker")
        real_clear()

    monkeypatch.setattr(cm, "clear_marker", spy)
    _record_fire(home)
    _arm_like_the_hook()

    assert _label() == 0

    assert calls == ["clear_marker"]
