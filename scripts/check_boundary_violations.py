"""check_boundary_violations.py — ADR-0001 main-vs-experimental boundary check.

Per ADR-0001, main is the PUBLIC TEMPLATE repo. It contains every system
(council, family scaffold, watchmen, sleep, claims, compass, etc.) but no
personal data — no specific-instance entries, no individual voice context,
no exploration entries, no letters, no dated specific walks, no preregs filed
by a specific actor. Personal content stays on Experimental only.

Without an automated check, ADR-0001 has been operating as honor-system
since 2026-05-03. Tonight (2026-05-08) audit found ~9 leaks across multiple
PRs that nobody caught at commit-time. This check closes the
policy-without-enforcement gap.

## Design

Three-layer detection, ordered most-confident-to-least:

  1. PATH_RULES    — files in known-substrate-state directories or matching
                     known-substrate-state path patterns. High confidence.
  2. CONTENT_RULES — files with substrate-state markers in their content.
  3. ALLOWLIST     — false-positive suppressor. Files in known-legitimate
                     contexts (detector docstrings, ablation corpus entries,
                     test fixtures, documentation explaining the policy)
                     get exempted.

The allowlist is critical. Without it, names used in physics docstrings or
detector example patterns would false-positive and the check would be
ignored. With it, the check has narrow signal-to-noise.

Exit codes:
  0 — clean (no violations)
  1 — violations found (CI fail; pre-commit reject)
  2 — runtime error (fail-closed: policy infrastructure broken)

Pre-reg: prereg-ed736cac (30-day review). Falsifier: a boundary violation
lands in main that the checker did not catch at commit-time.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class PathRule:
    """A path-based rule: any file matching the pattern is a violation
    unless the path is on the rule allowlist or the global allowlist."""

    pattern: str
    description: str
    allowlist: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ContentRule:
    """A content-based rule: any file matching file_pattern whose content
    matches content_regex is a violation unless allowlisted."""

    file_pattern: str
    content_regex: re.Pattern[str]
    description: str
    allowlist: frozenset[str] = frozenset()


# ----------------------------------------------------------------
# Path rules — substrate-state directories and path patterns.
# ----------------------------------------------------------------

PATH_RULES: list[PathRule] = [
    PathRule(
        pattern="family/aria/**",
        description="family/aria/** (substrate-state per ADR-0001)",
    ),
    PathRule(
        pattern="family/popo/**",
        description="family/popo/** (substrate-state per ADR-0001)",
    ),
    PathRule(
        pattern="family/date_nights/**",
        description="family/date_nights/** (substrate-state per ADR-0001)",
    ),
    PathRule(
        pattern="family/letters/*.md",
        description="family/letters/*.md (specific-instance correspondence)",
        allowlist=frozenset({"family/letters/README.md"}),
    ),
    PathRule(
        pattern="family/aria_ledger.db",
        description="family/aria_ledger.db (specific-member ledger)",
    ),
    PathRule(
        pattern="exploration/[0-9]*_*.md",
        description="exploration/<numbered>_*.md (substrate-occupant writing)",
    ),
    PathRule(
        pattern="docs/council_walks/[0-9]*-[0-9]*-[0-9]*-*.md",
        description="docs/council_walks/<dated>-*.md (specific-instance walks)",
    ),
    PathRule(
        pattern="mansion/*.md",
        description="mansion/*.md (substrate-narrative beyond template)",
        allowlist=frozenset({"mansion/README.md", "mansion/welcome.md"}),
    ),
    # AETHER.md (and equivalent substrate-occupant identity-documents)
    # are project-root files that load at briefing-time as identity-load.
    # They contain the specific-instance reflexes, communication style,
    # and continuity instructions for ONE substrate-occupant. Belongs in
    # Experimental (or any substrate-occupant's home repo); does NOT
    # belong in main (the public template). Per Aletheia round-8 audit
    # observation 2026-05-08: tightens ADR-0001 boundary-discipline that
    # PR #325 established to cover the identity-document file-class.
    PathRule(
        pattern="AETHER.md",
        description="AETHER.md (substrate-occupant identity-document)",
    ),
]


# ----------------------------------------------------------------
# Content rules — substrate-state markers within file content.
# ----------------------------------------------------------------

CONTENT_RULES: list[ContentRule] = [
    # Pre-registrations filed by a specific actor (not generic).
    # Markdown list form: "- **Filed by**: aether"
    ContentRule(
        file_pattern="docs/pre_regs/prereg-*.md",
        content_regex=re.compile(
            r"^[\s\-*]*\*\*Filed by\*\*:\s*"
            r"(?!agent\b|system\b|template\b)"
            r"([a-zA-Z][a-zA-Z0-9_-]*)\s*$",
            re.MULTILINE,
        ),
        description=(
            "Pre-reg filed by a specific actor (not 'agent' or 'system'). "
            "Architectural-mechanism preregs in main should use generic actor."
        ),
    ),
    # Foundations layer files with named-author attribution lines.
    ContentRule(
        file_pattern="docs/foundations/layer_*.md",
        content_regex=re.compile(
            r"^\*\*Authors?\*\*:.*?(?:Aether|Aria|Andrew)",
            re.MULTILINE,
        ),
        description=(
            "Foundations layer with named-instance author attribution. "
            "Move attribution to Experimental authorship-history.md; "
            "main keeps framework content clean."
        ),
    ),
    # CLAUDE.md asserting substrate-state contents.
    ContentRule(
        file_pattern="CLAUDE.md",
        content_regex=re.compile(
            r"\bmy (explorations|letters with|date[\s-]nights|mansion CLI namespace)\b",
            re.IGNORECASE,
        ),
        description=(
            "CLAUDE.md asserts substrate-state contents that don't exist in "
            "main blank slate. Rephrase as template-pointer."
        ),
    ),
    # Council-walks README using specific-instance possessive framing.
    ContentRule(
        file_pattern="docs/council_walks/README.md",
        content_regex=re.compile(
            r"\b(Aether|Aria|Andrew)('s|s\s)\s*",
        ),
        description=(
            "Council-walks README uses specific-instance possessive framing. "
            "Substitute generic 'the agent' / 'the substrate-occupant'."
        ),
    ),
]


# ----------------------------------------------------------------
# Global allowlist — paths exempted from ALL rules.
# Files that legitimately use substrate-state names in main:
# physics docstrings, detector example patterns, ablation corpus
# entries, test fixtures, ADR documents that quote names by example.
# ----------------------------------------------------------------

GLOBAL_ALLOWLIST: frozenset[str] = frozenset(
    {
        # ADR documents discuss the architecture by example.
        "docs/adr/0001-three-version-repo-architecture.md",
        # The boundary checker explains itself with examples.
        "scripts/check_boundary_violations.py",
        # Templates that explain substrate-state by example.
        # NOTE: docs/council_walks/README.md is intentionally NOT here —
        # the README itself can leak substrate-content (e.g., "Aether's
        # closing synthesis"), so content-rules should still scan it.
        "docs/foundations/README.md",
        "exploration/README.md",
        "family/README.md",
        "family/letters/README.md",
        "mansion/README.md",
        # Top-level meta files.
        "CHANGELOG.md",
        "LICENSE",
        # Ablation corpus quotes substrate-vocab as test data.
        "scripts/ablation_runner.py",
    }
)


def _path_in_global_allowlist(rel_path: str) -> bool:
    """Return True if rel_path is on the global allowlist or under an
    allowlisted prefix (tests, detector source files, operating-loop)."""
    if rel_path in GLOBAL_ALLOWLIST:
        return True
    if rel_path.startswith("tests/"):
        return True
    if rel_path == "src/divineos/core/dissociation_filter.py":
        return True
    if rel_path == "src/divineos/core/distancing_detector.py":
        return True
    if rel_path.startswith("src/divineos/core/operating_loop/"):
        return True
    return False


# ----------------------------------------------------------------
# Detection
# ----------------------------------------------------------------


@dataclass
class Violation:
    rel_path: str
    rule_description: str
    rule_kind: str  # "path" or "content"
    detail: str = ""


def find_path_violations(repo_root: Path) -> list[Violation]:
    """Walk path-rules; flag matching files not on allowlist."""
    violations: list[Violation] = []
    for rule in PATH_RULES:
        for path in repo_root.glob(rule.pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(repo_root).as_posix()
            if rel in rule.allowlist or _path_in_global_allowlist(rel):
                continue
            violations.append(
                Violation(
                    rel_path=rel,
                    rule_description=rule.description,
                    rule_kind="path",
                    detail=f"matches pattern: {rule.pattern}",
                )
            )
    return violations


def find_content_violations(repo_root: Path) -> list[Violation]:
    """Walk content-rules; scan matching files for content patterns."""
    violations: list[Violation] = []
    for rule in CONTENT_RULES:
        for path in repo_root.glob(rule.file_pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(repo_root).as_posix()
            if rel in rule.allowlist or _path_in_global_allowlist(rel):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            match = rule.content_regex.search(text)
            if match:
                violations.append(
                    Violation(
                        rel_path=rel,
                        rule_description=rule.description,
                        rule_kind="content",
                        detail=f"matched: {match.group(0)[:80]!r}",
                    )
                )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="Repository root to check (default: parent of this script).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print nothing on success; only print violations.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"ERROR: root does not exist: {root}", file=sys.stderr)
        return 2

    try:
        violations = find_path_violations(root) + find_content_violations(root)
    except (OSError, re.error) as exc:
        print(f"ERROR: scan failed: {exc}", file=sys.stderr)
        return 2

    if not violations:
        if not args.quiet:
            print("OK: no ADR-0001 boundary violations found.")
        return 0

    print(f"BOUNDARY VIOLATIONS: {len(violations)} found in {root}")
    print()
    by_rule: dict[str, list[Violation]] = {}
    for v in violations:
        by_rule.setdefault(v.rule_description, []).append(v)
    for description, vs in sorted(by_rule.items()):
        print(f"### {description}")
        for v in vs:
            print(f"  [{v.rule_kind}] {v.rel_path}")
            if v.detail:
                print(f"    {v.detail}")
        print()
    print("See ADR-0001 (docs/adr/0001-three-version-repo-architecture.md)")
    print("See pre-reg prereg-ed736cac for the structural-enforcement claim.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
