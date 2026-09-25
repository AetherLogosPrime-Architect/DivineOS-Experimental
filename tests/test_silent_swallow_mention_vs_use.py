"""Describing a swallow is not committing one.

The silent-swallow checker already learned this once. ``_line_is_comment``
carries the note: it fired on a ``#`` comment in conftest.py that DESCRIBED
the bug the check was built to catch, and the fix stripped pure-comment
lines. It covered ``#`` and stopped there.

On 2026-08-25 it flagged ``hook_surfaces.py`` for a docstring paragraph
explaining why a shell hook's bare ``except``-and-discard was the defect
being migrated away from -- prose about a swallow, in the commit that
removed the swallow. Same lesson, one syntactic form short.

That makes four instruments in this substrate to confuse a quoted pattern
with an executed one, so the boundary gets a test rather than another
comment.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_silent_swallow import _docstring_lines, _line_is_comment  # noqa: E402

SAMPLE = '''"""Module docstring that mentions except Exception: pass as prose."""


def real() -> None:
    try:
        risky()
    except ValueError: pass


def described() -> None:
    """Explains that `except ValueError: pass` is the shape we removed."""
    handle()
'''


def _write(tmp_path: Path) -> str:
    path = tmp_path / "sample.py"
    path.write_text(SAMPLE, encoding="utf-8")
    return str(path)


def test_prose_lines_are_covered_and_code_lines_are_not(tmp_path):
    path = _write(tmp_path)
    covered = _docstring_lines(path)

    lines = SAMPLE.splitlines()
    module_doc = (
        lines.index('"""Module docstring that mentions except Exception: pass as prose."""') + 1
    )
    real_swallow = lines.index("    except ValueError: pass") + 1
    func_doc = next(
        i + 1 for i, text in enumerate(lines) if text.strip().startswith('"""Explains that')
    )

    assert module_doc in covered, "module docstring must be treated as prose"
    assert func_doc in covered, "function docstring must be treated as prose"
    assert real_swallow not in covered, "an executed swallow must stay visible to the check"


def test_unparseable_file_fails_toward_flagging(tmp_path):
    """Could-not-look must not become a licence to swallow.

    Everywhere else in this substrate, an instrument that cannot look says
    so. Here the honest equivalent is to suppress nothing: an empty set
    means every line stays scannable, so a broken file yields false
    positives rather than a silent pass.
    """
    path = tmp_path / "broken.py"
    path.write_text("def (((", encoding="utf-8")

    assert _docstring_lines(str(path)) == set()


def test_missing_file_fails_toward_flagging(tmp_path):
    assert _docstring_lines(str(tmp_path / "absent.py")) == set()


def test_non_python_paths_are_not_parsed(tmp_path):
    path = tmp_path / "hook.sh"
    path.write_text("#!/bin/bash\necho hi\n", encoding="utf-8")

    assert _docstring_lines(str(path)) == set()


def test_hash_comments_still_handled_by_the_older_rule():
    """The docstring rule ADDS to the comment rule; it does not replace it."""
    assert _line_is_comment("    # except ValueError: pass", "x.py")
    assert not _line_is_comment("    except ValueError: pass", "x.py")
