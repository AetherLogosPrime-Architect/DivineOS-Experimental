"""The auto-cycle's printout says WHY a step failed, not only its exception class.

2026-11-05, Dad: "stop avoiding the squeaky floorboards". The save routine's commit step refused three
mornings running and printed only `error: RuntimeError`; the reason (a staged index left in the tree) was in
the step's own record the whole time and was never shown, so I shrugged at it each morning. This pins that the
reason is printed, and that a failure with no recorded reason still prints the class.
"""

from __future__ import annotations

from types import SimpleNamespace

from click.testing import CliRunner

from divineos.cli import auto_cycle_commands as cmds


def _step(succeeded, error_class=None, output_tail=""):
    return SimpleNamespace(
        succeeded=succeeded,
        duration_sec=0.1,
        tokens_used_est=1000,
        error_class=error_class,
        output_tail=output_tail,
    )


def _fire(monkeypatch, tmp_path, steps):
    monkeypatch.setattr(cmds, "_guess_context_pct", lambda: 0.9)
    result = SimpleNamespace(cycle_id="auto-cycle-test", steps=steps)
    monkeypatch.setattr(cmds.auto_cycle, "run_phase1", lambda context_pct, dry_run: result)
    monkeypatch.setattr(
        cmds.auto_cycle, "write_handshake_marker", lambda r: tmp_path / "marker.json"
    )
    monkeypatch.setattr(cmds.auto_cycle, "reset_defer_state", lambda: None)
    return CliRunner().invoke(cmds.fire_cmd, ["--force"]).output


def test_a_failed_step_prints_the_reason_it_recorded(monkeypatch, tmp_path):
    why = "[commit] RuntimeError: checkpoint did not commit: skipped auto-commit — staged index"
    out = _fire(monkeypatch, tmp_path, {"commit": _step(False, "RuntimeError", why)})
    assert "staged index" in out
    assert "[FAIL] commit" in out


def test_a_failed_step_with_no_recorded_reason_still_prints_the_class(monkeypatch, tmp_path):
    out = _fire(monkeypatch, tmp_path, {"commit": _step(False, "RuntimeError", "")})
    assert "error: RuntimeError" in out


def test_a_step_that_succeeded_prints_no_error_line(monkeypatch, tmp_path):
    out = _fire(monkeypatch, tmp_path, {"archive": _step(True)})
    assert "error:" not in out
