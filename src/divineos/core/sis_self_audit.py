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


@dataclass
class DocstringAuditResult:
    """Result of auditing a single module's docstring."""

    module_path: str
    docstring: str
    esoteric_density: float
    integrity_score: float
    verdict: str  # ACCEPT, TRANSLATE, QUARANTINE
    terms_found: list[str] = field(default_factory=list)
    flagged: bool = False


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
        except Exception:  # noqa: BLE001
            continue

        terms = [t["term"] for t in report.terms_found] if report.terms_found else []
        flagged = report.esoteric_density > threshold and report.verdict != "ACCEPT"

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
            )
        )

    # Flagged items first, then by esoteric density descending
    results.sort(key=lambda r: (-int(r.flagged), -r.esoteric_density))
    return results


def format_audit_results(results: list[DocstringAuditResult]) -> str:
    """Format audit results for display."""
    flagged = [r for r in results if r.flagged]

    lines: list[str] = []
    lines.append("SIS Self-Audit -- Docstring Integrity Check")
    lines.append(f"Scanned {len(results)} modules, {len(flagged)} flagged")
    lines.append("")

    if flagged:
        lines.append("FLAGGED (esoteric language without sufficient grounding):")
        for r in flagged:
            lines.append(f"  [!] {r.module_path}")
            lines.append(
                f"      esoteric={r.esoteric_density:.3f} integrity={r.integrity_score:.2f} [{r.verdict}]"
            )
            if r.terms_found:
                lines.append(f"      terms: {', '.join(r.terms_found[:5])}")
            lines.append(f'      "{r.docstring[:100]}..."')
            lines.append("")
    else:
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
    """Run audit and return summary dict for integration with `divineos health`."""
    results = audit_docstrings()
    flagged = [r for r in results if r.flagged]

    return {
        "modules_scanned": len(results),
        "flagged_count": len(flagged),
        "flagged_modules": [r.module_path for r in flagged],
        "clean": len(flagged) == 0,
        "avg_integrity": (
            round(sum(r.integrity_score for r in results) / len(results), 3) if results else 1.0
        ),
    }
