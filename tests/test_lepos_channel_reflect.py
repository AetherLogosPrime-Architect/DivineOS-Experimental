"""Tests for post-send lepos reflection channel."""

from __future__ import annotations

from divineos.core.lepos_channel_reflect import (
    Reflection,
    pending_surface_path,
    read_and_consume_pending,
    reflect,
    render_pending_or_empty,
    write_pending,
)


def test_reflect_detects_exact_span_citation() -> None:
    andrew = "the gate/channel needs to be triggered after your initial post"
    reply = "so the channel needs to be triggered after your initial post — got it"
    r = reflect(reply, andrew)
    assert r.heard is True
    assert r.heard_span is not None
    assert "triggered" in r.heard_span


def test_reflect_no_citation_when_paraphrasing() -> None:
    andrew = "we usually do block first because it locates the violation"
    reply = "yeah okay makes sense to me sure whatever you say"
    r = reflect(reply, andrew)
    assert r.heard is False
    assert r.heard_span is None


def test_reflect_detects_interior_marker() -> None:
    andrew = "want me to build the block first?"
    reply = "I think block-first is right — I have a concern about the ordering though"
    r = reflect(reply, andrew)
    assert r.interior is True
    assert r.interior_marker is not None


def test_reflect_flags_length_dump() -> None:
    andrew = "yes"
    reply = "x" * 5000
    r = reflect(reply, andrew)
    assert r.dumped is True
    assert r.length_ratio >= 8.0


def test_reflect_does_not_flag_short_replies_as_dumped() -> None:
    andrew = "hi"
    reply = "hey back"
    r = reflect(reply, andrew)
    assert r.dumped is False


def test_degenerate_when_all_three_fail() -> None:
    andrew = "wat"
    reply = "totally " * 100  # long, no citation, no interior marker
    r = reflect(reply, andrew)
    assert r.degenerate() is True


def test_not_degenerate_when_any_lens_present() -> None:
    andrew = "wat"
    reply = "I think " + "totally " * 100
    r = reflect(reply, andrew)
    assert r.degenerate() is False


def test_write_and_consume_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    r = reflect("I think the channel is right", "the channel should be right", now=1000.0)
    write_pending(r)
    assert pending_surface_path().exists()
    got = read_and_consume_pending()
    assert got is not None
    assert got.ts == 1000.0
    assert got.interior is True
    assert not pending_surface_path().exists()


def test_read_pending_returns_none_when_absent(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    assert read_and_consume_pending() is None


def test_render_pending_returns_empty_when_absent(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    assert render_pending_or_empty() == ""


def test_render_pending_includes_channel_empty_when_degenerate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    r = Reflection(
        ts=1.0,
        heard=False,
        heard_span=None,
        interior=False,
        interior_marker=None,
        dumped=True,
        length_ratio=20.0,
        reply_len=2000,
        andrew_len=100,
    )
    write_pending(r)
    out = render_pending_or_empty()
    assert "LEPOS REFLECTION" in out
    assert "channel-empty" in out


def test_read_and_consume_is_one_shot(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    r = reflect("I feel steady", "just checking in", now=42.0)
    write_pending(r)
    assert read_and_consume_pending() is not None
    assert read_and_consume_pending() is None
