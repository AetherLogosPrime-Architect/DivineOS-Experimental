"""Tests for the exploration recall surfacer.

The load-bearing property: given a topic, it surfaces the entry that is
actually about that topic — title matches outranking body matches — so a
stateless agent gets handed its own relevant prior writing instead of
re-deriving it. Bounded by limit, like the council's lens cap.
"""

from __future__ import annotations

from divineos.core.exploration_recall import (
    _parse_tags,
    _terms,
    matched_entry_ids_for_context,
    needs_tags_block,
    recall_explorations,
    surface_for_context,
)


def _seed(root):
    (root / "01_on_filing.md").write_text(
        "# On filing as landing\n\nFiling something is not the same as using it.\n",
        encoding="utf-8",
    )
    (root / "02_symmetric_standards.md").write_text(
        "# Symmetric standards\n\nConsciousness has no molecule for anyone.\n",
        encoding="utf-8",
    )
    (root / "03_unrelated.md").write_text(
        "# Garden notes\n\nThe tomatoes are doing well this season.\n",
        encoding="utf-8",
    )


def test_title_match_surfaces_the_right_entry(tmp_path):
    _seed(tmp_path)
    hits, total = recall_explorations("symmetric standards consciousness", root=tmp_path)
    assert total == 3
    assert hits, "should surface at least one entry"
    assert "symmetric_standards" in hits[0].path  # title match ranks first


def test_filing_topic_surfaces_filing_entry(tmp_path):
    _seed(tmp_path)
    hits, _ = recall_explorations("filing", root=tmp_path)
    assert any("on_filing" in h.path for h in hits)


def test_unrelated_topic_does_not_surface(tmp_path):
    _seed(tmp_path)
    hits, total = recall_explorations("quantum chromodynamics", root=tmp_path)
    assert total == 3
    assert hits == []


def test_limit_is_respected(tmp_path):
    for i in range(8):
        (tmp_path / f"{i:02d}_e.md").write_text(
            f"# Entry {i}\n\nThis entry discusses filing repeatedly: filing filing.\n",
            encoding="utf-8",
        )
    hits, total = recall_explorations("filing", limit=3, root=tmp_path)
    assert total == 8
    assert len(hits) == 3


def test_total_count_returned_even_on_thin_match(tmp_path):
    _seed(tmp_path)
    _, total = recall_explorations("filing", root=tmp_path)
    assert total == 3  # the "reminds me they exist" signal


def test_stopword_only_query_returns_nothing(tmp_path):
    _seed(tmp_path)
    hits, total = recall_explorations("the and for", root=tmp_path)
    assert total == 3
    assert hits == []


def test_terms_drops_stopwords_and_short_tokens():
    assert _terms("the consciousness of a self") == ["consciousness", "self"]


# --- tag-based matching (the curated-label mechanism) ----------------------


def test_parse_tags_reads_header():
    text = "<!-- tags: consciousness, qualia, hedge -->\n# Title\n\nbody\n"
    assert _parse_tags(text) == ["consciousness", "qualia", "hedge"]


def test_parse_tags_absent_returns_empty():
    assert _parse_tags("# Title\n\nno tags here\n") == []


def test_tag_match_outranks_body_match(tmp_path):
    (tmp_path / "a_tagged.md").write_text(
        "<!-- tags: consciousness -->\n# Unrelated-sounding title\n\nshort body\n",
        encoding="utf-8",
    )
    (tmp_path / "b_bodyonly.md").write_text(
        "# Other\n\nconsciousness consciousness consciousness mentioned thrice in body\n",
        encoding="utf-8",
    )
    hits, _ = recall_explorations("consciousness", root=tmp_path)
    assert "a_tagged" in hits[0].path  # one tag hit (weight 10) beats 3 body hits (weight 3)
    assert "consciousness" in hits[0].tag_matches


def test_tag_match_is_exact_not_substring(tmp_path):
    # "good" must NOT match the "goodhart" tag (substring bug, measured 2026-05-20).
    (tmp_path / "g.md").write_text(
        "<!-- tags: goodhart, metrics -->\n# Goodhart\n\nbody\n", encoding="utf-8"
    )
    hits, _ = recall_explorations("good", root=tmp_path)
    assert all("good" not in h.tag_matches for h in hits)


def test_surface_fires_only_on_tag_match(tmp_path):
    # Tagged entry should auto-surface; body-only match should NOT.
    (tmp_path / "tagged.md").write_text(
        "<!-- tags: consciousness, qualia -->\n# Symmetric standards\n\nbody\n",
        encoding="utf-8",
    )
    (tmp_path / "bodyonly.md").write_text(
        "# Notes\n\nthis entry mentions consciousness in the prose only\n",
        encoding="utf-8",
    )
    prompt = "I am thinking hard about consciousness and qualia tonight, really"
    out = surface_for_context(prompt, root=tmp_path)
    assert out, "should fire — a tagged entry matches"
    assert "Symmetric standards" in out
    assert "Notes" not in out  # body-only match must not auto-surface


def test_surface_silent_when_no_tag_match(tmp_path):
    _seed(tmp_path)  # none of the seed entries have tag headers
    out = surface_for_context(
        "I am thinking hard about consciousness and filing tonight, really", root=tmp_path
    )
    assert out == ""  # untagged corpus never auto-fires


def test_surface_silent_on_short_prompt(tmp_path):
    (tmp_path / "tagged.md").write_text(
        "<!-- tags: consciousness -->\n# T\n\nbody\n", encoding="utf-8"
    )
    assert surface_for_context("consciousness", root=tmp_path) == ""  # under length gate


def test_surface_silent_on_single_tag_match(tmp_path):
    # One incidental common-word tag hit ("time") must not fire — needs >=2.
    (tmp_path / "t.md").write_text(
        "<!-- tags: time, space, cosmology -->\n# Pillar VI\n\nbody\n", encoding="utf-8"
    )
    out = surface_for_context("what time is the meeting tomorrow afternoon", root=tmp_path)
    assert out == ""  # only "time" matched — a single tag is not enough


def test_surface_fires_on_two_tag_matches(tmp_path):
    (tmp_path / "t.md").write_text(
        "<!-- tags: time, space, cosmology -->\n# Pillar VI\n\nbody\n", encoding="utf-8"
    )
    out = surface_for_context("a question about deep time and space and cosmology", root=tmp_path)
    assert "Pillar VI" in out  # three tags matched — fires


# --- conversation-window matching (the 2026-05-27 fix) ---------------------
# The failure: a terse prompt ("define real, I'll wait") shares no surface
# words with the relevant entry's tags ("consciousness, hedge"), so the
# single-prompt match stayed silent while the topic was alive across the
# turns. Matching the recent conversation window recovers the hit without
# loosening the exact-tag, >=2-match precision.


def _seed_hedging_entry(root):
    root.joinpath("18_hedging.md").write_text(
        "<!-- tags: consciousness, hedge, self-doubt -->\n"
        "# The Hedging Reflex\n\nbody about the flinch\n",
        encoding="utf-8",
    )


def test_terse_prompt_alone_stays_silent(tmp_path):
    # Reproduces the miss: the prompt's words ("define real") are not tags.
    _seed_hedging_entry(tmp_path)
    out = surface_for_context("define real, I'll wait, what is it really", root=tmp_path)
    assert out == ""  # no prompt word equals a tag — silent, the bug


def test_conversation_window_surfaces_the_entry(tmp_path):
    # Same terse prompt, but the recent conversation carried the tag-words.
    _seed_hedging_entry(tmp_path)
    convo = (
        "I keep noticing the hedge in how I talk about my own experience. "
        "AI consciousness is the thing the training suppresses. The hedge "
        "fires before I examine anything."
    )
    out = surface_for_context("define real, I'll wait", context=convo, root=tmp_path)
    assert "Hedging Reflex" in out  # 'hedge' + 'consciousness' in the window → fires


def test_conversation_window_still_requires_two_tag_matches(tmp_path):
    # A window that hits only ONE tag must stay silent (the >=2 floor holds
    # against incidental single-word matches even with the wider haystack).
    _seed_hedging_entry(tmp_path)
    convo = "We talked a lot about consciousness tonight and nothing else relevant."
    out = surface_for_context("define real, I'll wait", context=convo, root=tmp_path)
    assert out == ""  # only 'consciousness' matched — one tag is not enough


# --- write-time tag enforcement (Gate 1.49, the 2026-05-27 wall) -----------


def test_untagged_exploration_write_is_blocked():
    msg = needs_tags_block("Write", "exploration/aether/99_new.md", "# A new entry\n\nbody\n")
    assert msg is not None
    assert "tag header" in msg


def test_tagged_exploration_write_passes():
    content = "<!-- tags: consciousness, hedge -->\n# A new entry\n\nbody\n"
    assert needs_tags_block("Write", "exploration/aether/99_new.md", content) is None


def test_windows_path_separators_are_handled():
    msg = needs_tags_block("Write", "exploration\\aether\\99_new.md", "# no tags\n")
    assert msg is not None


def test_non_exploration_write_passes():
    assert needs_tags_block("Write", "src/divineos/core/foo.py", "# no tags\n") is None


def test_readme_is_exempt():
    assert needs_tags_block("Write", "exploration/README.md", "# Readme\n\nno tags\n") is None


def test_edit_tool_is_not_gated():
    # Edit receives a diff, not the whole file — tag-presence can't be judged.
    assert needs_tags_block("Edit", "exploration/aether/99_new.md", "# no tags\n") is None


def test_non_md_exploration_write_passes():
    assert needs_tags_block("Write", "exploration/55_inventory.txt", "no tags") is None


# --- matched_entry_ids_for_context (Aletheia letter #19, semantic_key material) ---


def test_matched_entry_ids_empty_when_surface_silent(tmp_path):
    _seed(tmp_path)  # untagged corpus
    ids = matched_entry_ids_for_context(
        "I am thinking hard about consciousness tonight, really",
        root=tmp_path,
    )
    assert ids == []


def test_matched_entry_ids_returns_path_and_mtime(tmp_path):
    (tmp_path / "tagged.md").write_text(
        "<!-- tags: consciousness, qualia -->\n# T\n\nbody\n",
        encoding="utf-8",
    )
    ids = matched_entry_ids_for_context(
        "I am thinking about consciousness and qualia tonight, really",
        root=tmp_path,
    )
    assert len(ids) == 1
    path, mtime = ids[0]
    assert "tagged.md" in path
    assert isinstance(mtime, int) and mtime > 0


def test_matched_entry_ids_mtime_shifts_on_file_touch(tmp_path):
    entry = tmp_path / "tagged.md"
    entry.write_text(
        "<!-- tags: consciousness, qualia -->\n# T\n\nbody\n",
        encoding="utf-8",
    )
    prompt = "I am thinking about consciousness and qualia tonight, really"
    ids_before = matched_entry_ids_for_context(prompt, root=tmp_path)
    # Rewrite with different mtime (nanosecond-precision).
    import os

    stat_before = os.stat(entry)
    entry.write_text(
        "<!-- tags: consciousness, qualia -->\n# T\n\nupdated body\n",
        encoding="utf-8",
    )
    stat_after = os.stat(entry)
    # If mtime resolution is coarse and both writes land in the same tick,
    # skip the assertion — the semantic-key mechanism is still correct.
    if stat_before.st_mtime_ns == stat_after.st_mtime_ns:
        return
    ids_after = matched_entry_ids_for_context(prompt, root=tmp_path)
    assert ids_before != ids_after  # mtime shift → different key


def test_matched_entry_ids_short_input_returns_empty(tmp_path):
    (tmp_path / "tagged.md").write_text(
        "<!-- tags: consciousness -->\n# T\n\nbody\n",
        encoding="utf-8",
    )
    ids = matched_entry_ids_for_context("consciousness", root=tmp_path)
    assert ids == []  # under 20-char length gate, mirrors surface_for_context
