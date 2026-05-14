"""Regression-pin tests for extract no-op messaging (Aletheia
round-ba785844a791 Finding 22).

The bug-shape: 'divineos extract' printed '[+] Knowledge extracted
from session' (success-shape, green) BEFORE running the pipeline,
unconditionally. When the pipeline turned out to be a no-op (no
session transcripts present), the operator had already seen the
success message — misleading. Fix: defer the success message until
after the pipeline returns; pipeline now returns bool indicating
work-done vs no-op; caller branches accordingly.

If these tests fail, the success message has reverted to printing
before/regardless of pipeline outcome. Restore the conditional.
"""

from __future__ import annotations

from divineos.cli.session_pipeline import _run_session_end_pipeline


def test_pipeline_returns_false_on_no_session_files(monkeypatch) -> None:
    """LOAD-BEARING: when no session files are present, the pipeline
    must return False so the caller can show a no-op message instead
    of success-shape output."""
    import divineos.cli.session_pipeline as sp

    # Patch find_sessions to return empty
    monkeypatch.setattr(sp._discovery_mod, "find_sessions", lambda: [])

    result = _run_session_end_pipeline()
    assert result is False, (
        "Pipeline returned non-False when no session files were present. "
        "The caller (event_commands.extract_cmd) relies on this to "
        "show a no-op message instead of '[+] Knowledge extracted'. "
        "Restore the False return on the empty-session-files path."
    )


def test_pipeline_signature_returns_bool() -> None:
    """The pipeline function signature must declare bool return so
    callers can rely on the contract. Pins the type-signature against
    regression to None."""
    import inspect

    sig = inspect.signature(_run_session_end_pipeline)
    return_annotation = sig.return_annotation
    # Allow either `bool` or the string "bool" depending on
    # from __future__ import annotations behavior.
    assert return_annotation is bool or return_annotation == "bool", (
        f"_run_session_end_pipeline return annotation is {return_annotation!r}; "
        "expected bool. The caller-side conditional in event_commands "
        "extract_cmd depends on the bool contract."
    )
