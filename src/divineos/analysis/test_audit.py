"""Test quality audit — classify tests by what they actually verify.

Three categories matter:
1. Data: real DB vs synthetic/mock — does the test run against production-realistic conditions?
2. Assertion: behavior vs structure — does the test verify outcomes or just shapes?
3. Coverage: failure modes vs happy path — does the test exercise error paths?

Uses AST analysis to classify each test function. Approximate, not perfect.
But even a rough breakdown reveals blind spots.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AuditClassification:
    """Classification of a single test function."""

    file: str
    name: str
    data_type: str  # "real_db", "synthetic", "no_data"
    assertion_type: str  # "behavior", "structure", "mixed"
    coverage_type: str  # "failure_mode", "happy_path", "edge_case"


@dataclass
class AuditSummary:
    """Aggregate audit results."""

    total_tests: int = 0
    total_files: int = 0

    # Data classification
    real_db: int = 0
    synthetic: int = 0
    no_data: int = 0

    # Assertion classification
    behavior: int = 0
    structure: int = 0
    mixed: int = 0

    # Coverage classification
    failure_mode: int = 0
    happy_path: int = 0
    edge_case: int = 0

    # Inline schema problems
    inline_schemas: int = 0
    schema_files: list[str] = field(default_factory=list)

    tests: list[AuditClassification] = field(default_factory=list)


# -- Patterns for classification -----------------------------------------

_REAL_DB_PATTERNS = re.compile(
    r"init_db|init_knowledge_table|init_memory_tables|init_affect_log|"
    r"init_compass|init_edge_table|init_claim_tables|_get_connection|"
    r"get_connection|DIVINEOS_DB|sqlite3\.connect",
)

_MOCK_PATTERNS = re.compile(
    r"Mock\(|MagicMock\(|@patch|mock\.|_make_.*_record|"
    r"create_autospec",
)

_STRUCTURE_PATTERNS = re.compile(
    r"isinstance\(|hasattr\(|assertIsInstance|"
    r"assert\s+len\(|assert\s+type\(|"
    r"assert\s+\w+\s+in\s+\w+\.keys\(\)|"
    r'assert\s+"\w+"\s+in\s+\w+',
)

_BEHAVIOR_PATTERNS = re.compile(
    r"assert\s+\w+\s*==\s*|assert\s+\w+\s*!=\s*|"
    r"assert\s+\w+\s*[<>]=?\s*\d|"
    r"assert\s+.*\.exit_code\s*==|"
    r"assert\s+.*result\.|"
    r"\.fetchone\(\)|\.fetchall\(\)",
)

_FAILURE_KEYWORDS = re.compile(
    r"test_.*(?:invalid|error|fail|reject|bad|empty|missing|broken|"
    r"no_|none_|corrupt|malform|overflow|denied|block|exceed|crash)",
    re.IGNORECASE,
)

_EDGE_KEYWORDS = re.compile(
    r"test_.*(?:edge|boundary|limit|zero|one_|single|max_|min_|"
    r"empty_|huge|large|special|unicode|whitespace)",
    re.IGNORECASE,
)


def _get_source_lines(node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: list[str]) -> str:
    """Extract the source text of a function node."""
    start = node.lineno - 1
    end = node.end_lineno or start + 1
    return "\n".join(source_lines[start:end])


def _classify_data(source: str) -> str:
    """Classify whether a test uses real data or synthetic."""
    has_real = bool(_REAL_DB_PATTERNS.search(source))
    has_mock = bool(_MOCK_PATTERNS.search(source))
    if has_real and not has_mock:
        return "real_db"
    if has_mock:
        return "synthetic"
    if has_real and has_mock:
        return "synthetic"  # Mock overrides real
    return "no_data"


def _classify_assertion(source: str) -> str:
    """Classify whether assertions check behavior or structure."""
    has_raises = "pytest.raises" in source or "assertRaises" in source
    structure_count = len(_STRUCTURE_PATTERNS.findall(source))
    behavior_count = len(_BEHAVIOR_PATTERNS.findall(source))

    if has_raises:
        behavior_count += 2  # pytest.raises is strongly behavioral

    if behavior_count > 0 and structure_count > 0:
        return "mixed"
    if behavior_count > 0:
        return "behavior"
    if structure_count > 0:
        return "structure"
    # Default: if it has any assert, assume behavior
    if "assert " in source:
        return "behavior"
    return "structure"


def _classify_coverage(name: str, source: str) -> str:
    """Classify whether a test covers failure modes or just happy path."""
    has_raises = "pytest.raises" in source or "assertRaises" in source

    if has_raises or _FAILURE_KEYWORDS.match(name):
        return "failure_mode"
    if _EDGE_KEYWORDS.match(name):
        return "edge_case"
    return "happy_path"


def audit_test_file(filepath: Path) -> list[AuditClassification]:
    """Classify all test functions in a single file."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    source_lines = source.splitlines()
    file_source = source  # Full file for context
    results: list[AuditClassification] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue

        func_source = _get_source_lines(node, source_lines)

        results.append(
            AuditClassification(
                file=filepath.name,
                name=node.name,
                data_type=_classify_data(func_source + "\n" + file_source[:500]),
                assertion_type=_classify_assertion(func_source),
                coverage_type=_classify_coverage(node.name, func_source),
            )
        )

    return results


def audit_test_directory(test_dir: Path) -> AuditSummary:
    """Audit all test files in a directory."""
    summary = AuditSummary()

    # Count inline schemas
    schema_pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
        re.IGNORECASE,
    )

    for test_file in sorted(test_dir.glob("test_*.py")):
        classifications = audit_test_file(test_file)
        if not classifications:
            continue

        summary.total_files += 1
        summary.total_tests += len(classifications)

        # Check for inline schemas
        content = test_file.read_text(encoding="utf-8")
        inline_tables = schema_pattern.findall(content)
        if inline_tables:
            summary.inline_schemas += len(inline_tables)
            summary.schema_files.append(test_file.name)

        for c in classifications:
            summary.tests.append(c)

            # Data type
            if c.data_type == "real_db":
                summary.real_db += 1
            elif c.data_type == "synthetic":
                summary.synthetic += 1
            else:
                summary.no_data += 1

            # Assertion type
            if c.assertion_type == "behavior":
                summary.behavior += 1
            elif c.assertion_type == "structure":
                summary.structure += 1
            else:
                summary.mixed += 1

            # Coverage type
            if c.coverage_type == "failure_mode":
                summary.failure_mode += 1
            elif c.coverage_type == "edge_case":
                summary.edge_case += 1
            else:
                summary.happy_path += 1

    return summary


def format_audit_report(summary: AuditSummary) -> str:
    """Format audit results for display."""
    total = summary.total_tests or 1  # avoid division by zero

    lines = [
        f"Test Quality Audit: {summary.total_tests} tests across {summary.total_files} files",
        "",
        "  Data Source:",
        f"    Real DB:    {summary.real_db:>5} ({100 * summary.real_db / total:.0f}%)",
        f"    Synthetic:  {summary.synthetic:>5} ({100 * summary.synthetic / total:.0f}%)",
        f"    No data:    {summary.no_data:>5} ({100 * summary.no_data / total:.0f}%)",
        "",
        "  Assertion Type:",
        f"    Behavior:   {summary.behavior:>5} ({100 * summary.behavior / total:.0f}%)",
        f"    Structure:  {summary.structure:>5} ({100 * summary.structure / total:.0f}%)",
        f"    Mixed:      {summary.mixed:>5} ({100 * summary.mixed / total:.0f}%)",
        "",
        "  Coverage:",
        f"    Failure:    {summary.failure_mode:>5} ({100 * summary.failure_mode / total:.0f}%)",
        f"    Edge case:  {summary.edge_case:>5} ({100 * summary.edge_case / total:.0f}%)",
        f"    Happy path: {summary.happy_path:>5} ({100 * summary.happy_path / total:.0f}%)",
    ]

    if summary.inline_schemas:
        lines.extend(
            [
                "",
                "  Schema Divergence Risk:",
                f"    Inline CREATE TABLE: {summary.inline_schemas} in {len(summary.schema_files)} files",
                f"    Files: {', '.join(summary.schema_files)}",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "  Schema Sync: No inline CREATE TABLE found (all use production init)",
            ]
        )

    return "\n".join(lines)
