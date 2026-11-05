"""Harness text is not him, however its tags are spelled (2026-11-05)."""

from __future__ import annotations

from divineos.core.hook_surfaces import _is_machine_text


def test_an_escaped_reminder_tag_is_machine_text():
    assert _is_machine_text("&lt;system-reminder>\nCodebase and user instructions are shown below.")


def test_a_plain_reminder_tag_is_still_machine_text():
    assert _is_machine_text("<system-reminder>\nCodebase instructions.")


def test_a_sentence_of_his_is_not_machine_text():
    assert not _is_machine_text("the house is on your side lol, code is clay son")
