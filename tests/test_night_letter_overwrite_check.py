"""A Write over an existing shared night letter is refused; creation is not.

Two seats append to one file per night. Write replaces the whole file, and on
a new file it says "created" where on an existing one it says "updated", so the
overwrite looks routine. Last night Aria's Write replaced Aether's section.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import night_letter_overwrite_check as check
from divineos.core.hook_surfaces import night_letter_overwrite_surface


def _write(path: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}}


class TestTheJudgment:
    def test_creation_of_a_new_night_letter_is_allowed(self, tmp_path: Path) -> None:
        target = tmp_path / "the-night-letter-to-andrew-2026-11-03.md"
        assert not check.should_refuse("Write", str(target))

    def test_write_over_an_existing_night_letter_is_refused(self, tmp_path: Path) -> None:
        target = tmp_path / "the-night-letter-to-andrew-2026-11-03.md"
        target.write_text("## From aether\n", encoding="utf-8")
        assert check.should_refuse("Write", str(target))

    def test_refusal_names_both_ways_in(self, tmp_path: Path) -> None:
        target = tmp_path / "the-night-letter-to-andrew-2026-11-03.md"
        target.write_text("x", encoding="utf-8")
        msg = check.refusal_message(str(target))
        assert "Edit" in msg and "## From" in msg
        assert "cat >>" in msg and "<<'EOF'" in msg

    def test_any_other_file_is_untouched(self, tmp_path: Path) -> None:
        other = tmp_path / "some-other-letter.md"
        other.write_text("x", encoding="utf-8")
        assert not check.should_refuse("Write", str(other))
        near = tmp_path / "the-night-letter-to-aria-2026-11-03.md"
        near.write_text("x", encoding="utf-8")
        assert not check.should_refuse("Write", str(near))

    def test_edit_and_other_tools_are_not_this_doors_business(self, tmp_path: Path) -> None:
        target = tmp_path / "the-night-letter-to-andrew-2026-11-03.md"
        target.write_text("x", encoding="utf-8")
        assert not check.should_refuse("Edit", str(target))
        assert not check.should_refuse("Bash", str(target))

    @pytest.mark.parametrize(
        "path",
        [
            "C:\\Users\\a\\.divineos-shared\\letters\\the-night-letter-to-andrew-2026-11-03.md",
            "C:/Users/a/.divineos-shared/letters/the-night-letter-to-andrew-2026-11-03.md",
            "~/.divineos-shared/letters/the-night-letter-to-andrew-2026-11-03.md",
        ],
    )
    def test_backslash_and_forward_slash_paths_both_match(self, path: str) -> None:
        # exists is injected: a Windows path cannot be stat'ed on this box.
        assert check.should_refuse("Write", path, exists=lambda p: True)
        assert not check.should_refuse("Write", path, exists=lambda p: False)

    def test_a_bad_date_shape_does_not_match(self) -> None:
        assert not check.should_refuse(
            "Write", "/x/the-night-letter-to-andrew-tonight.md", exists=lambda p: True
        )


def test_the_door_is_actually_registered_on_the_doorbell() -> None:
    # A surface nothing dispatches is an alarm with the cable coiled beside it.
    from divineos.core.hook_router import registered
    from divineos.core.hook_surfaces import install

    install()
    assert "night_letter_overwrite" in registered("PreToolUse")


class TestTheSurface:
    def test_refuses_through_the_router_shape(self, tmp_path: Path) -> None:
        target = tmp_path / "the-night-letter-to-andrew-2026-11-03.md"
        target.write_text("x", encoding="utf-8")
        out = night_letter_overwrite_surface(_write(str(target)))
        assert out is not None and out.refused and "Edit" in out.reason

    def test_creation_says_nothing(self, tmp_path: Path) -> None:
        target = tmp_path / "the-night-letter-to-andrew-2026-11-04.md"
        out = night_letter_overwrite_surface(_write(str(target)))
        assert out is not None and not out.refused and out.state == "nothing-to-say"

    def test_non_write_payload_says_nothing(self) -> None:
        out = night_letter_overwrite_surface({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        assert out is not None and not out.refused


class TestCaseAndKeyVariants:
    def test_differently_cased_file_name_is_still_a_night_letter(self, tmp_path: Path) -> None:
        target = tmp_path / "The-Night-Letter-To-Andrew-2026-11-03.MD"
        target.write_text("x", encoding="utf-8")
        assert check.should_refuse("Write", str(target))

    def test_lower_case_tool_name_is_still_a_write(self, tmp_path: Path) -> None:
        target = tmp_path / "the-night-letter-to-andrew-2026-11-03.md"
        target.write_text("x", encoding="utf-8")
        assert check.should_refuse("write", str(target))
        assert not check.should_refuse("edit", str(target))

    def test_surface_reads_a_path_key_and_a_lower_case_tool(self, tmp_path: Path) -> None:
        target = tmp_path / "the-night-letter-to-andrew-2026-11-03.md"
        target.write_text("x", encoding="utf-8")
        payload = {"tool_name": "write", "tool_input": {"path": str(target), "content": "x"}}
        out = night_letter_overwrite_surface(payload)
        assert out is not None and out.refused
