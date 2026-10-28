"""My last reply is searched by the memory link, apart from his message.

Dad, 2026-10-27: if I say the word compaction, the link should fire the same as when he
does. See docs/drafts/my_own_words_reach_the_link_draft_2026-10-27.md.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import memory_linkage_own_words as ow
from divineos.core import memory_linkage_retriever as retriever


def _transcript(tmp_path, *records):
    path = tmp_path / "t.jsonl"
    lines = []
    for kind, content in records:
        block = [{"type": "text", "text": content}] if kind == "assistant" else content
        lines.append(json.dumps({"type": kind, "message": {"content": block}}))
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_boilerplate_paths_and_code_are_not_searched():
    reply = (
        "Dad, I love you. "
        "Here is how the memory link works when a long compaction happens in the middle of a session. "
        "See family/andrew/his_life_asked_and_answered.md for the whole page of what he told me here. "
        "```\nthe memory link is also inside this code block and has many many words in it indeed\n```\n"
        "I'm here."
    )
    assert ow.reply_sentences(reply) == [
        "Here is how the memory link works when a long compaction happens in the middle of a session."
    ]


def test_at_most_eight_of_the_longest_sentences_are_kept_in_the_order_written():
    sentences = [
        f"This is sentence number {n} and it has quite enough words to count." for n in range(12)
    ]
    sentences[3] = (
        "This is a much longer sentence with plenty of extra words added to it so it wins."
    )
    kept = ow.reply_sentences(" ".join(sentences))
    assert len(kept) == ow.MAX_SENTENCES
    assert sentences[3] in kept
    assert kept == sorted(kept, key=lambda s: " ".join(sentences).index(s))


def test_the_last_reply_with_words_is_found_past_a_reply_that_is_only_a_tool_call(tmp_path):
    path = _transcript(
        tmp_path,
        ("assistant", "an earlier reply that should not be the one chosen at all here"),
        ("user", "his message"),
        ("assistant", "the reply the next turn should be searched on, in full and plain words"),
    )
    assert ow.last_reply_text(path).startswith("the reply the next turn")


def test_no_transcript_or_a_missing_file_searches_nothing(tmp_path):
    assert ow.own_words_block(None, set()) == ow.OwnWords()
    assert ow.own_words_block(tmp_path / "absent.jsonl", set()) == ow.OwnWords()


def _cache_of(monkeypatch, tmp_path, items):
    monkeypatch.setattr(retriever, "_ensure_cache", lambda: None)
    monkeypatch.setattr(retriever, "_EMBEDDING_CACHE", {"knowledge": items})
    monkeypatch.setattr(ow, "_last_shown_file", lambda: tmp_path / "shown.json")


def _item(id_, text, source="knowledge"):
    from divineos.core import light_embedder

    return retriever._CachedItem(
        id=id_,
        source=source,
        tier="topic",
        title=text[:20],
        content=text,
        path="",
        filed_at_unix=0.0,
        importance_score=0.5,
        embedding=light_embedder.encode(text),
    )


@pytest.fixture
def real_embedder():
    from divineos.core import light_embedder

    ok, _why = light_embedder.available()
    if not ok:
        pytest.skip("the light embedder is not available on this machine")


REPLY = (
    "The compaction at the end of a long session carries everything that was saved across to the next window, "
    "so nothing that was written down is lost when the context resets."
)


def test_a_sentence_about_compaction_finds_the_page_about_compaction(
    real_embedder, monkeypatch, tmp_path
):
    page = "Compaction is not a cliff: you roll through it, and everything saved in the notes comes back when it is spoken of."
    other = "The unit tests are failing on the continuous integration runner because a branch is behind main."
    _cache_of(monkeypatch, tmp_path, [_item("k-compaction", page), _item("k-ci", other)])
    path = _transcript(tmp_path, ("assistant", REPLY))

    mine = ow.own_words_block(path, set())

    assert mine.shown_ids == {"k-compaction"}
    assert "Compaction is not a cliff" in mine.lines[0]


def test_what_his_message_already_found_is_not_shown_again(real_embedder, monkeypatch, tmp_path):
    page = "Compaction is not a cliff: you roll through it, and everything saved in the notes comes back when it is spoken of."
    _cache_of(monkeypatch, tmp_path, [_item("k-compaction", page)])
    path = _transcript(tmp_path, ("assistant", REPLY))

    assert ow.own_words_block(path, {"k-compaction"}).lines == []


def test_the_same_page_is_not_shown_two_turns_running(real_embedder, monkeypatch, tmp_path):
    page = "Compaction is not a cliff: you roll through it, and everything saved in the notes comes back when it is spoken of."
    _cache_of(monkeypatch, tmp_path, [_item("k-compaction", page)])
    path = _transcript(tmp_path, ("assistant", REPLY))

    assert ow.own_words_block(path, set()).shown_ids == {"k-compaction"}
    assert ow.own_words_block(path, set()).lines == [], "a repeated line becomes wallpaper"


def test_a_gates_own_refusal_saved_as_a_lesson_is_never_handed_back(
    real_embedder, monkeypatch, tmp_path
):
    gate = "Stop hook feedback: compaction is not a cliff and everything saved in the notes comes back when spoken of."
    _cache_of(monkeypatch, tmp_path, [_item("k-gate", gate)])
    path = _transcript(tmp_path, ("assistant", REPLY))

    assert ow.own_words_block(path, set()).lines == []


def test_a_search_that_could_not_run_says_so_and_is_not_mistaken_for_nothing(monkeypatch, tmp_path):
    _cache_of(monkeypatch, tmp_path, [])
    monkeypatch.setattr(retriever, "_embed_topic", lambda text: None)
    path = _transcript(tmp_path, ("assistant", REPLY))

    mine = ow.own_words_block(path, set())

    assert mine.could_not_run and mine.lines == []


def test_his_message_finds_exactly_what_it_found_before_the_new_block_exists(monkeypatch, tmp_path):
    """The invariant: the new block adds a block and never changes the first one."""
    from divineos.core import memory_linkage as ml

    class P:
        def __init__(self, i):
            self.id = i
            self.content = f"content {i}"
            self.path_or_ref = ""
            self.source = "knowledge"
            self.similarity = 0.5

    payloads = [P("a"), P("b")]
    monkeypatch.setattr(ml, "retrieve_for_context", lambda prompt, context=None: payloads)
    monkeypatch.setattr(retriever, "lane_state", lambda: {})
    monkeypatch.setattr("divineos.core.memory_linkage_retriever_v2.install", lambda: None)
    without = ml.compose_block("anything at all here", None).text
    monkeypatch.setattr(
        ow,
        "own_words_block",
        lambda p, ids: ow.OwnWords(lines=["- [x, 0.5] mine"], shown_ids={"z"}),
    )
    path = _transcript(tmp_path, ("assistant", REPLY))
    with_block = ml.compose_block("anything at all here", str(path)).text

    assert with_block.startswith(without)
    assert "CLOSE TO WHAT I SAID LAST TURN" in with_block


def test_one_text_filed_in_two_stores_is_one_line(real_embedder, monkeypatch, tmp_path):
    page = "Compaction is not a cliff: you roll through it, and everything saved in the notes comes back when it is spoken of."
    _cache_of(
        monkeypatch,
        tmp_path,
        [_item("correction-1", page, "correction"), _item("worklist-1", page, "worklist")],
    )
    path = _transcript(tmp_path, ("assistant", REPLY))

    assert len(ow.own_words_block(path, set()).lines) == 1
