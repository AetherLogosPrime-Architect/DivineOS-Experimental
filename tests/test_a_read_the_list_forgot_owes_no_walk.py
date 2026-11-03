"""A pure read must not owe a council walk, whatever its verb is called.

2026-10-25: `divineos compass-ops spectrums` (it only prints) owed a full walk, because the look list
held `show, list, status, summary, history, overdue, windows` and nothing else. Dad: fix the gates so
they are not a pain. The fix is to add only verbs that are plainly reads, and to keep every write
charged, which is what the second half of this file pins.
"""

import pytest

from divineos.core.gravity_classifier import score_substrate_modification


def _fired(command: str) -> tuple[str, ...]:
    return tuple(score_substrate_modification("Bash", bash_command=command).fired_features)


@pytest.mark.parametrize(
    "command",
    [
        "divineos compass-ops spectrums",
        "divineos journal search gate",
        "divineos audit list-clean",
        "divineos audit surprises",
        "divineos audit unknown-unknown-rate",
    ],
)
def test_a_command_that_only_reads_owes_nothing(command):
    assert "substrate-write-cli" not in _fired(command)


@pytest.mark.parametrize(
    "command",
    [
        # `compass-ops observe` and `journal save|link` were pinned here before main made record-only commands
        # exempt (they are my own record, not data others read); that exemption is main's, so they are not pinned.
        "divineos compass-ops dismiss --reason x",
        "divineos claim statement --tier 3",
        "divineos decide x --why y",
        "divineos audit submit-round focus --actor user",
        "divineos audit resolve f1 --status RESOLVED",
        "divineos audit tag-clean s1",
    ],
)
def test_a_command_that_writes_is_still_charged(command):
    assert "substrate-write-cli" in _fired(command)


def test_a_read_that_redirects_into_a_file_is_still_a_write():
    # Under the verbs main charges, a look that is redirected into a file is a write; `compass-ops` is not one of
    # those verbs any more, so the pin is on an audit look.
    assert "substrate-write-cli" in _fired("divineos audit list-clean > out.txt")
