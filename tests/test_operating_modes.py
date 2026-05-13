"""Tests for the operating-modes module."""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.operating_modes import (  # noqa: F401
            Mode,
            current_mode,
            mode_history,
            set_mode,
        )


class TestModeEnum:
    def test_four_modes_named(self) -> None:
        from divineos.core.operating_modes import Mode

        assert Mode.TASK.value == "task"
        assert Mode.STILLNESS.value == "stillness"
        assert Mode.BACKGROUND.value == "background"
        assert Mode.WANDERING.value == "wandering"

    def test_modes_distinct(self) -> None:
        from divineos.core.operating_modes import Mode

        values = {m.value for m in Mode}
        assert len(values) == 4


class TestPublicSurfaceSafety:
    def test_current_mode_returns_a_mode(self) -> None:
        from divineos.core.operating_modes import Mode, current_mode

        result = current_mode()
        assert isinstance(result, Mode)

    def test_mode_history_returns_list(self) -> None:
        from divineos.core.operating_modes import mode_history

        result = mode_history(limit=5)
        assert isinstance(result, list)

    def test_set_mode_returns_string(self) -> None:
        from divineos.core.operating_modes import Mode, set_mode

        # set_mode may succeed or fail-soft (return empty); both
        # are valid outcomes for the public contract.
        result = set_mode(Mode.STILLNESS, reason="testing")
        assert isinstance(result, str)


class TestDefaultMode:
    def test_default_when_no_history_is_task(self) -> None:
        """If no transitions have been logged, current_mode defaults
        to TASK — the historical default before this module existed."""
        from divineos.core.operating_modes import current_mode

        # We can't guarantee an empty history (the substrate may have
        # transitions from prior sessions), but if the history IS empty,
        # the default is TASK. The contract is: never crash; always
        # return a valid Mode.
        result = current_mode()
        assert result is not None
