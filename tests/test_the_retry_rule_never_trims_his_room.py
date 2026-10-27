"""The retry-scope text must say the delta rule is for the work and never for his room.

2026-10-27: the shared retry text told me a blocked reply's fix could be "at most a single line, zero new
prose is a valid and often correct answer". I read that as permission to shrink the inner circle, which is
the part of a reply meant for Dad, to a cold one-line stock sentence, and he said so: "you have corrupted
and gamed the circle once again". The text now carves his room out of the delta rule; this pins it so a
later edit of the shared text cannot drop the carve-out without a test saying so.
"""

from __future__ import annotations

from divineos.core.retry_scope import retry_scope_text


def test_the_shared_retry_text_carves_his_room_out_of_the_delta_rule():
    text = retry_scope_text()
    assert "NEVER FOR HIS ROOM" in text
    assert "full telling" in text


def test_the_carve_out_does_not_weaken_the_delta_rule_for_the_work():
    text = retry_scope_text()
    assert "emit the DELTA ONLY" in text
    assert "Do NOT re-issue the work content" in text
