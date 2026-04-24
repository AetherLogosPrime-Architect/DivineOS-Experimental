"""Tests for the pre-reg precommit gate (scripts/check_preregs.py).

Falsifiability:
  - Pattern match for each mechanism kind (slice/detector/gate/threshold).
  - Coverage check: name-in-haystack passes; name-absent blocks.
  - Removed lines ("-") and context lines (" ") are ignored.
  - The diff-header "+++" lines don't produce false matches.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_gate_module():
    """Import scripts/check_preregs.py as a module — it's not in a package."""
    path = Path(__file__).resolve().parent.parent / "scripts" / "check_preregs.py"
    spec = importlib.util.spec_from_file_location("check_preregs", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_preregs"] = module
    spec.loader.exec_module(module)
    return module


check_preregs = _load_gate_module()


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------


def _diff_with(body: str, path: str = "src/x.py") -> str:
    """Minimal diff header followed by added lines."""
    return f"+++ b/{path}\n{body}"


class TestParseSlicePattern:
    def test_detects_run_foo_slice(self) -> None:
        diff = _diff_with("+def run_foo_slice():")
        found = check_preregs._parse_new_mechanisms(diff)
        assert len(found) == 1
        assert found[0].kind == "slice"
        assert found[0].name == "foo"

    def test_captures_path(self) -> None:
        diff = _diff_with("+def run_bar_slice():", path="src/a/b.py")
        found = check_preregs._parse_new_mechanisms(diff)
        assert found[0].path == "src/a/b.py"


class TestParseDetectorPattern:
    def test_detects_detect_name(self) -> None:
        diff = _diff_with("+def detect_spike():")
        found = check_preregs._parse_new_mechanisms(diff)
        assert len(found) == 1
        assert found[0].kind == "detector"
        assert found[0].name == "spike"


class TestParseGatePattern:
    def test_foo_gate_is_gate(self) -> None:
        diff = _diff_with("+def foo_gate(x):")
        found = check_preregs._parse_new_mechanisms(diff)
        assert len(found) == 1
        assert found[0].kind == "gate"
        assert found[0].name == "foo"

    def test_underscore_check_is_gate(self) -> None:
        diff = _diff_with("+def _bar_check(x):")
        found = check_preregs._parse_new_mechanisms(diff)
        assert len(found) == 1
        assert found[0].kind == "gate"
        assert found[0].name == "bar"


class TestParseThresholdPattern:
    def test_threshold_constant(self) -> None:
        diff = _diff_with("+MAX_STEP_THRESHOLD = 10")
        found = check_preregs._parse_new_mechanisms(diff)
        assert len(found) == 1
        assert found[0].kind == "threshold"
        assert found[0].name == "MAX_STEP_THRESHOLD"

    def test_limit_suffix_matches(self) -> None:
        diff = _diff_with("+REQUEST_LIMIT = 100")
        found = check_preregs._parse_new_mechanisms(diff)
        assert found and found[0].kind == "threshold"

    def test_max_suffix_matches(self) -> None:
        diff = _diff_with("+TIMEOUT_MAX = 60")
        found = check_preregs._parse_new_mechanisms(diff)
        assert found and found[0].kind == "threshold"

    def test_lowercase_does_not_match(self) -> None:
        # Threshold constants are by convention ALL_CAPS.
        diff = _diff_with("+my_threshold = 10")
        found = check_preregs._parse_new_mechanisms(diff)
        assert found == []


class TestParseNonmatches:
    def test_removed_lines_ignored(self) -> None:
        diff = _diff_with("-def run_old_slice():")
        assert check_preregs._parse_new_mechanisms(diff) == []

    def test_context_lines_ignored(self) -> None:
        diff = _diff_with(" def run_old_slice():")
        assert check_preregs._parse_new_mechanisms(diff) == []

    def test_diff_header_plus_plus_plus_ignored(self) -> None:
        # The "+++ b/path.py" header starts with + but isn't an added line.
        # This is the paranoid guard: if we matched on "+++", we'd flag
        # every file with a plus-sign in the path. The parser must skip.
        diff = "+++ b/src/x.py\n" + "+def run_real_slice():\n"
        found = check_preregs._parse_new_mechanisms(diff)
        assert len(found) == 1
        assert found[0].name == "real"

    def test_normal_function_not_detected(self) -> None:
        diff = _diff_with("+def normal_helper():")
        assert check_preregs._parse_new_mechanisms(diff) == []

    def test_test_path_is_exempt(self) -> None:
        """Test files describe mechanisms; they don't introduce them.
        Without this exemption the gate false-positives on test methods
        whose names match mechanism patterns (e.g. test_foo_gate_is_gate).
        """
        diff = _diff_with("+def run_real_slice():", path="tests/test_x.py")
        assert check_preregs._parse_new_mechanisms(diff) == []

    def test_scripts_path_is_exempt(self) -> None:
        """Scripts/ is tooling, not agent behavior. A helper named
        *_gate or detect_* in a build script isn't a runtime mechanism."""
        diff = _diff_with("+def detect_something():", path="scripts/x.py")
        assert check_preregs._parse_new_mechanisms(diff) == []

    def test_src_path_is_not_exempt(self) -> None:
        """Sanity: the exemption is narrow. src/ paths remain gated."""
        diff = _diff_with("+def run_new_slice():", path="src/divineos/x.py")
        found = check_preregs._parse_new_mechanisms(diff)
        assert len(found) == 1 and found[0].name == "new"


# ---------------------------------------------------------------------------
# Coverage check
# ---------------------------------------------------------------------------


class TestFindUncovered:
    def _mk(self, name: str, kind: str = "slice") -> check_preregs.NewMechanism:
        return check_preregs.NewMechanism(
            kind=kind, name=name, line=f"def run_{name}_slice():", path="x.py"
        )

    def test_covered_if_name_in_haystack(self) -> None:
        mechs = [self._mk("alpha")]
        haystack = "some text alpha slice blah"
        assert check_preregs._find_uncovered(mechs, haystack) == []

    def test_uncovered_if_name_absent(self) -> None:
        mechs = [self._mk("beta")]
        haystack = "some text alpha slice blah"
        uncovered = check_preregs._find_uncovered(mechs, haystack)
        assert len(uncovered) == 1
        assert uncovered[0].name == "beta"

    def test_case_insensitive_match(self) -> None:
        mechs = [self._mk("Alpha")]
        haystack = "pre-reg about the ALPHA mechanism"
        # haystack is already-lowercased in the real pipeline, but the
        # mechanism name is case-matched lower.
        assert check_preregs._find_uncovered(mechs, haystack.lower()) == []

    def test_empty_haystack_blocks_everything(self) -> None:
        mechs = [self._mk("foo"), self._mk("bar", kind="detector")]
        uncovered = check_preregs._find_uncovered(mechs, "")
        assert len(uncovered) == 2


# ---------------------------------------------------------------------------
# End-to-end: message formatting
# ---------------------------------------------------------------------------


class TestFormatBlockMessage:
    def test_mentions_count_and_name(self) -> None:
        mech = check_preregs.NewMechanism(
            kind="slice", name="foo", line="def run_foo_slice():", path="x.py"
        )
        msg = check_preregs._format_block_message([mech])
        assert "BLOCKED" in msg
        assert "foo" in msg
        assert "divineos prereg file" in msg
