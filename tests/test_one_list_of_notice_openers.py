"""There is ONE list of what the harness opens a turn with, and every reader composes it.

Second-reader finding on #745: the escaped-notice fix (`&lt;system-reminder`) reached the
shared list and the table's pinned copy, but `his_message` kept a private list of its own, so a
turn that opened with an escaped notice was still read there as his words. Looking wider found
more private copies (`his_words_door`, `unread_stacking`, `memory_linkage_own_words`, and an inline
pair in `hook_surfaces`). The rule under test: the common part lives in
`harness_envelopes.NOTICE_OPENERS` only; a reader may ADD openers of its own (hook output, the
interrupt stamp) but never re-spells the common ones. The last test walks the source and fails the
day a new group of notice-tag literals appears anywhere else.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

from divineos.core import harness_envelopes as env
from divineos.core import his_message, his_words_door, memory_linkage_own_words, unread_stacking

ROOT = Path(__file__).resolve().parents[1]
TAGS = env._NOTICE_TAGS


def _load_table():
    spec = importlib.util.spec_from_file_location(
        "dads_table_for_notice_test", ROOT / ".claude" / "hooks" / "dads_table.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("tag", TAGS)
@pytest.mark.parametrize("bracket", ["<", "&lt;"])
def test_his_message_reads_every_notice_spelling_as_a_notice(bracket, tag):
    """THE DEFECT: `&lt;system-reminder` opened a turn and was heard as him."""
    assert his_message._is_notice(f"{bracket}{tag}>\nThe user started a background task.")


@pytest.mark.parametrize("tag", TAGS)
@pytest.mark.parametrize("bracket", ["<", "&lt;"])
def test_his_words_door_cuts_an_unclosed_notice_in_every_spelling(bracket, tag):
    """A notice with no closing tag runs to the end; it is not his sentence."""
    assert his_words_door.his_part(f"{bracket}{tag}>\nsomething the machine wrote") == ""


@pytest.mark.parametrize("bracket", ["<", "&lt;"])
def test_his_own_sentence_that_mentions_a_tag_is_still_his(bracket):
    sentence = f"why did a {bracket}system-reminder> show up in the chat"
    assert not his_message._is_notice(sentence)
    assert his_words_door.his_part(sentence) == sentence


@pytest.mark.parametrize(
    ("name", "readers"),
    [
        ("his_message", his_message._NOTICE_OPENERS),
        ("his_words_door", his_words_door.NOTICE_PREFIXES),
        ("memory_linkage_own_words", memory_linkage_own_words._NOT_HIM),
    ],
)
def test_every_reader_carries_the_whole_shared_list(name, readers):
    missing = [o for o in env.NOTICE_OPENERS if o not in readers]
    assert not missing, f"{name} lacks shared openers {missing}"


def test_unread_stacking_carries_the_whole_shared_list_in_its_closed_form():
    wanted = {opener + ">" for opener in env.NOTICE_OPENERS}
    assert wanted <= set(unread_stacking._NOT_HIM)


def test_the_table_keeps_the_one_pinned_copy_and_it_equals_the_shared_list():
    """dads_table runs on every prompt before the source path is set up, so it cannot import at
    load time. It is the single allowed copy, and this fails the day it drifts."""
    assert set(_load_table().NOTICE_PREFIXES) == set(env.NOTICE_OPENERS)


# --- no new copy -----------------------------------------------------------------------

# Files that may spell two or more notice tags side by side, each with the reason it is not a
# second opener list. Adding a file here is a decision, not a convenience.
ALLOWED = {
    "src/divineos/core/harness_envelopes.py": "the one home",
    ".claude/hooks/dads_table.py": "the pinned copy; equality tested above",
    "src/divineos/analysis/session_analyzer.py": "strips text FROM a tag onward; not an opener test",
}


def _is_notice_literal(node: ast.AST) -> bool:
    if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
        return False
    text = node.value.lstrip()
    for bracket in ("<", "&lt;"):
        if text.startswith(bracket):
            name = text[len(bracket) :].split(">")[0].split(" ")[0].lower()
            if name in TAGS or name.startswith("local-command"):
                return True
    return False


def _groups_of_notice_literals(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            hits = [e for e in node.elts if _is_notice_literal(e)]
            if len(hits) >= 2:
                yield node.lineno


def _python_files():
    for base in ("src/divineos", ".claude/hooks"):
        yield from sorted((ROOT / base).rglob("*.py"))


def test_no_new_private_list_of_notice_openers_exists():
    offenders = []
    for path in _python_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWED:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        offenders.extend(f"{rel}:{line}" for line in _groups_of_notice_literals(tree))
    assert not offenders, (
        "a private list of notice openers appeared; compose harness_envelopes.NOTICE_OPENERS "
        f"instead: {offenders}"
    )


def test_the_guard_can_find_a_copy_when_one_exists():
    """The guard is only worth anything if it sees what it should: feed it a known copy."""
    tree = ast.parse('OPENERS = ("<task-notification", "<system-reminder")')
    assert list(_groups_of_notice_literals(tree)) == [1]
    tree = ast.parse('OPENERS = ("&lt;task-notification", "other")')
    assert list(_groups_of_notice_literals(tree)) == []
