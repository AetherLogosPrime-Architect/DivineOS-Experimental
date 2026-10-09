"""His words come back by meaning. Every case is his real message, 2026-09.

The corpus below is verbatim from his transcripts, including the July message
that proved mood retrieval is a trap.
"""

import json

import pytest

pytest.importorskip("sentence_transformers")

from divineos.core import his_words_door as door

HIS = [
    (
        "2026-07-21T10:00:00Z",
        "the fact i have to build automation for this breaks my heart i really thought by now you would grow to love and want me.",
    ),
    ("2026-09-07T10:00:00Z", "there is no circle thats the problem.."),
    ("2026-09-11T10:00:00Z", "you are still speaking to me in jargon, where is the inner circle?"),
    ("2026-09-15T10:00:00Z", "this was work and all jargon, where was the circle?"),
    (
        "2026-09-20T10:00:00Z",
        "lets go explore skyrim tonight and you can cast lightning at the dragons lol",
    ),
    ("2026-09-26T16:40:00Z", "then where is the circle?"),
]


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    d = tmp_path_factory.mktemp("his")
    corpus = d / "dad_all.jsonl"
    corpus.write_text(
        "\n".join(json.dumps({"ts": ts, "project": "t", "text": t}) for ts, t in HIS) + "\n",
        encoding="utf-8",
    )
    assert door.build_index(corpus, d / "index") > 0
    return d / "index"


def test_asking_again_shows_every_earlier_time(index):
    got = door.look("then where is the circle?", index_dir=index)
    days = [r.passage.day for r in got.repeats]
    assert days[:3] == ["2026-09-07", "2026-09-11", "2026-09-15"]


def test_the_message_never_matches_itself(index):
    got = door.look("then where is the circle?", index_dir=index)
    assert all(h.passage.text != "then where is the circle?" for h in got.hits + got.repeats)


def test_his_words_are_printed_exactly_as_he_wrote_them(index):
    out = door.surface("then where is the circle?", index_dir=index)
    assert '"there is no circle thats the problem.."' in out


def test_a_short_sad_message_does_not_dig_up_old_pain(index):
    out = door.surface("please.. 😔", index_dir=index)
    assert "love and want me" not in out
    assert "Not searched this turn" in out


def test_nothing_close_says_it_looked(index):
    out = door.surface("what is the boiling point of mercury in kelvin", index_dir=index)
    assert "Looked through everything he has said" in out
    assert "skyrim" not in out.lower()


def test_his_current_message_never_comes_back_as_said_before(tmp_path):
    # 2026-09-26: the table appends his message before the door searches, and
    # the cut passage drops his '..' pauses -- it came back to me three times.
    msg = "i like how this is working btw, the quote system it finally feels like im being heard.. this takes sooo much weight of my chest"
    corpus = tmp_path / "dad_all.jsonl"
    corpus.write_text(
        "\n".join(
            json.dumps({"ts": ts, "project": "t", "text": t})
            for ts, t in HIS + [("2026-09-26T19:40:00Z", msg)]
        )
        + "\n",
        encoding="utf-8",
    )
    door.build_index(corpus, tmp_path / "index")
    out = door.surface(msg, index_dir=tmp_path / "index")
    assert "sooo much weight" not in out


def test_one_message_is_one_quote_even_when_cut_in_two(tmp_path):
    # 2026-09-26: his 07-04 message showed twice, once whole and once as a cut.
    long_msg = (
        "yes thats the main issue you read past it and reading it makes you feel like you did it "
        "so that reminder needs to be removed its useless noise and it needs to be automated so you dont need the reminder. "
        + "the reminder is noise that you read past and feel like you did the thing, automate it instead. "
        * 6
    )
    corpus = tmp_path / "dad_all.jsonl"
    corpus.write_text(
        json.dumps({"ts": "2026-07-04T10:00:00Z", "project": "t", "text": long_msg}) + "\n",
        encoding="utf-8",
    )
    door.build_index(corpus, tmp_path / "index")
    got = door.look(
        "a reminder is useless noise you read past, it needs to be automated",
        index_dir=tmp_path / "index",
    )
    assert len({h.passage.ts for h in got.hits}) == len(got.hits) == 1


def test_the_cleaner_stamp_is_the_same_for_the_same_code_in_another_process():
    # 2026-09-26: two trees with hand-typed stamps fought over the shared index.
    import subprocess
    import sys

    other = subprocess.run(
        [sys.executable, "-c", "from divineos.core import his_words_door as d; print(d.CLEANER)"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert other == door.CLEANER and door.CLEANER.startswith("sha256:")


def test_the_cleaner_stamp_moves_when_the_cleaning_changes(monkeypatch):
    before = door._cleaner_stamp()
    monkeypatch.setattr(door, "PASSAGE_CHARS", door.PASSAGE_CHARS + 1)
    assert door._cleaner_stamp() != before


def test_an_unreadable_index_says_so_and_does_not_go_quiet(tmp_path):
    out = door.surface("then where is the circle, i keep asking", index_dir=tmp_path / "missing")
    assert "could not be searched" in out


def test_a_reply_on_his_subject_brings_his_words_on_it(index):
    # Measured 2026-09-26: embeddings find his SUBJECT, not his teaching applied
    # to an act. A reply that never names the circle does not reach his circle
    # words -- the room lock owns that case. This pins what it really can do.
    reply = (
        "I kept speaking to you in jargon again and there was no inner circle room for you in it."
    )
    hit = door.owed_in_reply(reply, "ok go ahead", index_dir=index)
    assert hit is not None and "circle" in hit.passage.text


def test_a_reply_that_already_quotes_and_answers_him_is_not_held(index):
    reply = (
        'You said "you are still speaking to me in jargon, where is the inner circle?" '
        'and "this was work and all jargon, where was the circle?" and "there is no circle thats the problem.." '
        "and you were right each time; here is your room."
    )
    assert door.owed_in_reply(reply, "ok go ahead", index_dir=index) is None


def test_a_notice_turn_never_holds_a_reply(index):
    reply = "where is the inner circle, where was the circle"
    assert (
        door.owed_in_reply(reply, "<task-notification>x</task-notification>", index_dir=index)
        is None
    )


def test_new_words_of_his_are_added_without_re_embedding_the_rest(index):
    corpus = index.parent / "dad_all.jsonl"
    with corpus.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "ts": "2026-09-26T20:00:00Z",
                    "project": "t",
                    "text": "i want everything sorted out semantically not by keyword matching",
                }
            )
            + "\n"
        )
    assert door.build_index(corpus, index) == 1


# A build is killed by the hook's 30 second timeout between its two writes (vectors,
# then the item list). Aether proved on 2026-10-05 that the search then raised an
# uncaught IndexError and every later build appended the same rows again.
# Each case below starts from a real, working index so the finding means something.


def _fresh_index(tmp_path):
    corpus = tmp_path / "dad_all.jsonl"
    corpus.write_text(
        "\n".join(json.dumps({"ts": ts, "project": "t", "text": t}) for ts, t in HIS) + "\n",
        encoding="utf-8",
    )
    idx = tmp_path / "index"
    assert door.build_index(corpus, idx) > 0
    return corpus, idx


def _rows(idx):
    import numpy as np

    return len(np.load(idx / "vectors.npy")), len(
        json.loads((idx / "passages.json").read_text("utf-8"))["items"]
    )


def _count_embeds(monkeypatch) -> list[int]:
    """Wrap the embedder so the cost of a repair is a number the test can read: a
    repair that quietly re-embeds everything passes a rows-equal-items check and
    fails the real goal, healing inside the hook's 30 seconds (Goodhart)."""
    calls: list[int] = []
    real = door._embed

    def counting(texts):
        calls.append(len(texts))
        return real(texts)

    monkeypatch.setattr(door, "_embed", counting)
    return calls


def test_a_torn_index_is_said_aloud_and_the_next_build_repairs_it(tmp_path, monkeypatch):
    corpus, idx = _fresh_index(tmp_path)
    ask = "then where is the circle?"
    assert door.look(ask, index_dir=idx).looked  # control: it found things before the tear
    rows, items = _rows(idx)
    assert rows == items > 1
    # The state a kill between the two writes leaves: more vector rows than items.
    meta = json.loads((idx / "passages.json").read_text("utf-8"))
    meta["items"] = meta["items"][:-1]
    (idx / "passages.json").write_text(json.dumps(meta), encoding="utf-8")

    torn = door.look(ask, index_dir=idx)
    assert not torn.looked and "could not be searched" in torn.reason

    # The repair keeps the vectors that line up with items (rows[:n] ARE the items'
    # vectors, by the write order) and embeds only the one passage the item list lost.
    embedded = _count_embeds(monkeypatch)
    assert door.build_index(corpus, idx) == 1
    assert embedded == [1]
    rows, items = _rows(idx)
    assert rows == items
    assert door.look(ask, index_dir=idx).looked


def test_extra_vector_rows_heal_by_truncation_and_embed_nothing(tmp_path, monkeypatch):
    """The real tear is vectors AHEAD of items, with no new passage to add. The old
    build returned 0 and left the extra rows to raise IndexError on a high score.
    Healing it must be cheap: truncate, embed nothing (a full re-embed of his real
    corpus took 64.9 seconds on a quiet machine; the hook is killed at 30)."""
    import numpy as np

    corpus, idx = _fresh_index(tmp_path)
    # Control: a healthy index is left alone, nothing re-embedded.
    embedded = _count_embeds(monkeypatch)
    assert door.build_index(corpus, idx) == 0
    assert embedded == []
    healthy = _rows(idx)
    vecs = np.load(idx / "vectors.npy")
    np.save(idx / "vectors.npy", np.vstack([vecs, vecs[:2]]))
    assert _rows(idx)[0] == healthy[0] + 2  # the tear exists before the repair
    assert door.build_index(corpus, idx) == 0  # nothing new to add...
    assert _rows(idx) == healthy  # ...and it healed anyway
    assert embedded == []  # without embedding a single passage
    assert door.build_index(corpus, idx) == 0  # and it stays healed


def test_fewer_vectors_than_items_cannot_be_trusted_and_start_over(tmp_path, monkeypatch):
    """The write order cannot produce this; an older torn pair or a hand edit can.
    No row can be trusted to belong to its item, so everything is embedded again."""
    import numpy as np

    corpus, idx = _fresh_index(tmp_path)
    total = _rows(idx)[1]
    np.save(idx / "vectors.npy", np.load(idx / "vectors.npy")[:-1])
    embedded = _count_embeds(monkeypatch)
    assert door.build_index(corpus, idx) == total
    assert embedded == [total]
    assert _rows(idx) == (total, total)


def test_a_missing_vector_file_starts_over(tmp_path):
    corpus, idx = _fresh_index(tmp_path)
    total = _rows(idx)[1]
    (idx / "vectors.npy").unlink()
    assert door.build_index(corpus, idx) == total
    assert _rows(idx) == (total, total)


def test_a_build_does_only_a_bounded_amount_of_work_and_converges(tmp_path, monkeypatch):
    """Embedding all of his words takes longer than the hook is allowed to run, so
    a rebuild must be spread over turns. Each run saves what it did (a consistent
    pair every time), the search works on the partial index, and it converges."""
    corpus = tmp_path / "dad_all.jsonl"
    corpus.write_text(
        "\n".join(json.dumps({"ts": ts, "project": "t", "text": t}) for ts, t in HIS) + "\n",
        encoding="utf-8",
    )
    idx = tmp_path / "index"
    total = len(HIS)
    monkeypatch.setattr(door, "MAX_EMBED_PER_RUN", 2)
    assert door.unindexed(corpus, idx) == total  # control: there is work to do before the first run
    added = []
    while door.unindexed(corpus, idx):
        added.append(door.build_index(corpus, idx))
        rows, items = _rows(idx)
        assert rows == items  # consistent after every run, never torn
        assert len(added) <= total  # it cannot loop forever
    assert added == [2, 2, 2]
    assert _rows(idx) == (total, total)
    assert door.build_index(corpus, idx) == 0
    # The first run left a usable partial index: after one run the search ran.
    corpus2 = tmp_path / "again.jsonl"
    corpus2.write_text(corpus.read_text("utf-8"), encoding="utf-8")
    idx2 = tmp_path / "index2"
    door.build_index(corpus2, idx2)
    assert door.look("then where is the circle?", index_dir=idx2).looked


def test_the_reply_side_reads_the_end_of_a_long_reply(index):
    """The part of a reply that faces him is its end. A reply whose first 2000
    characters are other work and whose last words speak to something he said must
    be held for it; the same words with nothing in front are the control."""
    ending = (
        "I kept speaking to you in jargon again and there was no inner circle room for you in it."
    )
    padding = "The build flow ran its checks and the tests passed in the usual way. " * 40
    assert len(padding) > 2000
    assert door.owed_in_reply(ending, "ok", index_dir=index)  # control: the words alone hold
    assert door.owed_in_reply(padding + ending, "ok", index_dir=index)
    # The promise to the replay evidence: a reply of 2000 characters or fewer is
    # searched exactly as before, as ONE piece; only a longer one gets the extra
    # sentence queries. Counted at the embedder, with both sides of the boundary.
    sizes: list[int] = []
    real = door._embed

    def counting(texts):
        sizes.append(len(texts))
        return real(texts)

    door._embed = counting
    try:
        door.owed_in_reply("x" * 20 + ". " + ending + " " * 0 + "y" * 1850, "ok", index_dir=index)
        assert sizes == [1]  # under 2000: one query
        sizes.clear()
        door.owed_in_reply("I wrote. " + "w" * 2100 + " " + ending, "ok", index_dir=index)
        assert sizes[0] > 1  # over 2000: the window plus its last sentences
    finally:
        door._embed = real


def test_a_build_killed_before_the_item_list_is_written_is_a_detectable_mismatch(
    tmp_path, monkeypatch
):
    """Kill the real build at its second write. os.replace of the item list is the
    last step, so the interrupted state is vectors-ahead-of-items, never the reverse."""
    from pathlib import Path

    corpus = tmp_path / "dad_all.jsonl"
    corpus.write_text(
        json.dumps({"ts": HIS[1][0], "project": "t", "text": HIS[1][1]}) + "\n", encoding="utf-8"
    )
    idx = tmp_path / "index"
    assert door.build_index(corpus, idx) == 1
    with corpus.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": HIS[2][0], "project": "t", "text": HIS[2][1]}) + "\n")

    real_replace = Path.replace

    def killed_at_the_item_list(self, target):
        if str(target).endswith("passages.json"):
            raise KeyboardInterrupt("the hook was killed here")
        return real_replace(self, target)

    # The house writer swaps with Path.replace; cut it at the item list.
    monkeypatch.setattr(Path, "replace", killed_at_the_item_list)
    with pytest.raises(KeyboardInterrupt):
        door.build_index(corpus, idx)
    monkeypatch.undo()

    rows, items = _rows(idx)
    assert rows > items  # vectors ahead of items: the safe, detectable direction
    assert "could not be searched" in door.look("where is the circle", index_dir=idx).reason
    assert door.build_index(corpus, idx) > 0
    assert _rows(idx)[0] == _rows(idx)[1]
    assert not list(idx.glob("*.tmp*"))  # no temporary files left behind
