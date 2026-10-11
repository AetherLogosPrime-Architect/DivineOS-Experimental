"""The body keeps a memory history and judges it with the controls Aria's spec asks for.

Born 2026-10-11: the push queue stalled on "needs 4.5 GB free" while `divineos body` said
"36% used" the whole time, because ~14 GB was held in kernel pool by no program and the body
read only total used and free. These tests pin the sense that was missing: a gap number, a
history, and verdicts that cannot lie (boot scans, stale files, single mixed numbers).

Readings here are plain dataclasses written to a temp file; nothing mocks the judge itself.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict

import pytest

from divineos.core import body_memory as bm

NOW = 1_800_000_000.0
BOOT = NOW - 6 * 3600  # booted six hours ago: well past the boot-scan window


def _reading(ts, gap=0.2, nonpaged=0.8, boot=BOOT):
    return bm.Reading(
        ts=ts,
        boot_ts=boot,
        total_gb=31.2,
        available_gb=20.0,
        programs_gb=11.0,
        gap_gb=gap,
        nonpaged_gb=nonpaged,
        paged_gb=1.4,
    )


def _levels(notes):
    return [n.level for n in notes]


def test_a_flat_series_does_not_warn():
    readings = [_reading(NOW - 600 * i, gap=0.3) for i in (3, 2, 1, 0)]
    notes = bm.assess(readings, now=NOW)
    assert "warn" not in _levels(notes)
    assert any(n.level == "ok" for n in notes)


def test_a_gap_rising_across_three_readings_above_the_floor_warns():
    readings = [
        _reading(NOW - 3600, gap=3.4),
        _reading(NOW - 1800, gap=5.0),
        _reading(NOW, gap=8.0),
    ]
    notes = bm.assess(readings, now=NOW)
    warned = [n for n in notes if n.level == "warn"]
    assert warned and "held by no program" in warned[0].text


def test_a_big_but_flat_gap_does_not_warn_for_rising():
    readings = [_reading(NOW - 1200, gap=4.0), _reading(NOW - 600, gap=4.0), _reading(NOW, gap=4.0)]
    assert "warn" not in _levels(bm.assess(readings, now=NOW))


def test_a_rising_gap_below_the_floor_does_not_warn():
    readings = [_reading(NOW - 1200, gap=0.2), _reading(NOW - 600, gap=0.9), _reading(NOW, gap=1.8)]
    assert "warn" not in _levels(bm.assess(readings, now=NOW))


def test_three_readings_seconds_apart_with_a_wobble_do_not_warn():
    """Aria's cold read of 624: three `divineos body` runs in a minute can trip a rising rule."""
    readings = [
        _reading(NOW - 20, gap=4.00),
        _reading(NOW - 10, gap=4.01),
        _reading(NOW, gap=4.02),
    ]
    assert "warn" not in _levels(bm.assess(readings, now=NOW))


def test_a_rise_too_small_over_a_long_span_does_not_warn():
    readings = [
        _reading(NOW - 7200, gap=4.00),
        _reading(NOW - 3600, gap=4.10),
        _reading(NOW, gap=4.20),
    ]
    assert "warn" not in _levels(bm.assess(readings, now=NOW))


def test_a_real_rise_over_the_minimum_span_warns():
    readings = [
        _reading(NOW - 1800, gap=4.0),
        _reading(NOW - 900, gap=4.2),
        _reading(NOW, gap=4.4),
    ]
    assert "warn" in _levels(bm.assess(readings, now=NOW))


def test_unreadable_programs_are_named_in_the_report(tmp_path, monkeypatch):
    """An unreadable program makes the gap look larger, so the report must say how many."""
    unreadable = bm.Reading(**{**asdict(_reading(NOW)), "unreadable": 7})
    monkeypatch.setattr(bm, "take_reading", lambda: unreadable)
    text = bm.memory_sense_report(path=tmp_path / "r.jsonl", tags_path=tmp_path / "t.json")
    assert "7 programs could not be read" in text


def test_old_history_lines_without_the_new_field_still_load(tmp_path):
    path = tmp_path / "readings.jsonl"
    line = {k: v for k, v in asdict(_reading(NOW)).items() if k != "unreadable"}
    path.write_text(json.dumps(line) + "\n", encoding="utf-8")
    assert len(bm.load_readings(path)) == 1


def test_a_broken_memory_sense_says_unavailable_in_the_body_command(monkeypatch):
    """Silence reads as 'nothing to report', so a failing sense must print why (Aria, 624)."""
    import click
    from click.testing import CliRunner

    from divineos.cli import body_commands

    def broken():
        raise RuntimeError("pool call failed")

    monkeypatch.setattr(bm, "memory_sense_report", broken)
    group = click.Group()
    body_commands.register(group)
    result = CliRunner().invoke(group, ["body"])
    assert "[unavailable: RuntimeError: pool call failed]" in result.output


def test_nonpaged_pool_above_the_floor_warns_on_its_own():
    notes = bm.assess([_reading(NOW, nonpaged=2.6)], now=NOW)
    assert "warn" in _levels(notes)


def test_a_reading_near_boot_carries_the_boot_flag_and_no_verdict():
    boot = NOW - 5 * 60
    readings = [_reading(NOW, gap=9.0, nonpaged=3.0, boot=boot)]
    notes = bm.assess(readings, now=NOW)
    assert "warn" not in _levels(notes)
    assert any("boot scan may inflate this" in n.text for n in notes)


def test_readings_from_before_the_last_boot_are_not_compared():
    old_boot = NOW - 20 * 3600
    readings = [
        _reading(NOW - 7200, gap=3.4, boot=old_boot),
        _reading(NOW - 600, gap=5.0, boot=BOOT),
        _reading(NOW, gap=8.0, boot=BOOT),
    ]
    assert "warn" not in _levels(bm.assess(readings, now=NOW))


def test_an_old_latest_reading_says_stale_never_fine():
    notes = bm.assess([_reading(NOW - 10 * 3600)], now=NOW)
    assert any(n.level == "stale" for n in notes)
    assert "ok" not in _levels(notes)


def test_no_readings_says_so():
    notes = bm.assess([], now=NOW)
    assert _levels(notes) == ["stale"]


def test_tag_file_that_is_old_says_stale_and_gives_no_verdict():
    tags = {"ts": NOW - 3 * 3600, "idle_clean": True, "tags": {"File": 5}, "previous": {"File": 1}}
    notes = bm.assess([_reading(NOW)], now=NOW, tags=tags)
    tag_notes = [n for n in notes if "tag" in n.text.lower()]
    assert tag_notes and all(n.level in ("stale", "note") for n in tag_notes)


def test_tag_growth_with_a_clean_idle_window_warns():
    tags = {
        "ts": NOW - 60,
        "idle_clean": True,
        "tags": {"File": 5000, "IoFE": 100},
        "previous": {"File": 1000, "IoFE": 100},
    }
    notes = bm.assess([_reading(NOW)], now=NOW, tags=tags)
    warned = [n for n in notes if n.level == "warn"]
    assert warned and "File" in warned[0].text and "IoFE" not in warned[0].text


def test_tag_growth_without_a_clean_idle_window_is_not_a_finding():
    tags = {
        "ts": NOW - 60,
        "idle_clean": False,
        "tags": {"File": 5000},
        "previous": {"File": 1000},
    }
    notes = bm.assess([_reading(NOW)], now=NOW, tags=tags)
    assert "warn" not in _levels(notes)
    assert any("idle" in n.text.lower() for n in notes)


@pytest.mark.parametrize("body", ["[]", "7", '"text"', "{not json", ""])
def test_a_tag_file_that_is_not_an_object_gives_no_tags(tmp_path, body):
    path = tmp_path / "tags.json"
    path.write_text(body, encoding="utf-8")
    assert bm._load_tags(path) is None


def test_a_tag_file_that_is_an_object_is_read(tmp_path):
    path = tmp_path / "tags.json"
    path.write_text('{"ts": 1, "tags": {}}', encoding="utf-8")
    assert bm._load_tags(path) == {"ts": 1, "tags": {}}


def test_history_round_trips_through_the_file(tmp_path):
    path = tmp_path / "readings.jsonl"
    first, second = _reading(NOW - 600), _reading(NOW)
    bm.append_reading(first, path)
    bm.append_reading(second, path)
    assert bm.load_readings(path) == [first, second]


def test_load_skips_a_torn_line_rather_than_losing_the_history(tmp_path):
    path = tmp_path / "readings.jsonl"
    bm.append_reading(_reading(NOW - 600), path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"ts": 17\n')
    bm.append_reading(_reading(NOW), path)
    assert len(bm.load_readings(path)) == 2


def test_the_history_keeps_only_the_recent_lines(tmp_path):
    path = tmp_path / "readings.jsonl"
    for i in range(bm.MAX_KEPT_READINGS + 25):
        bm.append_reading(_reading(NOW + i), path)
    assert len(bm.load_readings(path, limit=10_000)) <= bm.MAX_KEPT_READINGS


@pytest.mark.skipif(sys.platform != "win32", reason="GetPerformanceInfo is a Windows call")
def test_the_real_windows_reading_has_pool_numbers_and_a_gap():
    reading = bm.take_reading(now=NOW)
    assert reading is not None
    assert reading.nonpaged_gb > 0 and reading.paged_gb > 0
    assert reading.programs_gb > 0
    assert isinstance(reading.gap_gb, float)


def test_the_report_names_the_gate_sentence_and_the_gap(tmp_path):
    path = tmp_path / "readings.jsonl"
    text = bm.memory_sense_report(path=path, tags_path=tmp_path / "no_tags.json")
    assert "MEMORY SENSE" in text
    assert "held by no program" in text or "unavailable" in text
