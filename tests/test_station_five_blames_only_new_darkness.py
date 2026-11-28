"""Station 5 blames a request only for surfaces dark on its branch and not dark on main.

Aletheia 2026-11-28, #884 held: matching a request's file paths against the dark list was
blind. Deleting the caller of a surface, or adding a dark one outside core/, passed with
"nothing left unreachable". The honest question is what became dark that main did not have.
"""

from divineos.core.build_flow import Status, check_test_station

CODE = "src/divineos/cli/x.py"
TEST = "tests/test_x.py"


def test_a_surface_dark_on_both_is_not_this_requests_fault():
    r = check_test_station([CODE, TEST], ["ablation_summary"], ["ablation_summary"])
    assert r.status is Status.SATISFIED


def test_it_never_says_nothing_is_unreachable_while_something_is():
    r = check_test_station([CODE, TEST], ["ablation_summary"], ["ablation_summary"])
    assert "nothing left unreachable" not in r.detail
    assert "none new" in r.detail


def test_deleting_the_caller_of_a_surface_is_caught_though_its_file_is_untouched():
    # the surface's own module is not in the changed paths; the caller was edited
    r = check_test_station(["src/divineos/core/multiplex_panels.py", TEST], ["journal"], [])
    assert r.status is Status.MISSING
    assert "journal" in r.detail


def test_a_new_dark_surface_anywhere_is_caught():
    r = check_test_station(["src/divineos/cli/new_thing.py", TEST], ["new_thing"], [])
    assert r.status is Status.MISSING


def test_only_the_new_one_is_named():
    r = check_test_station([CODE, TEST], ["old", "new"], ["old"])
    assert r.status is Status.MISSING
    assert "new" in r.detail and "old" not in r.detail


def test_clean_on_both_says_so():
    r = check_test_station([CODE, TEST], [], [])
    assert r.status is Status.SATISFIED
    assert "nothing left unreachable" in r.detail


def test_an_unreadable_branch_list_cannot_check():
    assert check_test_station([CODE, TEST], None, []).status is Status.CANNOT_CHECK


def test_an_unreadable_main_list_cannot_check_it_never_assumes_clean():
    assert check_test_station([CODE, TEST], ["x"], None).status is Status.CANNOT_CHECK


def test_no_tests_touched_is_still_missing():
    assert check_test_station([CODE], [], []).status is Status.MISSING


def test_prose_only_still_has_nothing_to_wire():
    assert check_test_station(["docs/a.md"], ["x"], []).status is Status.SATISFIED


def test_the_real_registry_on_this_tree_does_not_block_a_request_that_edits_memory_journal():
    # memory_journal is hand-wired in knowledge_commands and listed in ALREADY_LIVE, so the
    # real dark list on this tree must not carry it (Aria's cold read of #884).
    from divineos.core.surface_registry import dark_surfaces

    branch = dark_surfaces()
    assert "memory_journal" not in branch
    r = check_test_station(
        ["src/divineos/core/memory_journal.py", TEST], branch, ["memory_journal"]
    )
    assert r.status is Status.SATISFIED
