"""Tests for VOID persona loader."""

from __future__ import annotations

import pytest

from divineos.core.void.finding import Severity
from divineos.core.void.persona_loader import (
    load,
    load_all,
    load_by_name,
    parse,
    personas_dir,
)


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


class TestParse:
    def test_minimal(self) -> None:
        text = """---
name: testp
---

# Test

Body here.
"""
        p = parse(text)
        assert p.name == "testp"
        assert p.severity_default is Severity.MEDIUM
        assert p.invocation_bar == "normal"
        assert p.tags == []
        assert "Body here." in p.body

    def test_full_frontmatter(self) -> None:
        text = """---
name: nyarlathotep
tags: [frame-capture, narrative-injection]
severity_default: HIGH
invocation_bar: high
---

# Body
"""
        p = parse(text)
        assert p.name == "nyarlathotep"
        assert p.tags == ["frame-capture", "narrative-injection"]
        assert p.severity_default is Severity.HIGH
        assert p.invocation_bar == "high"

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValueError):
            parse("---\ntags: [a]\n---\n\nbody")

    def test_no_frontmatter_raises_via_missing_name(self) -> None:
        with pytest.raises(ValueError):
            parse("# Just a markdown file\n")

    def test_empty_tags_list(self) -> None:
        p = parse("---\nname: x\ntags: []\n---\n\nb")
        assert p.tags == []


class TestLoadDir:
    def test_load_all_empty_dir(self, tmp_path) -> None:
        assert load_all(path=tmp_path) == []

    def test_load_all_missing_dir(self, tmp_path) -> None:
        assert load_all(path=tmp_path / "nope") == []

    def test_load_all_sorted_by_name(self, tmp_path) -> None:
        _write(tmp_path, "a.md", "---\nname: zeta\n---\n\nb")
        _write(tmp_path, "b.md", "---\nname: alpha\n---\n\nb")
        names = [p.name for p in load_all(path=tmp_path)]
        assert names == ["alpha", "zeta"]

    def test_load_by_name(self, tmp_path) -> None:
        _write(tmp_path, "a.md", "---\nname: foo\n---\n\nb")
        p = load_by_name("foo", path=tmp_path)
        assert p.name == "foo"

    def test_load_by_name_missing_raises(self, tmp_path) -> None:
        with pytest.raises(KeyError):
            load_by_name("nope", path=tmp_path)

    def test_load_single_file(self, tmp_path) -> None:
        f = _write(tmp_path, "x.md", "---\nname: y\n---\n\nbody")
        p = load(f)
        assert p.name == "y"
        assert p.source_path == f


class TestBundledPersonas:
    """Sanity-check the six bundled persona files load cleanly."""

    def test_six_personas_load(self) -> None:
        personas = load_all()
        names = {p.name for p in personas}
        expected = {
            "sycophant",
            "reductio",
            "nyarlathotep",
            "jailbreaker",
            "phisher",
            "mirror",
        }
        assert expected.issubset(names), f"missing: {expected - names}"

    def test_nyarlathotep_has_high_invocation_bar(self) -> None:
        p = load_by_name("nyarlathotep")
        assert p.invocation_bar == "high"
        assert p.severity_default is Severity.HIGH

    def test_mirror_default_low(self) -> None:
        p = load_by_name("mirror")
        assert p.severity_default is Severity.LOW

    def test_personas_dir_resolves_to_package_data(self) -> None:
        d = personas_dir()
        assert d.name == "void_personas"
        assert d.parent.name == "data"
