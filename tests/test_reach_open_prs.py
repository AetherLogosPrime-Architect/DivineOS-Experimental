"""`reach open` must look at open pull requests, not only code and git."""

from __future__ import annotations

from divineos.core.reach_open_prs import format_open_pr_section, matching_prs

PRS = [
    {"number": 7, "title": "Sleep refreshes both memory indexes", "headRefName": "job6-x"},
    {"number": 8, "title": "The push gate says could-not-check", "headRefName": "job4-push"},
]


def test_two_shared_content_words_match() -> None:
    hits = matching_prs("sleep does not refresh memory indexes", PRS)
    assert [p["number"] for p in hits] == [7]


def test_one_shared_word_does_not_match() -> None:
    assert matching_prs("sleep forever", PRS) == []


def test_stop_words_and_short_words_ignored() -> None:
    assert matching_prs("the and its new does not with that", PRS) == []


def test_head_branch_words_count_once_each() -> None:
    # "push" appears in title and branch but is one distinct word: not enough.
    assert matching_prs("push refuses", PRS) == []
    assert [p["number"] for p in matching_prs("push gate", PRS)] == [8]


def test_empty_pr_list_says_none_found_not_silence() -> None:
    out = format_open_pr_section("anything here", lambda: [])
    assert out.startswith("Open PRs that may already do this:")
    assert "none" in out.lower()


def test_word_endings_do_not_hide_a_match() -> None:
    prs = [{"number": 9, "title": "Gate stamp ending check", "headRefName": "job-x"}]
    assert [p["number"] for p in matching_prs("gates checking endings", prs)] == [9]


def test_stemming_does_not_join_unrelated_words() -> None:
    prs = [{"number": 9, "title": "Gate stamp ending check", "headRefName": "job-x"}]
    assert matching_prs("garden stamps", prs) == []


def test_none_found_line_says_what_was_searched() -> None:
    out = format_open_pr_section("zzzz qqqq", lambda: PRS)
    assert "only titles and branch names were searched" in out


def test_gh_failure_is_not_a_clean_bill() -> None:
    def boom() -> list:
        raise RuntimeError("gh not found")

    out = format_open_pr_section("sleep memory", boom)
    assert out == "Could not look at open PRs (gh not found): this is not a clean bill."


def test_hits_are_listed_with_number_title_branch() -> None:
    out = format_open_pr_section("sleep memory indexes", lambda: PRS)
    assert "#7" in out and "Sleep refreshes" in out and "job6-x" in out
