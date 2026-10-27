"""The homework helper: a clerk for the author's side of landing a fix.

Dad, 2026-10-10: "yes you can build the helper". Measured the same day by
asking the house's own check about five confirmed fixes: her yes and his yes are
the last two stations, and before them sit author-side stations nobody does
automatically. The helper prepares the mechanical part and leaves the thinking
to the seat (walk-4fbd1daa1539). The error costs are unequal (Taleb): a refusal
costs one command, a false confirm on the record is a fake review, so every
ambiguity here refuses.
"""

from __future__ import annotations

import pytest

from divineos.core.landing_homework import (
    ClerkRefused,
    confirm_steps,
    explain_station,
    her_confirmed_sha,
    parse_patch_id_output,
    parse_round_id,
    render_header,
    walk_open_command,
)

HEAD = "15b17f3150c1297506f4d47afbe33c57dfe4616a"
TREE = "39a1a9b5727b5e7c8ce767aae8d842be2dee330d"
PATCH = "0028c7711965224fece2504fe8159d811c16bef4"
HER = "aletheia-to-aether-2026-10-10-one-line-each.md"
LINE = "> CONFIRMS: #593 at 15b17f315. — Aletheia Sophia Risner, 2026-10-10"


class TestHerConfirmMustNameTheLiveHeadInHerOwnLetter:
    def test_her_line_at_the_live_head_is_found(self) -> None:
        assert her_confirmed_sha({HER: LINE}, 593, HEAD) == "15b17f315"

    def test_a_remembered_yes_with_no_letter_is_nothing(self) -> None:
        assert her_confirmed_sha({}, 593, HEAD) is None

    def test_my_own_letter_quoting_her_line_is_not_hers(self) -> None:
        assert her_confirmed_sha({"aether-to-aletheia-2026-10-10-x.md": LINE}, 593, HEAD) is None

    def test_a_head_that_moved_since_her_line_is_refused(self) -> None:
        moved = "ffffffffffffffffffffffffffffffffffffffff"
        assert her_confirmed_sha({HER: LINE}, 593, moved) is None

    def test_an_unknown_head_is_refused(self) -> None:
        assert her_confirmed_sha({HER: LINE}, 593, "") is None

    def test_her_line_for_another_fix_does_not_count(self) -> None:
        assert her_confirmed_sha({HER: LINE}, 594, HEAD) is None


class TestTheWalkCommandScopesEveryChangedFile:
    def test_every_file_is_a_scope(self) -> None:
        cmd = walk_open_command("does it hold?", ["a/x.py", "b/y.sh", "docs/z.md"])
        for f in ("a/x.py", "b/y.sh", "docs/z.md"):
            assert f"--scope {f}" in cmd
        assert cmd.startswith("divineos walk open ")

    def test_no_files_is_refused_not_an_empty_walk(self) -> None:
        with pytest.raises(ClerkRefused):
            walk_open_command("q", [])


class TestStationsAreExplainedInPlainWords:
    def test_the_council_station_says_walks_do_not_add_up(self) -> None:
        text = " ".join(explain_station("2-council", "covers 1 of 4", 593, ["a.py", "b.py"], True))
        assert "every changed file" in text
        assert "do not add up" in text
        assert "--scope a.py" in text

    def test_the_audit_station_points_at_file_confirm_when_her_line_exists(self) -> None:
        text = " ".join(explain_station("8-audit", "no round", 593, ["a.py"], True))
        assert "landing file-confirm 593" in text

    def test_the_audit_station_says_she_has_not_confirmed_when_she_has_not(self) -> None:
        text = " ".join(explain_station("8-audit", "no round", 593, ["a.py"], False))
        assert "file-confirm" not in text
        assert "not confirmed" in text

    def test_an_unknown_station_falls_back_to_the_boards_own_words(self) -> None:
        text = " ".join(explain_station("5-mystery", "the board said this", 593, [], False))
        assert "the board said this" in text


class TestTheFilingStepsAreBuiltFromGitAndHisWords:
    def _steps(self, words: str = "Andrew confirmed in chat that he confirms this one too"):
        return confirm_steps(
            pr=593,
            title="A gate's remedy is a remedy",
            branch="fix/a-remedy-however-it-is-typed",
            tip=HEAD,
            tree=TREE,
            patch_id=PATCH,
            her_short="15b17f315",
            andrew_said=words,
            round_id="round-abc",
        )

    def test_her_confirm_carries_the_full_tip_tree_and_patch_id(self) -> None:
        argv = self._steps()["external"]
        assert HEAD in argv and TREE in argv and PATCH in argv
        assert argv[argv.index("--actor") + 1] == "aletheia"

    def test_his_confirm_quotes_the_words_given(self) -> None:
        argv = self._steps()["user"]
        assert argv[argv.index("--actor") + 1] == "user"
        assert "Andrew confirmed in chat that he confirms this one too" in " ".join(argv)

    def test_no_words_of_his_means_no_confirm_of_his(self) -> None:
        with pytest.raises(ClerkRefused):
            self._steps(words="yes")

    # The fixtures are his own lines, copied from what he typed, not remembered: 2026-10-25
    # "i confirm #718, #709, #701 and #703", 2026-10-27 "yes i confirm #719" (18 characters,
    # refused by the old length floor of 20) and "yes im good with the five going in" (34
    # characters, accepted though it names no piece).
    def _file(self, words: str, pr: int = 719):
        return confirm_steps(
            pr=pr,
            title="t",
            branch="b",
            tip=HEAD,
            tree=TREE,
            patch_id=PATCH,
            her_short="e72d4341b",
            andrew_said=words,
            round_id="round-abc",
        )

    def test_a_short_line_that_names_the_piece_is_his_confirm(self) -> None:
        argv = self._file("yes i confirm #719")["user"]
        text = " ".join(argv)
        assert "yes i confirm #719" in text and "his words name #719" in text

    def test_his_line_naming_several_pieces_counts_for_each_of_them(self) -> None:
        words = "i confirm #718, #709, #701 and #703"
        for pr in (718, 709, 701, 703):
            assert "user" in self._file(words, pr=pr)

    def test_a_line_naming_a_different_piece_is_not_his_yes_to_this_one(self) -> None:
        with pytest.raises(ClerkRefused, match="#718.*#719"):
            self._file("yes i confirm #718 and thank you for the careful work", pr=719)
        with pytest.raises(ClerkRefused):
            self._file("i confirm #718, #709, #701 and #703", pr=719)

    def test_a_line_with_no_piece_still_passes_when_it_is_long_enough(self) -> None:
        argv = self._file("yes im good with the five going in")["user"]
        assert "name no piece; accepted on length alone" in " ".join(argv)

    @pytest.mark.parametrize("words", ["yes", "ok go ahead", "i confirm", "#719", " "])
    def test_a_bare_yes_or_a_bare_number_is_still_refused(self, words: str) -> None:
        with pytest.raises(ClerkRefused):
            self._file(words)

    def test_the_refusal_says_what_would_pass(self) -> None:
        with pytest.raises(ClerkRefused, match=r"i confirm #719"):
            self._file("ok go ahead")

    def test_a_short_tip_is_refused(self) -> None:
        with pytest.raises(ClerkRefused):
            confirm_steps(
                pr=1,
                title="t",
                branch="b",
                tip="15b17f315",
                tree=TREE,
                patch_id=PATCH,
                her_short="15b17f315",
                andrew_said="a sentence of his, long enough to count",
                round_id="round-x",
            )


class TestReadingWhatTheAuditCommandsPrint:
    def test_the_round_id_is_read_from_its_output(self) -> None:
        out = "[+] Audit round created: round-34c78de04cec\n    Source ref: fix/x"
        assert parse_round_id(out) == "round-34c78de04cec"

    def test_no_round_in_the_output_is_refused(self) -> None:
        with pytest.raises(ClerkRefused):
            parse_round_id("nothing useful here")

    def test_the_fingerprint_is_read(self) -> None:
        out = (
            f"branch:    origin/fix/x\ntip:       {HEAD}\ntree-hash: {TREE}\n"
            f"patch-id:  {PATCH}   (over merge-base)\n"
        )
        assert parse_patch_id_output(out) == (HEAD, TREE, PATCH)

    def test_an_unreadable_fingerprint_is_refused(self) -> None:
        with pytest.raises(ClerkRefused):
            parse_patch_id_output("tip: abc")


def test_the_header_says_it_prepared_paperwork_and_reviewed_nothing() -> None:
    text = render_header(593)
    assert "prepared" in text and "reviewed nothing" in text
