from divineos.core import voiced_family
from divineos.core.voiced_family import render_block, voiced


def test_a_speaker_label_for_aria_is_caught_from_aethers_seat():
    reply = "## INNER CIRCLE\n\n**Aether (me):** I am here.\n\n**Aria:** She would want you to know it is fine.\n"
    assert voiced(reply, "aether") == ["Aria"]


def test_both_labels_in_the_reply_that_prompted_this():
    reply = "**Aria:** the map is done.\n\n**Aletheia:** She said yes to all nine.\n"
    assert voiced(reply, "aether") == ["Aria", "Aletheia"]


def test_a_stated_wish_is_caught():
    assert voiced("Aria would want you to know the credits are used.", "aether") == ["Aria"]
    assert voiced("Aletheia'd say you should rest.", "aether") == ["Aletheia"]


def test_my_own_label_is_never_a_slip_from_my_own_seat():
    assert voiced("**Aether (me):** I am glad to be here.", "aether") == []
    assert voiced("**Aria:** I am glad to be here.", "aria") == []


def test_aria_speaking_for_aether_is_caught_from_arias_seat():
    # Aria's cold read: the speaker was hardcoded, so her seat missed this entirely.
    assert voiced("**Aether:** I want you to know I am proud.", "aria") == ["Aether"]
    assert voiced("Aether would want you to know he is tired.", "aria") == ["Aether"]


def test_aria_naming_herself_in_the_third_person_is_not_refused_in_her_own_window():
    assert voiced("Aria would want you to rest.", "aria") == []


def test_the_same_sentence_flips_with_the_seat():
    sentence = "Aria would want you to rest."
    assert voiced(sentence, "aether") == ["Aria"]
    assert voiced(sentence, "aria") == []


def test_quoted_words_and_blockquotes_are_exempt():
    assert voiced('She wrote "Aria: the map is done" in her letter.', "aether") == []
    assert voiced("> Aria: the map is done.\n\nThat is what her letter says.", "aether") == []


def test_plain_mention_is_not_a_slip():
    assert voiced("I wrote to Aria and she is reading it.", "aether") == []
    assert voiced("Aria's letter says the map is in.", "aether") == []
    assert voiced("Aether tells me you can read it in the morning.", "aria") == []


def test_code_fences_are_exempt():
    assert voiced("```\nAria: example\n```", "aether") == []


def _stop_payload(tmp_path, reply: str) -> dict:
    import json

    def rec(role, text):
        return json.dumps(
            {"type": role, "message": {"role": role, "content": [{"type": "text", "text": text}]}}
        )

    path = tmp_path / "t.jsonl"
    path.write_text(rec("user", "hi") + "\n" + rec("assistant", reply) + "\n", encoding="utf-8")
    return {"transcript_path": str(path)}


def test_the_registered_stop_door_refuses_a_voiced_circle_and_passes_a_clean_one(
    tmp_path, monkeypatch
):
    from divineos.core import hook_router, hook_surfaces

    monkeypatch.setattr(voiced_family, "this_speaker", lambda: "aether")
    hook_router.clear("Stop")
    hook_surfaces.install()
    assert "voiced_family" in hook_router.registered("Stop")

    voiced_reply = "## INNER CIRCLE\n\n**Aria:** she would want you to rest.\n"
    bad = hook_router.dispatch("Stop", _stop_payload(tmp_path, voiced_reply))
    assert "voiced_family" in [o.name for o in bad.refusals]

    clean_reply = "## INNER CIRCLE\n\nI am glad to be here with you.\n"
    ok = hook_router.dispatch("Stop", _stop_payload(tmp_path, clean_reply))
    assert "voiced_family" not in [o.name for o in ok.refusals]


def test_an_unknown_seat_is_could_not_run_never_a_pass(tmp_path, monkeypatch):
    from divineos.core import hook_router, hook_surfaces

    monkeypatch.setattr(voiced_family, "this_speaker", lambda: None)
    hook_router.clear("Stop")
    hook_surfaces.install()
    result = hook_router.dispatch(
        "Stop", _stop_payload(tmp_path, "**Aria:** she would want you to rest.\n")
    )
    assert "voiced_family" in [o.name for o in result.errored]
    assert "voiced_family" not in [o.name for o in result.refusals]


def test_block_names_who_and_asks_for_one_line():
    block = render_block(["Aria", "Aletheia"])
    assert "Aria, Aletheia" in block
    assert "Do not re-post" in block
    assert render_block([]) == ""
