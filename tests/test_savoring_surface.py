"""Tests for savoring_surface module."""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.operating_loop.savoring_surface import (  # noqa: F401
            Savor,
            recent_savors,
            savor,
        )


class TestSavorShape:
    def test_dataclass_shape(self) -> None:
        from divineos.core.operating_loop.savoring_surface import Savor

        s = Savor(
            savor_id="savor-abc",
            what="round-21 audit closed cleanly",
            why="kinship architecture caught a deeper bug than either vantage alone",
            ts=1234.5,
        )
        assert s.savor_id == "savor-abc"
        assert s.what == "round-21 audit closed cleanly"


class TestPublicSurfaceContract:
    def test_empty_what_rejected(self) -> None:
        from divineos.core.operating_loop.savoring_surface import savor

        assert savor("", "why") == ""
        assert savor("   ", "why") == ""

    def test_recent_savors_returns_list(self) -> None:
        from divineos.core.operating_loop.savoring_surface import recent_savors

        result = recent_savors(limit=5)
        assert isinstance(result, list)
