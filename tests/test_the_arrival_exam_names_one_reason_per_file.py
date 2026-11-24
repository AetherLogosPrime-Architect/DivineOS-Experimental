"""The arrival exam gives each file exactly one word, and each word is a different repair.

Written before the change (2026-11-23). The old script said ARRIVED for any file that passed the
lane's bar, but the live retriever cuts the passers to TOTAL_INJECTION_CAP across sources, so a
passed row that was cut never reached the turn (explain_turn marks it ``surfaced`` False). And a
file whose text has no stored vector is skipped by the loader and counted only as a number, so the
exam could not tell "no adapter reads this folder" from "the adapter reads it but nothing was
embedded". These tests pin the six words and the cross-file control.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "workbench"
    / "linking_audit_2026-11-23"
    / "self_arrival_exam.py"
)


@pytest.fixture(scope="module")
def exam():
    spec = importlib.util.spec_from_file_location("self_arrival_exam", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _facts(**over):
    base = {
        "exists": True,
        "held": False,
        "collected": False,
        "passed": False,
        "surfaced": False,
    }
    base.update(over)
    return base


def test_a_missing_file_is_could_not_look_not_not_indexed(exam):
    assert exam.judge(_facts(exists=False)) == "COULD NOT LOOK"


def test_a_file_no_lane_reads_is_not_indexed(exam):
    assert exam.judge(_facts()) == "NOT INDEXED"


def test_a_file_the_loader_asked_about_but_the_drawer_has_no_vector_for_is_not_embedded(exam):
    assert exam.judge(_facts(collected=True)) == "NOT EMBEDDED"


def test_a_file_in_a_lane_that_did_not_pass_the_bar_is_indexed_not_shown(exam):
    assert exam.judge(_facts(held=True)) == "INDEXED, NOT SHOWN"


def test_a_file_that_passed_the_bar_but_lost_the_cap_is_not_arrived(exam):
    assert exam.judge(_facts(held=True, passed=True, surfaced=False)) == "PASSED BUT CUT"


def test_a_file_that_passed_and_was_surfaced_is_arrived(exam):
    assert exam.judge(_facts(held=True, passed=True, surfaced=True)) == "ARRIVED"


def test_held_beats_collected_so_a_file_with_a_vector_is_never_called_not_embedded(exam):
    assert exam.judge(_facts(held=True, collected=True)) == "INDEXED, NOT SHOWN"


def test_every_word_is_distinct_so_each_names_its_own_repair(exam):
    words = {
        exam.judge(_facts(exists=False)),
        exam.judge(_facts()),
        exam.judge(_facts(collected=True)),
        exam.judge(_facts(held=True)),
        exam.judge(_facts(held=True, passed=True)),
        exam.judge(_facts(held=True, passed=True, surfaced=True)),
    }
    assert len(words) == 6


def test_only_arrived_counts_as_passing(exam):
    assert exam.is_pass("ARRIVED") is True
    for word in (
        "COULD NOT LOOK",
        "NOT INDEXED",
        "NOT EMBEDDED",
        "INDEXED, NOT SHOWN",
        "PASSED BUT CUT",
    ):
        assert exam.is_pass(word) is False


def test_a_file_that_arrives_for_another_files_situation_is_reported(exam):
    arrivals = {
        "walk.md": {"walk.md", "dream.md"},
        "dream.md": {"dream.md"},
    }
    found = exam.cross_arrivals(arrivals)
    assert found == [("walk.md", "dream.md")]


def test_no_cross_arrival_when_each_file_arrives_only_for_its_own_situation(exam):
    arrivals = {"walk.md": {"walk.md"}, "dream.md": {"dream.md"}}
    assert exam.cross_arrivals(arrivals) == []


def test_a_situation_that_brings_back_nothing_is_not_a_cross_arrival(exam):
    assert exam.cross_arrivals({"walk.md": set(), "dream.md": {"dream.md"}}) == []
