"""The prose about the 946 forks in docs/known_chain_breaks.md must excuse nothing.

2026-11-27: the 946 forks in Aether's ledger were written down with their cause
(his own probes of 2026-08-20, no gap, no edited row). That section is prose on
purpose. The verifier excuses a link only for a line of the shape
"- `<event id>` <evidence>", so a careless bullet added to that section would
quietly turn a written-down finding into silent exemptions. This pins that the
file still exempts exactly the one break it exempted before, and that the parser
would notice a bullet if one were added (the control). The older test in
test_ledger_wipe_and_write_path_defences.py pins that the file is found and read.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core import ledger

DOC = Path(__file__).resolve().parents[1] / "docs" / "known_chain_breaks.md"
JUNE = "22d95584-4a61-4931-9767-5acd036742ed"
FIRST_FORK = "9a47e603-b8fd-4b10-b257-ff67b6ec4b50"


def test_the_file_exempts_only_the_june_break() -> None:
    assert ledger.KNOWN_CHAIN_BREAKS_FILE.resolve() == DOC.resolve()
    assert ledger._known_chain_breaks() == {JUNE}


def test_the_section_is_there_and_names_its_evidence() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "Written down, not exempted" in text
    assert "none is a gap" in text
    assert "be001ee800d6e5417844e6e1c418c596eaae46eab8443379666635481376ac36" in text
    assert "backfill_chain_hashes" in text  # the warning not to re-link


def test_control_a_bullet_with_an_id_and_evidence_would_exempt(monkeypatch, tmp_path) -> None:
    """Without this, the first test could pass because the parser sees nothing at all."""
    doc = tmp_path / "known_chain_breaks.md"
    doc.write_text(
        DOC.read_text(encoding="utf-8")
        + f"\n- `{FIRST_FORK}` — an example entry with enough evidence beside it\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ledger, "KNOWN_CHAIN_BREAKS_FILE", doc)
    assert ledger._known_chain_breaks() == {JUNE, FIRST_FORK}
