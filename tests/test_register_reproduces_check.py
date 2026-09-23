"""A generator that produced nothing must not be reported as drift.

Aletheia's attack on the three-outcome design, 2026-09-19: the clean tree
builds, the generator runs, and the generator itself fails or produces
nothing -- third outcome, or mismatch?

A crash was already covered: a non-zero exit returns COULD_NOT_CHECK before
the diff ever runs. The quieter half was not. A generator that exits zero and
writes nothing leaves a file that compares unequal to the committed one, and
the comparison would have called that DRIFTED.

Her point about the failure direction is the reason this matters rather than
being a tidiness question: reporting drift sends someone to regenerate the
file, which is the remedy for drift and does nothing at all for a generator
that produced no bytes. A correct-sounding instruction pointing at the wrong
repair is worse than no instruction.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_automation_register.py"


@pytest.fixture(scope="module")
def register_module():
    spec = importlib.util.spec_from_file_location("generate_automation_register", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_missing_register_is_could_not_look_not_a_mismatch(register_module, tmp_path):
    reason = register_module._why_nothing_was_produced(tmp_path / "never_written.md")
    assert reason is not None
    assert "wrote no register" in reason


def test_an_empty_register_is_could_not_look_not_a_mismatch(register_module, tmp_path):
    empty = tmp_path / "AUTOMATION_REGISTER.md"
    empty.write_text("", encoding="utf-8")

    reason = register_module._why_nothing_was_produced(empty)
    assert reason is not None
    assert "empty register" in reason


def test_a_real_register_is_comparable(register_module, tmp_path):
    written = tmp_path / "AUTOMATION_REGISTER.md"
    written.write_text("# Automation Register\n\none row\n", encoding="utf-8")

    assert register_module._why_nothing_was_produced(written) is None
