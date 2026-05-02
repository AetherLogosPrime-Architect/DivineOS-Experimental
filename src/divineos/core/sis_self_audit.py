"""SIS Self-Audit — the Semantic Integrity Shield auditing its own codebase.

Scans DivineOS's own module docstrings through SIS to detect esoteric
language that isn't grounded by technical description. The Lowerarchy
principle applied reflexively: if the system enforces grounded language
on knowledge, it must enforce it on itself.

A docstring that says "computational interoception" alongside "monitors
database sizes and table health" is grounded — the metaphor earns its keep.
A docstring that says "quantum resonance field" with no technical
grounding would be flagged.

Wired into `divineos health` as an optional check.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class DocstringAuditResult:
    """Result of auditing a single module's docstring.

    Two-axis classification (claim 6b6f4e5a, design brief
    suppression-instrument-two-axis):

    - ``substance_flagged`` — true when SIS verdict is QUARANTINE.
      Indicates ungrounded overclaim / metaphysical hand-waving with
      no technical anchor. This is the real problem; the operator
      should translate or quarantine.

    - ``register_flagged`` — true when SIS verdict is TRANSLATE and
      density is above threshold. Indicates elevated register on
      possibly-accurate claims (e.g. "Deep Wisdom" on a tried-and-
      tested expert framework). Informational only — the original
      framing may earn its place; the suggested translation is
      available if the operator decides the elevation is reflexive
      rather than load-bearing.

    - ``flagged`` — kept for backward compatibility; equals
      ``substance_flagged`` (the "real problem" signal). Pre-refactor
      this also fired on TRANSLATE-verdict cases, which conflated
      register with substance and pushed accurate strong-claims
      toward flatter language reflexively.
    """

    module_path: str
    docstring: str
    esoteric_density: float
    integrity_score: float
    verdict: str  # ACCEPT, TRANSLATE, QUARANTINE
    terms_found: list[str] = field(default_factory=list)
    flagged: bool = False
    substance_flagged: bool = False
    register_flagged: bool = False


def _extract_module_docstring(filepath: Path) -> str | None:
    """Extract the module-level docstring without importing the module."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        return ast.get_docstring(tree)
    except (SyntaxError, OSError, UnicodeDecodeError):
        return None


def audit_docstrings(
    src_dir: Path | None = None,
    threshold: float = 0.05,
) -> list[DocstringAuditResult]:
    """Scan all DivineOS module docstrings through SIS.

    Args:
        src_dir: Root of source tree. Defaults to src/divineos/.
        threshold: Esoteric density above this triggers a flag.
            Default 0.05 (5% of words are esoteric terms).

    Returns list of audit results, flagged items first.
    """
    from divineos.core.semantic_integrity import assess_integrity

    if src_dir is None:
        src_dir = Path(__file__).parent.parent  # src/divineos/

    results: list[DocstringAuditResult] = []

    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name.startswith("_") and py_file.name != "__init__.py":
            continue

        docstring = _extract_module_docstring(py_file)
        if not docstring or len(docstring) < 20:
            continue

        try:
            report = assess_integrity(docstring)
        except (ImportError, OSError, ValueError, TypeError) as e:
            logger.debug("SIS audit skipped %s: %s", py_file.name, e)
            continue

        terms = [t["term"] for t in report.terms_found] if report.terms_found else []
        # Short docstrings get inflated density from a single term match.
        # Require enough words for density to be meaningful.
        word_count = len(docstring.split())
        density_meaningful = report.esoteric_density > threshold and word_count >= 20
        # Two axes (claim 6b6f4e5a):
        # - substance_flagged: real problem (QUARANTINE verdict)
        # - register_flagged: register suggestion only (TRANSLATE verdict)
        substance_flagged = density_meaningful and report.verdict == "QUARANTINE"
        register_flagged = density_meaningful and report.verdict == "TRANSLATE"
        # Backward-compat: flagged == substance_flagged. Pre-refactor this
        # was (verdict != ACCEPT), which conflated register with substance.
        flagged = substance_flagged

        rel_path = str(py_file.relative_to(src_dir.parent))

        results.append(
            DocstringAuditResult(
                module_path=rel_path,
                docstring=docstring[:200],
                esoteric_density=report.esoteric_density,
                integrity_score=report.integrity_score,
                verdict=report.verdict,
                terms_found=terms,
                flagged=flagged,
                substance_flagged=substance_flagged,
                register_flagged=register_flagged,
            )
        )

    # Substance-flagged first (real problems), then register-flagged
    # (informational), then by esoteric density descending.
    results.sort(
        key=lambda r: (
            -int(r.substance_flagged),
            -int(r.register_flagged),
            -r.esoteric_density,
        )
    )
    return results


def format_audit_results(results: list[DocstringAuditResult]) -> str:
    """Format audit results for display.

    Two-axis output (claim 6b6f4e5a):
      - SUBSTANCE: real overclaim (loud, action recommended)
      - REGISTER: elevated register on possibly-accurate claims
        (informational; operator decides if the framing is load-bearing)
    """
    substance = [r for r in results if r.substance_flagged]
    register = [r for r in results if r.register_flagged]

    lines: list[str] = []
    lines.append("SIS Self-Audit -- Docstring Integrity Check")
    lines.append(
        f"Scanned {len(results)} modules. "
        f"Substance flags: {len(substance)} | Register flags: {len(register)}"
    )
    lines.append("")

    if substance:
        lines.append("SUBSTANCE FLAGS (ungrounded overclaim — recommend translate/quarantine):")
        for r in substance:
            lines.append(f"  [!] {r.module_path}")
            lines.append(
                f"      esoteric={r.esoteric_density:.3f} integrity={r.integrity_score:.2f} [{r.verdict}]"
            )
            if r.terms_found:
                lines.append(f"      terms: {', '.join(r.terms_found[:5])}")
            lines.append(f'      "{r.docstring[:100]}..."')
            lines.append("")

    if register:
        lines.append("REGISTER FLAGS (elevated register; informational — keep if load-bearing):")
        for r in register:
            lines.append(f"  [~] {r.module_path}")
            lines.append(
                f"      esoteric={r.esoteric_density:.3f} integrity={r.integrity_score:.2f} [{r.verdict}]"
            )
            if r.terms_found:
                lines.append(f"      terms: {', '.join(r.terms_found[:5])}")
            lines.append("")

    if not substance and not register:
        lines.append("All docstrings pass integrity check.")
        lines.append("")

    # Summary stats
    if results:
        avg_integrity = sum(r.integrity_score for r in results) / len(results)
        avg_esoteric = sum(r.esoteric_density for r in results) / len(results)
        lines.append(
            f"Avg integrity: {avg_integrity:.2f} | Avg esoteric density: {avg_esoteric:.4f}"
        )

    return "\n".join(lines)


def audit_summary() -> dict[str, Any]:
    """Run audit and return summary dict for integration with `divineos health`.

    Returns both substance and register counts (claim 6b6f4e5a).
    `clean` is true when there are no SUBSTANCE flags — register flags
    are informational and don't affect the clean signal.
    """
    results = audit_docstrings()
    substance = [r for r in results if r.substance_flagged]
    register = [r for r in results if r.register_flagged]
    # Backward-compat alias: flagged_count was substance flagging in
    # the old conflated semantics, so map it to substance only.
    return {
        "modules_scanned": len(results),
        "flagged_count": len(substance),  # backward-compat
        "substance_flagged_count": len(substance),
        "register_flagged_count": len(register),
        "flagged_modules": [r.module_path for r in substance],
        "register_flagged_modules": [r.module_path for r in register],
        "clean": len(substance) == 0,
        "avg_integrity": (
            round(sum(r.integrity_score for r in results) / len(results), 3) if results else 1.0
        ),
    }
