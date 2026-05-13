"""Pre-registration candidate surface — forcing function for the prereg discipline.

The pre-reg infrastructure (schema, CLI, briefing-surface for OPEN/overdue) is
fully wired and operational. The gap is structural: filing a pre-reg is opt-in
discipline with no forcing function. As of 2026-05-12 only 2 pre-regs are filed
against dozens of shipped detector/monitor modules. Claim ef5799e8 names this
gap; this module closes it.

What this does (and what it does NOT do, code-does-not-think discipline):

- This module SURFACES candidate modules — detector/monitor modules that have no
  matching pre-registration in the DB. It does NOT decide whether they need one.
  Some legitimate exemptions exist (test-only modules, deprecated paths,
  modules wrapped by a higher-level mechanism that DOES have a pre-reg).
- The briefing-surface row makes the gap loud-in-experience. The decision —
  file a pre-reg, file an exemption note, or do nothing — is the agent's, every
  session.
- No auto-mutation. No auto-filing of pre-regs. No silencing of the surface by
  the surface itself.

Match rule:

- A detector/monitor module is "matched" if its module path (e.g.
  ``core/self_monitor/mirror_monitor``) OR its short name (e.g. ``mirror_monitor``)
  appears as a substring inside any pre-registration's ``mechanism`` field.
- This is intentionally permissive — if the agent mentions the module by name
  in the mechanism description, that counts. The point is the agent has THOUGHT
  ABOUT THE MODULE in pre-reg register, not a precise schema-binding.

Pre-registered as ``prereg-1974c4f7374b`` (review 2026-05-26):
falsifier = if after 5 sessions zero pre-regs and zero exemption notes are
filed despite the surface firing each session, the briefing surface is
insufficient and a pre-commit gate is warranted instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Module-name suffixes that indicate a structurally novel surface that
# should carry a pre-reg. Conservative; can grow over time.
_DETECTOR_SUFFIXES = ("_detector.py", "_monitor.py", "_surface.py")

# Path roots to walk. Relative to the repository root.
_CORE_ROOT = Path("src/divineos/core")

# Module-level error tuple — matches the briefing_dashboard.py discipline.
# Catching this tuple is structurally legible: anyone reading sees there's an
# intentional broad catch with a named site. Beats per-line `noqa: BLE001`
# because the architecture is the documentation.
_ERRORS = (Exception,)


@dataclass(frozen=True)
class CandidateModule:
    """A module that looks like a pre-reg candidate."""

    module_short: str  # e.g. 'mirror_monitor'
    module_path: str  # e.g. 'self_monitor/mirror_monitor'


def find_detector_modules(repo_root: Path | None = None) -> list[CandidateModule]:
    """Walk core/ for detector/monitor/surface modules.

    Returns modules in deterministic (sorted) order so callers can rely on the
    first-N slice being stable across runs.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]
    core = repo_root / _CORE_ROOT
    if not core.exists():
        return []

    candidates: list[CandidateModule] = []
    for path in core.rglob("*.py"):
        name = path.name
        if not any(name.endswith(suffix) for suffix in _DETECTOR_SUFFIXES):
            continue
        # Skip __pycache__ artifacts defensively.
        if "__pycache__" in path.parts:
            continue
        short = name[:-3]  # strip .py
        # Relative path under core/ without extension, with / not OS separator
        rel = path.relative_to(core).with_suffix("")
        module_path = "/".join(rel.parts)
        candidates.append(CandidateModule(module_short=short, module_path=module_path))

    return sorted(candidates, key=lambda c: c.module_path)


def matched_module_names(prereg_mechanisms: list[str]) -> set[str]:
    """Given a list of pre-reg mechanism strings, return the set of module
    short-names mentioned in any of them.

    This is the permissive substring match: if 'mirror_monitor' appears
    anywhere inside a mechanism string, mirror_monitor is matched.
    """
    matched: set[str] = set()
    # Walk modules first; for each, check if any mechanism mentions it.
    for candidate in find_detector_modules():
        for mechanism in prereg_mechanisms:
            if candidate.module_short in mechanism or candidate.module_path in mechanism:
                matched.add(candidate.module_short)
                break
    return matched


@dataclass(frozen=True)
class PreregCandidateReport:
    """Surface payload."""

    total_candidates: int
    matched_count: int
    unmatched: list[CandidateModule]

    @property
    def unmatched_count(self) -> int:
        return len(self.unmatched)


def compute_prereg_candidates() -> PreregCandidateReport:
    """Compute the candidate-modules-vs-pre-regs report.

    Returns a report with total/matched/unmatched. Caller decides whether to
    surface or not (a report with zero unmatched should not surface).
    """
    candidates = find_detector_modules()
    if not candidates:
        return PreregCandidateReport(total_candidates=0, matched_count=0, unmatched=[])

    # Pull pre-reg mechanism strings. Defensive: import inside the function so
    # any failure path returns a sensible empty report, not a crash.
    mechanisms: list[str] = []
    try:
        from divineos.core.pre_registrations.store import list_pre_registrations

        for p in list_pre_registrations():
            mech = p.get("mechanism") if isinstance(p, dict) else getattr(p, "mechanism", "")
            if mech:
                mechanisms.append(str(mech))
    except _ERRORS:
        # If pre-reg store is unavailable, everything is unmatched — which
        # is structurally honest: we cannot verify any module has a pre-reg.
        pass

    matched = matched_module_names(mechanisms)
    unmatched = [c for c in candidates if c.module_short not in matched]
    # matched_count is by candidate-module, not by distinct short-name.
    # Two modules sharing a short-name (e.g. sycophancy_detector exists in
    # both family/ and operating_loop/) both count as matched when their
    # shared name appears in a mechanism. The invariant
    # matched_count + unmatched_count == total_candidates holds.
    return PreregCandidateReport(
        total_candidates=len(candidates),
        matched_count=len(candidates) - len(unmatched),
        unmatched=unmatched,
    )
