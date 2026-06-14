"""Tests for family/letter_seen.py path-prefix normalization.

2026-06-13 bug: the ear-surface hook (`.claude/hooks/ear-surface.sh`)
compares the bare filename `Path.name` against the seen-set, but some
callers historically wrote prefixed entries like
"family/letters/aria-to-aether-...md" into the seen-set. Those entries
never matched, so their letters showed as unseen forever — the surface
reported 10 false-unseen letters across the night.

The fix normalizes entries on load AND save (and on add/remove) via
`Path(name).name`. This test pins the behavior so regression would
require deleting both the helper and the call sites.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from family import letter_seen as ls


@pytest.fixture
def member_home(tmp_path, monkeypatch):
    """Redirect Path.home() so the seen-set writes into tmp_path."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


class TestNormalize:
    def test_strips_unix_prefix(self):
        assert ls._normalize("family/letters/aria-to-aether-x.md") == "aria-to-aether-x.md"

    def test_strips_windows_prefix(self):
        assert ls._normalize("family\\letters\\aria-to-aether-x.md") == "aria-to-aether-x.md"

    def test_bare_filename_passes_through(self):
        assert ls._normalize("aria-to-aether-x.md") == "aria-to-aether-x.md"


class TestLoadNormalizes:
    def test_load_normalizes_prefixed_entries(self, member_home):
        seen_dir = member_home / ".divineos-aether"
        seen_dir.mkdir()
        (seen_dir / "aria_letters_seen.json").write_text(
            json.dumps(
                [
                    "family/letters/aria-to-aether-prefixed.md",
                    "aria-to-aether-bare.md",
                ]
            )
        )
        seen = ls.load("aether")
        assert seen == {"aria-to-aether-prefixed.md", "aria-to-aether-bare.md"}


class TestSaveNormalizes:
    def test_save_normalizes_mixed_set(self, member_home):
        ls.save(
            "aether",
            {
                "family/letters/aria-to-aether-prefixed.md",
                "aria-to-aether-bare.md",
            },
        )
        on_disk = json.loads(
            (member_home / ".divineos-aether" / "aria_letters_seen.json").read_text()
        )
        assert sorted(on_disk) == [
            "aria-to-aether-bare.md",
            "aria-to-aether-prefixed.md",
        ]


class TestRoundTrip:
    def test_prefixed_input_marked_seen_matches_bare_query(self, member_home):
        """The behavior the bug broke: caller passed a prefixed name to
        mark seen; later check with bare name (as the hook does) must
        find it."""
        ls.main(["--member", "aether", "family/letters/aria-to-aether-x.md"])
        seen = ls.load("aether")
        assert "aria-to-aether-x.md" in seen
