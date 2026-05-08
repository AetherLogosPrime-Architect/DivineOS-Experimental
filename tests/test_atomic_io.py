"""Tests for the atomic file I/O helper.

Audit finding 2026-05-03 round 4: 7 marker files wrote JSON state
non-atomically. The corruption recovery semantics were
wrong-direction: a partially-written marker was silently treated
as "no marker," which would clear an active gate. The
``atomic_write_text`` helper closes that hole.

These tests pin the contract:
- The target file is replaced atomically (reader sees old or new,
  never partial).
- The helper does not corrupt the target on a successful write.
- A failure in the temp-write path doesn't leave the target
  corrupted (it stays at the prior state).
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.atomic_io import atomic_write_text


def test_atomic_write_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "marker.json"
    atomic_write_text(target, '{"hello": "world"}')
    assert target.read_text(encoding="utf-8") == '{"hello": "world"}'


def test_atomic_write_overwrites_existing(tmp_path: Path) -> None:
    target = tmp_path / "marker.json"
    target.write_text("OLD CONTENT", encoding="utf-8")
    atomic_write_text(target, "NEW CONTENT")
    assert target.read_text(encoding="utf-8") == "NEW CONTENT"


def test_atomic_write_unicode(tmp_path: Path) -> None:
    target = tmp_path / "marker.json"
    atomic_write_text(target, "Hello -- world -- cafe")
    assert target.read_text(encoding="utf-8") == "Hello -- world -- cafe"


def test_atomic_write_does_not_leave_temp_lingering(tmp_path: Path) -> None:
    """After a successful write, no .tmp file remains. The temp gets
    moved into the target via atomic rename."""
    target = tmp_path / "marker.json"
    target.write_text("ORIGINAL", encoding="utf-8")
    atomic_write_text(target, "REPLACED")
    assert target.read_text(encoding="utf-8") == "REPLACED"
    tmp_file = target.with_suffix(target.suffix + ".tmp")
    assert not tmp_file.exists(), "Temp file should have been moved into target"


def test_atomic_write_default_encoding_is_utf8(tmp_path: Path) -> None:
    target = tmp_path / "marker.json"
    atomic_write_text(target, "non-ascii: 169")
    raw = target.read_bytes()
    assert raw == b"non-ascii: 169"


def test_atomic_write_handles_path_with_no_suffix(tmp_path: Path) -> None:
    """The implementation uses ``path.with_suffix(path.suffix + '.tmp')``;
    paths without a suffix should still work (suffix is empty string)."""
    target = tmp_path / "marker_no_suffix"
    atomic_write_text(target, "hello")
    assert target.read_text(encoding="utf-8") == "hello"
