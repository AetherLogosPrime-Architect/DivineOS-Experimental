"""The build-flow doorman today, pinned before it learns to see worktrees.

Found building his asks' store (2026-09-24): a whole module written in a
worktree of this repository, and no work item ever opened. The doorman
resolves every path against REPO_ROOT, the install's own tree, so a file in
any other checkout -- a worktree of this very repository included -- is "not
code in this tree, not this gate's business." Aether confirmed it through two
doors: calling the function directly, and by writing a test file in his own
worktree that opened nothing.

That matters because of where we build now. Nearly all branch work, his build
included, happens in worktrees. So the inspector stands at the door we used to
work through, which is the front-door failure in another room.

FLIPS IN part 2 of dad_kept_and_known: the doorman resolves against the tree
the call came from. When it does, this test is rewritten to the new behaviour
in the same commit, never deleted quietly.

WHY NO FILES ARE CREATED. The first version built a fake worktree under
tmp_path and failed: this repo's conftest puts tmp_path INSIDE the repo, so
the "outside" tree was inside REPO_ROOT and the doorman rightly counted it.
The instrument was wrong, not the finding. The doorman only resolves path
strings, so a sibling path that never exists on disk is the honest probe --
and nothing is written outside the sandbox.
"""

from __future__ import annotations

from divineos.core import work_item_doorman as wid


def _sibling_checkout_file() -> str:
    """A code path in a checkout beside this one, as a worktree would be."""
    return str(
        wid.REPO_ROOT.parent / "wsomething-sibling-checkout" / "src" / "divineos" / "core" / "x.py"
    )


def test_a_code_file_in_a_sibling_checkout_opens_no_work():
    path = _sibling_checkout_file()
    assert wid._repo_relative(path) is None
    assert wid.needs_an_item([path]) == ()


def test_the_same_file_in_the_install_tree_does_open_work():
    """The contrast that makes the pin mean something: same file, other tree."""
    code = wid.REPO_ROOT / "src" / "divineos" / "core" / "x.py"
    assert wid.needs_an_item([str(code)]) == ("src/divineos/core/x.py",)
