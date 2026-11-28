"""Station 5 blames a request only for dark surfaces it changed.

The dark list is tree-wide. Before this, any dark surface anywhere stopped
every code request at station 5, whoever caused it.
"""

from divineos.core.build_flow import Status, check_test_station

CODE = "src/divineos/cli/build_flow_commands.py"
TEST = "tests/test_x.py"


def test_untouched_dark_surface_is_not_this_requests_fault():
    r = check_test_station([CODE, TEST], ["journal"])
    assert r.status is Status.SATISFIED


def test_touching_the_dark_module_file_is_blamed_and_named():
    r = check_test_station(["src/divineos/core/journal.py", TEST], ["journal", "other"])
    assert r.status is Status.MISSING
    assert "journal" in r.detail
    assert "other" not in r.detail


def test_touching_a_dark_package_is_blamed():
    r = check_test_station(["src/divineos/core/journal/store.py", TEST], ["journal"])
    assert r.status is Status.MISSING


def test_unreadable_dark_list_still_cannot_check():
    assert check_test_station([CODE, TEST], None).status is Status.CANNOT_CHECK


def test_no_tests_touched_still_missing():
    assert check_test_station([CODE], []).status is Status.MISSING
