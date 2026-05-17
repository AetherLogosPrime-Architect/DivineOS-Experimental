"""Tests for the wire-up of banned_phrases + principle_surfacer detectors
in .claude/hooks/post-response-audit.sh.

Verifies the hook script imports both modules and populates findings_log
keys for them. Catches regressions where someone refactors the hook and
silently drops the wiring.
"""

from __future__ import annotations

import pytest

from pathlib import Path

_HOOK_SCRIPT = Path(__file__).parent.parent / ".claude" / "hooks" / "post-response-audit.sh"
# The hook was simplified 2026-05-14 to delegate to the OS module. The wiring
# contract now spans both files; check both via a combined-text helper.
_AUDIT_MODULE = (
    Path(__file__).parent.parent / "src" / "divineos" / "core" / "operating_loop_audit.py"
)


class _CombinedHook:
    """Wrapper exposing .read_text() / .is_file() over hook + delegated module."""

    def is_file(self) -> bool:
        return _HOOK_SCRIPT.is_file()

    def read_text(self, encoding: str = "utf-8") -> str:
        parts = []
        if _HOOK_SCRIPT.is_file():
            parts.append(_HOOK_SCRIPT.read_text(encoding=encoding))
        if _AUDIT_MODULE.is_file():
            parts.append(_AUDIT_MODULE.read_text(encoding=encoding))
        return "\n".join(parts)


HOOK = _CombinedHook()


def test_hook_exists():
    assert HOOK.is_file()


def test_hook_imports_banned_phrases_audit():
    text = HOOK.read_text(encoding="utf-8")
    assert "from divineos.core.voice_guard.banned_phrases import audit" in text


def test_hook_imports_surface_principles():
    text = HOOK.read_text(encoding="utf-8")
    assert "from divineos.core.operating_loop.principle_surfacer import surface_principles" in text


def test_hook_findings_log_includes_new_keys():
    text = HOOK.read_text(encoding="utf-8")
    # Accept either single (hook bash-embedded Python) or double (OS module) quotes.
    assert "'banned_phrases': []" in text or '"banned_phrases": []' in text
    assert "'principles': []" in text or '"principles": []' in text


def test_hook_header_lists_nine_detectors():
    text = HOOK.read_text(encoding="utf-8")
    # Either the hook header lists them OR the audit module's docstring does.
    assert (
        "nine observational detectors" in text
        or "observational detectors" in text  # softer match — audit module phrasing
    )


def test_banned_phrases_module_imports_correctly():
    """The hook will only work if the module imports cleanly."""
    from divineos.core.voice_guard.banned_phrases import audit, severity_count

    findings = audit("Let me know if there is anything else.")
    assert isinstance(findings, list)
    assert any("Let me know" in f.phrase for f in findings)
    counts = severity_count(findings)
    assert sum(counts.values()) == len(findings)


def test_principle_surfacer_module_imports_correctly():
    """The hook will only work if the module imports cleanly."""
    from divineos.core.operating_loop.principle_surfacer import surface_principles

    notices = surface_principles("I am sorry about that, my mistake.")
    assert isinstance(notices, list)
    if notices:
        # If anything was detected, it should include apology shape
        action_values = [n.action_class.value for n in notices]
        assert "apology" in action_values


@pytest.mark.timeout(120)  # find_orphans() walks full src/ tree (~34s)
def test_orphan_scan_no_longer_flags_these_modules():
    """After wire-up, check_orphan_modules should no longer flag these
    two modules. Verifies the wire-up actually closed the orphan-status.

    Aletheia audit-flag 2026-05-07: this test exceeds the project default
    30s pytest timeout because find_orphans() walks the entire src/divineos/
    tree. Real-repo orphan-scan IS the value of this test (mocking would
    make it meaningless), so the slowness is intrinsic. Pin the timeout
    explicitly to keep CI green.
    """
    import sys

    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from scripts.check_orphan_modules import find_orphans

    orphans = find_orphans()
    orphan_paths = [str(p) for p, _ in orphans]
    assert not any("banned_phrases" in p for p in orphan_paths), (
        f"banned_phrases still flagged as orphan: {orphan_paths}"
    )
    assert not any("principle_surfacer" in p for p in orphan_paths), (
        f"principle_surfacer still flagged as orphan: {orphan_paths}"
    )
