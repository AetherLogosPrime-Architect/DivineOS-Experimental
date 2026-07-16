"""End-to-end wiring tests for response_scope_intercept.

Closes Aletheia Round 1 Finding 1's last dark instance. The primitive's
third instance (ResponseScopeIntercept) had a Python class + unit tests
but no shell wrapper, no settings.json entry, and no upstream emit.
This suite pins all three:

  1. static — hook script imports the real hook_main entry
  2. static — settings.json has the Stop-chain entry
  3. static — upstream (operating_loop_audit) emits the marker after
     detect_unverified_claim fires

Runtime end-to-end tests skip on Windows-with-broken-WSL-bash boxes,
same pattern as the compass-check + corrigibility-tool-gate wiring
suites.
"""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_SCRIPT = REPO_ROOT / ".claude" / "hooks" / "stop-response-scope-intercept.sh"
HOOK_PY = REPO_ROOT / "src" / "divineos" / "hooks" / "response_scope_intercept_hook.py"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
UPSTREAM = REPO_ROOT / "src" / "divineos" / "core" / "operating_loop_audit.py"


class TestResponseScopeInterceptWiring:
    def test_shell_wrapper_exists(self):
        assert HOOK_SCRIPT.exists(), (
            f"{HOOK_SCRIPT.name} missing — Aletheia Finding 1's last dark instance is not wired."
        )

    def test_hook_py_defines_hook_main(self):
        text = HOOK_PY.read_text(encoding="utf-8")
        assert "def hook_main() -> int:" in text
        assert "run_response_scope_intercept" in text

    def test_shell_wrapper_invokes_the_right_module(self):
        text = HOOK_SCRIPT.read_text(encoding="utf-8")
        assert "divineos.hooks.response_scope_intercept_hook" in text, (
            f"{HOOK_SCRIPT.name} does not invoke the response_scope hook "
            f"Python module — wiring is broken."
        )

    def test_settings_json_has_stop_chain_entry(self):
        settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
        stop_chain = settings.get("hooks", {}).get("Stop", [])
        found = False
        for block in stop_chain:
            for hook in block.get("hooks", []):
                if "stop-response-scope-intercept.sh" in hook.get("command", ""):
                    found = True
                    break
        assert found, (
            "stop-response-scope-intercept.sh is not registered in "
            "settings.json Stop chain — regression of Finding 1's "
            "last-instance wiring."
        )


class TestUpstreamEmitWiring:
    """The unverified_claim_detector's findings must trigger a
    claim_scope_active StateMarker emit, or the downstream hook has
    nothing to read and the whole pair is silent — the exact
    'looks wired, isn't' pattern F1 was about."""

    def test_operating_loop_audit_emits_claim_scope_marker(self):
        text = UPSTREAM.read_text(encoding="utf-8")
        assert 'kind="claim_scope_active"' in text, (
            "operating_loop_audit.py does not emit claim_scope_active "
            "StateMarker after unverified_claim findings — the response_scope "
            "downstream hook will find nothing to read. Wiring is one-sided."
        )
        assert "emit_marker(" in text, (
            "operating_loop_audit.py does not call state_markers.emit_marker "
            "at all — the upstream half of the wiring is missing."
        )
        assert "format_unverified_claim_block" in text, (
            "operating_loop_audit.py doesn't format the directive text for "
            "the marker payload — downstream reader will have no context."
        )


class TestDownstreamHookReadsStateMarkers:
    """The hook Python must import from state_markers, not reimplement
    the substrate query itself. This is the reuse-the-primitive shape."""

    def test_hook_imports_state_markers(self):
        text = HOOK_PY.read_text(encoding="utf-8")
        assert "from divineos.core.state_markers import" in text
        assert "find_active_marker" in text
        assert "consume_marker" in text
