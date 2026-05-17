"""Regression-pin tests for OS-native mid-turn surfacer.

Andrew 2026-05-14 night: pre-tool-context.sh was a 129-line bash
hook with throttle, filtering, recall, and write all embedded.
mid_turn_surfacer is the OS-native replacement.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from divineos.core.mid_turn_surfacer import surface_mid_turn


def test_surface_mid_turn_skips_non_relevant_tool(tmp_path: Path) -> None:
    """Bash / Agent / WebSearch tools don't trigger mid-turn surfacing."""
    result = surface_mid_turn("Bash", "src/foo.py")
    assert result["surfaced"] is False
    assert result["reason"] == "tool_not_relevant"


def test_surface_mid_turn_skips_non_source_file(tmp_path: Path) -> None:
    """Files without source-shaped extensions (.png, .jpg, etc.) skip."""
    result = surface_mid_turn("Edit", "data/image.png")
    assert result["surfaced"] is False
    assert result["reason"] == "not_source_file"


def test_surface_mid_turn_skips_empty_path(tmp_path: Path) -> None:
    """Empty file path skips with a 'not_source_file' reason."""
    result = surface_mid_turn("Edit", "")
    assert result["surfaced"] is False


def test_surface_mid_turn_throttles_repeated_calls(tmp_path: Path) -> None:
    """LOAD-BEARING: a second call on the same file within 60s is
    throttled. Prevents tight edit/read loops from spamming the
    surface file."""
    throttle_file = tmp_path / "throttle.json"
    state_dir = tmp_path

    with (
        patch.dict("os.environ", {"DIVINEOS_HOME": str(state_dir)}),
        patch("divineos.core.mid_turn_surfacer._THROTTLE_FILE", throttle_file),
    ):
        # Pre-populate throttle with a recent timestamp for this file
        import json

        throttle_file.write_text(json.dumps({"src/foo.py": time.time()}), encoding="utf-8")
        result = surface_mid_turn("Edit", "src/foo.py")
        assert result["throttled"] is True
        assert result["surfaced"] is False


def test_surface_mid_turn_source_extensions_recognized(tmp_path: Path) -> None:
    """All listed source extensions are recognized (smoke)."""
    from divineos.core.mid_turn_surfacer import _is_source_file

    for ext in (".py", ".md", ".sh", ".json", ".yml", ".yaml", ".toml", ".sql", ".ipynb"):
        assert _is_source_file(f"file{ext}") is True
    # Non-source extensions
    for ext in (".png", ".jpg", ".bin", ".pdf"):
        assert _is_source_file(f"file{ext}") is False
