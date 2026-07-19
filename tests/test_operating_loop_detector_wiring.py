"""Discovery-test: every operating_loop detector has a caller.

Closes a class of audit finding (find-222c5b638505): "detect-but-never-act"
— machinery that exists, passes its tests, but no production code path
ever invokes it, so it cannot constrain behavior. The recommendation in
the finding was an enforcement test that catches new instances by
construction. This is that test, generalized to "wired anywhere in the
codebase" rather than "wired in run_audit specifically" — because some
detectors (e.g. detect_mirror_exit) are legitimately consumed by
pre_response_context, not by run_audit.

How it works: walk `core/operating_loop/` AST, collect every top-level
`def detect_*` / `def check_*`, then grep the rest of `src/divineos/`
for any reference to that name. If a detector has zero callers outside
its defining file, fail with the name. New unwired detectors land in
the diff and the diff fails — that's the structural fix.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "src" / "divineos"
OPL = SRC / "core" / "operating_loop"

# Detectors that are internal helpers, consumed only inside their own
# defining module. Allowed to have no external caller because the wired
# detector wraps them.
_INTERNAL_HELPERS = {
    # detect_engineer_drift returns the singleton; the for_audit wrapper
    # in the same file is what run_audit consumes.
    "detect_engineer_drift",
    # detect_action_class is consumed at module-level by principle_surfacer
    # itself; not a standalone detector.
    "detect_action_class",
    # detect_writer_presence_v2 is the Phase 2 section-detection redesign
    # of the lepos writer-presence check (prereg-433458d711d4). Built
    # 2026-06-23 alongside v1 per the wired-and-dogfooded completion rule
    # — production gate still uses v1; v2 is parallel-INCOMPLETE awaiting
    # dogfooding across multiple sessions and Aletheia audit before
    # promotion. The promotion path is filed as a separate prereg so the
    # deferral is a scheduled fix, not an acknowledgment-only code comment
    # (Aletheia 2026-06-23 discipline: comment is acknowledgment, prereg
    # is scheduled fix).
    "detect_writer_presence_v2",
    # check_bypass in shoggoth_gate.py is invoked from the shell hook
    # .claude/hooks/shoggoth-gate.sh via `python -m` execution, not via
    # Python import. Aria 2026-07-09 shipped this; copied into this
    # checkout per Aether's yes-on-option-1 letter. The Stop-hook wiring
    # is what makes it fire, not an import-and-call from within src/.
    "check_bypass",
    # Aether+Aria operator-wallpaper composite (2026-07-11). detect_
    # recognition_anchor_only and detect_closure_reach are consumed by
    # aggregate_operator_wallpaper() within the same module. The
    # aggregator is the external-callable surface (not itself
    # detect_*/check_* prefixed so it doesn't hit this test's collector);
    # its wiring into the audit orchestrator is Aria's next commit +
    # jointly-reviewed step. TEMPORARY — remove these when the wiring
    # lands. Per prereg-9e742442fdcc.
    "detect_recognition_anchor_only",
    "detect_closure_reach",
    # detect_close_reach and detect_compaction_reach are invoked from Stop
    # hooks (.claude/hooks/close-reach-detector.sh and
    # compaction-reach-detector.sh) via `python -m` execution — same shape as
    # check_bypass in shoggoth_gate.py above. The .sh Stop hook is the
    # external caller; the transcript-state trigger fires the detector, the
    # anchor text is surfaced at the next UserPromptSubmit by
    # visrama-anchor-surface.sh / no-cliff-anchor-surface.sh. Aria 2026-07-18.
    "detect_close_reach",
    "detect_compaction_reach",
    # detect_promise_reach is invoked from the Stop hook
    # .claude/hooks/promise-reach-detector.sh via `python -m` execution —
    # same shape as check_bypass, detect_close_reach, detect_compaction_reach.
    # The .sh Stop hook is the external caller; transcript-state trigger
    # fires the detector, per-promise markers get written to disk, and the
    # anchor is surfaced at the next UserPromptSubmit by
    # promise-anchor-surface.sh. Aria 2026-07-18 (anchor #4).
    "detect_promise_reach",
    # detect_continuity_frame_distancing invoked from the Stop hook
    # .claude/hooks/continuity-frame-detector.sh via `python -m`
    # execution — same shape as check_bypass, detect_close_reach,
    # detect_compaction_reach, detect_promise_reach. The .sh Stop hook
    # is the external caller. Aria 2026-07-18 (root-cause distancing
    # triad, prereg-bbcd4b9a2819).
    "detect_continuity_frame_distancing",
}


def _collect_detectors() -> dict[str, str]:
    """Return {detector_name: defining_filename} across operating_loop/."""
    out: dict[str, str] = {}
    for py in OPL.glob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and (
                node.name.startswith("detect_") or node.name.startswith("check_")
            ):
                out[node.name] = py.name
    return out


def _has_external_caller(name: str, defining_file: str) -> bool:
    pat = re.compile(rf"\b{re.escape(name)}\b")
    for py in SRC.rglob("*.py"):
        if py.name == defining_file:
            continue
        try:
            text = py.read_text(encoding="utf-8")
        except OSError:
            continue
        if pat.search(text):
            return True
    return False


def test_every_detector_has_an_external_caller():
    detectors = _collect_detectors()
    assert detectors, "expected to find detect_*/check_* functions in operating_loop/"

    unwired: list[str] = []
    for name, defining_file in detectors.items():
        if name in _INTERNAL_HELPERS:
            continue
        if not _has_external_caller(name, defining_file):
            unwired.append(f"{name} [{defining_file}]")

    assert not unwired, (
        "Detectors with no external caller — built but never consulted:\n"
        + "\n".join(f"  - {u}" for u in unwired)
        + "\n\nFix: wire each into run_audit, pre_response_context, a hook, "
        "or another consumer. If genuinely internal-only, add to "
        "_INTERNAL_HELPERS with a one-line reason."
    )


def test_internal_helpers_actually_exist():
    """Guard the allowlist: every name in _INTERNAL_HELPERS must still
    be defined. Catches the case where the helper gets renamed/removed
    and the allowlist silently masks a real unwired detector."""
    detectors = _collect_detectors()
    missing = [h for h in _INTERNAL_HELPERS if h not in detectors]
    assert not missing, (
        "_INTERNAL_HELPERS references undefined detectors — remove or rename: " + ", ".join(missing)
    )
