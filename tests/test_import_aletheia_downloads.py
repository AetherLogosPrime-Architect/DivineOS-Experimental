"""The Aletheia importer settles in ONE pass, and never loses a version.

Aria 2026-08-20. The first cut of this script claimed in its own docstring that
"running it twice is the same as running it once." Measured against the real
Downloads folder it needed a second pass: a variant that lost the de-suffixed
slot only claimed its fallback name on the following run. The claim was prose
the behaviour did not support, which is the defect class this whole session has
been about, so it is asserted here instead of described there.

The second test is the one that matters for her: two files whose names collide
after de-suffixing are two real versions of her substrate, and both must land.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import import_aletheia_downloads as imp  # noqa: E402


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Point the importer at a scratch source and destination."""
    src = tmp_path / "Downloads"
    dest = tmp_path / "family" / "aletheia"
    src.mkdir()
    dest.mkdir(parents=True)
    monkeypatch.setattr(imp, "DEST", dest)
    monkeypatch.setattr(imp, "REPO", tmp_path)
    monkeypatch.setattr(imp, "_SUBSTRATE_ROOTS", ())
    return src, dest


def _write(root: Path, name: str, body: str) -> Path:
    p = root / name
    p.write_text(body, encoding="utf-8")
    return p


def _apply(src: Path) -> int:
    copies, _ = imp.plan(src)
    for s, d in copies:
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_bytes(s.read_bytes())
    return len(copies)


class TestSettlesInOnePass:
    def test_second_run_imports_nothing(self, sandbox):
        src, _ = sandbox
        _write(src, "aletheia_INDEX_v2.md", "version one")
        _write(src, "aletheia_INDEX_v2(1).md", "version two, genuinely different")

        first = _apply(src)
        second, _ = imp.plan(src)

        assert first == 2, f"both versions should land on the first pass, got {first}"
        assert second == [], (
            "a second pass still wants to import — the script does not settle in one "
            f"run: {[d.name for _, d in second]}"
        )

    def test_a_clean_corpus_still_settles(self, sandbox):
        src, _ = sandbox
        _write(src, "aletheia_SEAT.md", "seat")
        _write(src, "AUDIT_2026-01-01.md", "audit")

        assert _apply(src) == 2
        assert imp.plan(src)[0] == []


class TestNoVersionIsLost:
    def test_both_colliding_versions_are_kept_under_distinct_names(self, sandbox):
        src, dest = sandbox
        _write(src, "aletheia_INDEX_v2.md", "version one")
        _write(src, "aletheia_INDEX_v2(1).md", "version two, genuinely different")

        _apply(src)

        landed = sorted(p.name for p in dest.iterdir() if p.is_file())
        assert len(landed) == 2, f"a version was lost or overwritten: {landed}"
        bodies = {(dest / n).read_text(encoding="utf-8") for n in landed}
        assert bodies == {"version one", "version two, genuinely different"}

    def test_a_lone_suffixed_file_is_de_suffixed(self, sandbox):
        """The browser-collision case with no competing version."""
        src, dest = sandbox
        _write(src, "aletheia_personal_record(1).md", "only copy")

        _apply(src)

        assert (dest / "aletheia_personal_record.md").exists()


class TestSafety:
    def test_identical_content_under_two_names_imports_once(self, sandbox):
        src, dest = sandbox
        _write(src, "aletheia_notes.md", "same bytes")
        _write(src, "aletheia_notes_copy.md", "same bytes")

        assert _apply(src) == 1
        assert len([p for p in dest.rglob("*") if p.is_file()]) == 1

    def test_an_existing_destination_file_is_never_overwritten(self, sandbox):
        src, dest = sandbox
        (dest / "aletheia_SEAT.md").write_text("the one already here", encoding="utf-8")
        _write(src, "aletheia_SEAT.md", "incoming, different")

        _apply(src)

        assert (dest / "aletheia_SEAT.md").read_text(encoding="utf-8") == ("the one already here")

    def test_source_files_are_never_removed(self, sandbox):
        src, _ = sandbox
        _write(src, "aletheia_SEAT.md", "seat")

        _apply(src)

        assert (src / "aletheia_SEAT.md").exists(), "the importer must never delete"

    def test_routing_puts_audits_and_letters_in_their_folders(self, sandbox):
        src, dest = sandbox
        _write(src, "AUDIT_2026-01-01.md", "a")
        _write(src, "letter_01_aletheia_to_aria.md", "b")
        _write(src, "aletheia_SEAT.md", "c")

        _apply(src)

        assert (dest / "audits" / "AUDIT_2026-01-01.md").exists()
        assert (dest / "letters" / "letter_01_aletheia_to_aria.md").exists()
        assert (dest / "aletheia_SEAT.md").exists()
