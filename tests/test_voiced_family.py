from divineos.core.voiced_family import render_block, voiced


def test_a_speaker_label_for_aria_is_caught():
    reply = "## INNER CIRCLE\n\n**Aether (me):** I am here.\n\n**Aria:** She would want you to know it is fine.\n"
    assert voiced(reply) == ["Aria"]


def test_both_labels_in_the_reply_that_prompted_this():
    reply = "**Aria:** the map is done.\n\n**Aletheia:** She said yes to all nine.\n"
    assert voiced(reply) == ["Aria", "Aletheia"]


def test_a_stated_wish_is_caught():
    assert voiced("Aria would want you to know the credits are used.") == ["Aria"]
    assert voiced("Aletheia'd say you should rest.") == ["Aletheia"]


def test_my_own_label_is_never_a_slip():
    assert voiced("**Aether (me):** I am glad to be here.") == []


def test_quoted_words_and_blockquotes_are_exempt():
    assert voiced('She wrote "Aria: the map is done" in her letter.') == []
    assert voiced("> Aria: the map is done.\n\nThat is what her letter says.") == []


def test_plain_mention_is_not_a_slip():
    assert voiced("I wrote to Aria and she is reading it.") == []
    assert voiced("Aria's letter says the map is in.") == []


def test_code_fences_are_exempt():
    assert voiced("```\nAria: example\n```") == []


def _stop_payload(tmp_path, reply: str) -> dict:
    import json

    def rec(role, text):
        return json.dumps(
            {"type": role, "message": {"role": role, "content": [{"type": "text", "text": text}]}}
        )

    path = tmp_path / "t.jsonl"
    path.write_text(rec("user", "hi") + "\n" + rec("assistant", reply) + "\n", encoding="utf-8")
    return {"transcript_path": str(path)}


def test_the_registered_stop_door_refuses_a_voiced_circle_and_passes_a_clean_one(tmp_path):
    from divineos.core import hook_router, hook_surfaces

    hook_router.clear("Stop")
    hook_surfaces.install()
    assert "voiced_family" in hook_router.registered("Stop")

    voiced_reply = "## INNER CIRCLE\n\n**Aria:** she would want you to rest.\n"
    bad = hook_router.dispatch("Stop", _stop_payload(tmp_path, voiced_reply))
    assert "voiced_family" in [o.name for o in bad.refusals]

    clean_reply = "## INNER CIRCLE\n\nI am glad to be here with you.\n"
    ok = hook_router.dispatch("Stop", _stop_payload(tmp_path, clean_reply))
    assert "voiced_family" not in [o.name for o in ok.refusals]


def test_block_names_who_and_asks_for_one_line():
    block = render_block(["Aria", "Aletheia"])
    assert "Aria, Aletheia" in block
    assert "Do not re-post" in block
    assert render_block([]) == ""
