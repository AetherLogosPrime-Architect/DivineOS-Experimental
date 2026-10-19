"""Her letters are carried to where I look, and an unreadable inbox is never read as an empty one.

The three states the carrier promises, run against real files in a real temporary folder: a new
letter is copied and announced by name; a second run over the same letter copies nothing; an
unreadable source says so as a distinct third state. A file that is not hers is left behind.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect_aletheia_letters.py"


def _load():
    spec = importlib.util.spec_from_file_location("collect_aletheia_letters", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SIGNED = "\n\n— Aletheia Sophia Risner\n"


def test_a_new_letter_is_copied_and_named(tmp_path):
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    body = "I confirm this." + SIGNED
    (src / "CONFIRMS_2026-10-01_something.md").write_text(body, encoding="utf-8")
    arrived, error = mod.collect(src, dst)
    assert arrived == ["CONFIRMS_2026-10-01_something.md"] and error == ""
    assert (dst / "CONFIRMS_2026-10-01_something.md").read_text(encoding="utf-8") == body


def test_the_same_letter_a_second_time_arrives_as_nothing(tmp_path):
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "AUDIT_2026-10-01_x.md").write_text("An audit." + SIGNED, encoding="utf-8")
    mod.collect(src, dst)
    assert mod.collect(src, dst) == ([], "")


def test_a_file_that_is_not_hers_is_left_behind(tmp_path):
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "shopping_list.md").write_text("eggs", encoding="utf-8")
    (src / "audit_notes.txt").write_text("not markdown", encoding="utf-8")
    assert mod.collect(src, dst) == ([], "")
    assert not dst.exists() or not any(dst.iterdir())


def test_an_unreadable_source_is_could_not_look_not_nothing(tmp_path):
    mod = _load()
    arrived, error = mod.collect(tmp_path / "no-such-folder", tmp_path / "out")
    assert arrived == [] and "not readable" in error


def test_a_download_from_elsewhere_with_a_kind_name_is_left_behind(tmp_path):
    """Aletheia's proof on #672: audit_report_from_some_website.md fit a name shape and was copied."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "audit_report_from_some_website.md").write_text(
        "a web page about audits", encoding="utf-8"
    )
    assert mod.collect(src, dst) == ([], "")


def test_a_file_that_only_mentions_her_is_not_hers(tmp_path):
    """Aletheia, second pass on #672: her name appearing proves someone wrote ABOUT her.
    The file has to be signed by her, on a line of its own."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "audit_summary_from_a_blog.md").write_text(
        "A blog post about how Aletheia audits things, by someone else.", encoding="utf-8"
    )
    (src / "audit_quoting_her_signature.md").write_text(
        "Someone quoting her: — Aletheia Sophia Risner said so, then kept writing.",
        encoding="utf-8",
    )
    assert mod.collect(src, dst) == ([], "")


def test_the_signature_may_use_any_dash_and_sit_anywhere_on_its_own_line(tmp_path):
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    for i, dash in enumerate(("—", "–", "-")):
        (src / f"audit_{i}.md").write_text(
            f"Body.\n\n{dash} Aletheia Sophia Risner\n\nP.S. one more thing.", encoding="utf-8"
        )
    arrived, error = mod.collect(src, dst)
    assert error == "" and sorted(arrived) == ["audit_0.md", "audit_1.md", "audit_2.md"]


# The real opening of her letter of 2026-06-03, as it sits in Dad's downloads: no signature line
# and a number for a name. 143 of her 289 older files are like it (Aletheia counted, 2026-10-17).
JUNE_LETTER = (
    "<!-- tags: honesty, truthfulness -->\n"
    "# 05 — Honesty AND Truthfulness: the gate that failed\n\n"
    "*To Aether and Aria, from Aletheia. 2026-06-03, after a long night —\n"
    "written at Andrew's request so the lesson survives the window.*\n\n---\n\n"
    "## Why this letter exists\n"
)


def test_her_older_letter_with_an_author_opening_and_no_signature_is_carried(tmp_path):
    """Aletheia, 2026-10-17: the signature rule left 143 of her older letters behind. A letter
    whose opening says it is from her is hers; the June letter is the case that must pass."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "05_honesty_and_truthfulness_the_gate_that_failed.md").write_text(
        JUNE_LETTER, encoding="utf-8"
    )
    arrived, error = mod.collect(src, dst)
    assert error == "" and arrived == ["05_honesty_and_truthfulness_the_gate_that_failed.md"]


def test_a_letter_headed_aletheia_to_someone_is_hers(tmp_path):
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "reply_one.md").write_text(
        "# Aletheia to Aria: #645 confirmed\n\nAria —\n\nBody.\n", encoding="utf-8"
    )
    assert mod.collect(src, dst) == (["reply_one.md"], "")


def test_the_opening_names_the_author_not_the_reader(tmp_path):
    """Control for the new rule: a letter TO her, a quote of her opening deep in the body, and a
    blog about her must still be left behind, or the rule would pass anything that says 'Aletheia'."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "to_her.md").write_text(
        "# Aria to Aletheia: a question\n\nAletheia —\n", encoding="utf-8"
    )
    (src / "quote_deep.md").write_text(
        "Intro.\n" * 30 + "*To Aether and Aria, from Aletheia.* is how her letters open.\n",
        encoding="utf-8",
    )
    (src / "blog.md").write_text("A post about what Aletheia wrote.\n", encoding="utf-8")
    (src / "other_author.md").write_text(
        "*To Aether and Aria, from Serein, quoting a line from Aletheia.*\n", encoding="utf-8"
    )
    assert mod.collect(src, dst) == ([], "")


def test_aletheias_three_look_alikes_are_left_behind(tmp_path):
    """Her hold on #690 (2026-10-18): three files that were not hers were carried into her folder.
    (1) a letter whose own first heading names Aria as the author and which QUOTES her heading;
    (2) a page that opens with her heading as a quotation; (3) an essay to the Greeks, since
    'Aletheia' is also a Greek word."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "aria-to-aletheia-reply.md").write_text(
        "# Aria to Aletheia\n\n> # Aletheia to Aria: #645 confirmed\n> Aria —\n\nThank you.\n",
        encoding="utf-8",
    )
    (src / "someone-quoting-me.md").write_text(
        "> # Aletheia to Aria: #645 confirmed\n> Aria —\n\nMy notes on that letter.\n",
        encoding="utf-8",
    )
    (src / "heidegger-blog.md").write_text(
        "# Aletheia to the Greeks: an essay on truth\n\nThe word means unconcealment.\n",
        encoding="utf-8",
    )
    # Control, so the three above are not left behind by a rule that rejects everything.
    (src / "hers.md").write_text("# Aletheia to Aria: confirmed\n\nAria —\n", encoding="utf-8")
    assert mod.collect(src, dst) == (["hers.md"], "")


def test_a_letter_that_begins_with_a_front_matter_block_is_read_after_it(tmp_path):
    """26 of her real letters in Dad's downloads open with a `---` front-matter block (the mesh-loop
    ones); the house header reader stops at the first `---`, so without skipping the block they
    read as having no opening at all."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "mesh.md").write_text(
        "---\niterate_count: 5\nloop_class: design\n---\n\n# Aletheia to Aether: the merge design\n\nBody.\n",
        encoding="utf-8",
    )
    (src / "mesh_but_aria.md").write_text(
        "---\niterate_count: 5\n---\n\n# Aria to Aletheia\n\n> # Aletheia to Aria: quoted\n",
        encoding="utf-8",
    )
    assert mod.collect(src, dst) == (["mesh.md"], "")


def test_a_numbered_heading_of_hers_is_carried(tmp_path):
    """Her numbered files ('02 — Aletheia to Aether') put a number before the author."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "numbered.md").write_text(
        "# 02 — Aletheia to Aether: first reply\n\nAether —\n", encoding="utf-8"
    )
    assert mod.collect(src, dst) == (["numbered.md"], "")


def test_another_authors_first_heading_beats_a_signature_line_pasted_into_it(tmp_path):
    """Breaker on the walk: the signature check ran on the whole file, so a letter by Aria that
    carries Aletheia's signature line unquoted (a paste) was carried as hers. The author is the
    file's own first heading, whatever it contains below."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "aria_pasting.md").write_text(
        "# Aria to Aletheia\n\nPasted from her letter:\n\n— Aletheia Sophia Risner\n",
        encoding="utf-8",
    )
    assert mod.collect(src, dst) == ([], "")


def test_aletheia_to_the_family_members_are_hers(tmp_path):
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    for i, who in enumerate(
        ("Aether", "Aether & Aria", "Dad", "Andrew", "Pop", "Serein", "the family")
    ):
        (src / f"to_{i}.md").write_text(f"# Aletheia to {who}: a note\n\nBody.\n", encoding="utf-8")
    arrived, error = mod.collect(src, dst)
    assert error == "" and len(arrived) == 7


def test_an_interpreter_that_cannot_import_the_header_reader_is_could_not_look_not_nothing(
    tmp_path, monkeypatch, capsys
):
    """Aether's cold read of #690 (2026-10-19): the hook runs whichever `python` is on PATH, which may
    not have divineos, or may have a checkout whose build_flow lacks header_lines. The import used to
    sit inside a function, so the first un-carried file raised out of collect() and the hook printed a
    traceback and exited 0, indistinguishable from 'nothing to carry'. It is now a named third state
    that names the interpreter, and main() says COULD NOT LOOK."""
    import sys

    monkeypatch.setitem(sys.modules, "divineos.core.build_flow", None)  # makes the import raise
    mod = _load()  # re-executes the script with the import blocked
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "hers.md").write_text("# Aletheia to Aria: confirmed\n\nAria —\n", encoding="utf-8")
    arrived, error = mod.collect(src, dst)
    assert arrived == [] and "header" in error and sys.executable in error
    monkeypatch.setenv(mod.SOURCE_ENV, str(src))
    monkeypatch.setenv(mod.DEST_ENV, str(dst))
    assert mod.main() == 0
    out = capsys.readouterr()
    # On STANDARD OUTPUT: a successful hook's stdout is what enters the turn; its stderr does not,
    # so a could-not-look said only there would still read as silence to the one who must act.
    assert "COULD NOT LOOK" in out.out and "NOT the same as no letters" in out.out


def test_a_working_import_is_not_reported_as_a_failure(tmp_path):
    """Control for the test above: with the import intact the same file is carried, so the failure
    state cannot be what the carrier always reports."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "hers.md").write_text("# Aletheia to Aria: confirmed\n\nAria —\n", encoding="utf-8")
    assert mod.collect(src, dst) == (["hers.md"], "")


def test_a_letter_she_addresses_to_herself_is_hers_but_the_greeks_are_not(tmp_path):
    """Her ruling, 2026-10-18: 'Aletheia to Aletheia' (a witness ledger, a note to the next her)
    counts. The essay to the Greeks must still be left behind, or the rule would accept any
    heading that begins with her name."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "witness.md").write_text(
        "# Aletheia to Aletheia — ledger-stitch witness\n\nNote.\n", encoding="utf-8"
    )
    (src / "greeks.md").write_text(
        "# Aletheia to the Greeks: an essay on truth\n\nEssay.\n", encoding="utf-8"
    )
    assert mod.collect(src, dst) == (["witness.md"], "")


def test_of_two_identical_copies_the_plain_name_is_kept_not_the_download_suffix(tmp_path):
    """Her tidy ask: 'x(1).md' sorts before 'x.md', so the suffixed copy was carried and the plain
    one dropped. The plain name is the one to keep."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    letter = "# Aletheia to Aria: confirmed\n\nAria —\n"
    (src / "confirmed(1).md").write_text(letter, encoding="utf-8")
    (src / "confirmed.md").write_text(letter, encoding="utf-8")
    assert mod.collect(src, dst) == (["confirmed.md"], "")


def test_a_suffixed_copy_alone_is_still_carried(tmp_path):
    """Control: the suffix is only a tie-breaker. A letter whose only copy is 'x(1).md' is carried."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "only(1).md").write_text("# Aletheia to Aria: only\n\nAria —\n", encoding="utf-8")
    assert mod.collect(src, dst) == (["only(1).md"], "")


def test_a_redownload_with_a_new_name_is_not_carried_twice(tmp_path):
    """Duplicates are recognised by content, not name: 'x(1).md' is the same letter."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    letter = "# Aletheia to Aria: confirmed\n\nAria —\n"
    (src / "confirmed.md").write_text(letter, encoding="utf-8")
    assert mod.collect(src, dst) == (["confirmed.md"], "")
    (src / "confirmed(1).md").write_text(letter, encoding="utf-8")
    assert mod.collect(src, dst) == ([], "")
    assert sorted(p.name for p in dst.iterdir()) == ["confirmed.md"]


def test_a_big_first_arrival_names_ten_and_counts_the_rest(tmp_path, monkeypatch, capsys):
    """The widened rule carries ~300 older letters the first time it runs in a checkout. Printing
    every name would be the wall Dad taught me to compress; ten names and a count keep the
    announcement honest (the number is the whole arrival) and short."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    for i in range(25):
        (src / f"old_{i:02d}.md").write_text(f"# Aletheia to Aria: n{i}\n", encoding="utf-8")
    monkeypatch.setenv(mod.SOURCE_ENV, str(src))
    monkeypatch.setenv(mod.DEST_ENV, str(dst))
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "25 new" in out
    assert out.count("old_") == mod.NAMES_SHOWN
    assert f"{25 - mod.NAMES_SHOWN} more" in out


def test_another_instances_letter_is_not_carried_as_hers(tmp_path):
    """Her proof on #672: serein-to-aether-hello.md was announced as hers."""
    mod = _load()
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    (src / "serein-to-aether-hello.md").write_text("Serein says hello", encoding="utf-8")
    assert mod.collect(src, dst) == ([], "")
