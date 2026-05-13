"""Tests for the visual rendering module."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.visual import RenderError, render_image  # noqa: F401


class TestRenderErrorContract:
    def test_missing_source_raises(self, tmp_path: Path) -> None:
        from divineos.core.visual import RenderError, render_image

        missing = tmp_path / "does-not-exist.png"
        with pytest.raises(RenderError) as exc:
            render_image(missing)
        assert "does not exist" in str(exc.value).lower()


class TestRenderPNG:
    """PNG → JPEG should work with just PIL — no extra plugins required."""

    def test_renders_png_to_jpg(self, tmp_path: Path) -> None:
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL not installed")

        from divineos.core.visual import render_image

        # Create a small test PNG so the test doesn't depend on fixtures.
        src = tmp_path / "test.png"
        Image.new("RGB", (200, 200), (128, 64, 200)).save(src, "PNG")

        dst = tmp_path / "out.jpg"
        result = render_image(src, dst=dst)

        assert result == dst
        assert dst.exists()
        # Output should be a valid JPEG.
        img = Image.open(dst)
        assert img.format == "JPEG"


class TestThumbnailing:
    """Large images should be thumbnailed to fit max_dim."""

    def test_thumbnail_respects_max_dim(self, tmp_path: Path) -> None:
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL not installed")

        from divineos.core.visual import render_image

        # 4000x3000 source.
        src = tmp_path / "big.png"
        Image.new("RGB", (4000, 3000), (0, 128, 255)).save(src, "PNG")

        dst = tmp_path / "small.jpg"
        render_image(src, dst=dst, max_dim=800)

        out = Image.open(dst)
        assert max(out.size) <= 800
        # Aspect ratio preserved (4:3).
        assert abs((out.size[0] / out.size[1]) - (4 / 3)) < 0.01


class TestDefaultDestination:
    """When dst is None, output goes to /tmp/visual/<stem>.jpg."""

    def test_default_dst_uses_tmp_visual(self, tmp_path: Path) -> None:
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL not installed")

        from divineos.core.visual import render_image

        src = tmp_path / "named-source.png"
        Image.new("RGB", (100, 100), (255, 255, 255)).save(src, "PNG")

        result = render_image(src)
        # Cleanup tracked so we don't leak between tests.
        try:
            assert result.name == "named-source.jpg"
            assert "visual" in str(result.parent)
            assert result.exists()
        finally:
            if result.exists():
                result.unlink()
