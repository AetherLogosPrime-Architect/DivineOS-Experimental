"""The state block before an edit speaks when it changed and not when it did not.

Dad's token-waste order, 2026-10-10: the same corrections-and-bypass block rode
before every edit, byte-identical, about ten times an hour. These blocks are
data, so unchanged data stays silent. Both directions are pinned: the second
identical run is quiet, and a run after the block changed speaks again, because
a silence that also hid something new would be worse than the waste.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "state-gravity-surface.sh"
BASH = shutil.which("bash")

pytestmark = [
    pytest.mark.skipif(not HOOK.exists(), reason="hook absent from this checkout"),
    pytest.mark.skipif(BASH is None, reason="no working bash on this platform"),
]

PAYLOAD = json.dumps(
    {
        "tool_name": "Edit",
        "tool_input": {"file_path": (REPO_ROOT / "src" / "divineos" / "core" / "x.py").as_posix()},
    }
)


@pytest.fixture(autouse=True)
def _one_block_to_show():
    """The suite runs in an empty private home, where no block has anything to
    say and the hook is silent for the wrong reason. Seed one bypass event so
    the silence this file pins is the dedup's and not an empty store's."""
    from divineos.core.bypass_telemetry import record_bypass

    record_bypass("test-gate", "DIVINEOS_TEST_STATE_BLOCK", reason="seed for the quiet-block test")


def _run(dedup_dir: str) -> str:
    env = dict(os.environ)
    env["DIVINEOS_CONTEXT_DEDUP_DIR"] = dedup_dir
    done = subprocess.run(
        [BASH, str(HOOK)],
        input=PAYLOAD,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=180,
        env=env,
    )
    return done.stdout.strip()


def test_the_second_identical_block_is_silent_and_the_translate_note_is_gone():
    with tempfile.TemporaryDirectory(prefix="dedup-") as d:
        first = _run(d)
        if not first:
            pytest.skip("no state blocks to show on this checkout, so nothing to repeat")
        assert "MID-TURN TRANSLATE" not in first, "the Stop floor already locks this"
        second = _run(d)
        # Something must survive suppression (test_hook_dedup_contract.py): the
        # standing counts. But it is a small fraction of the full block.
        assert second, "nothing survived the suppression, which the dedup contract forbids"
        assert len(second) * 3 < len(first), "an unchanged block spoke in full: the waste is back"


def test_a_changed_block_speaks_again():
    with tempfile.TemporaryDirectory(prefix="dedup-") as d:
        first = _run(d)
        if not first:
            pytest.skip("no state blocks to show on this checkout, so nothing to repeat")
        state = Path(d) / "session_state.json"
        data = json.loads(state.read_text(encoding="utf-8"))
        data["state_gravity_blocks"]["hash"] = "stale-so-the-content-differs"
        state.write_text(json.dumps(data), encoding="utf-8")
        assert _run(d) != "", "a block that changed stayed silent"
