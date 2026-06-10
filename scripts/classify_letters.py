"""Classify family/letters/*.md as heart / build / mixed by content density.

Reads the whole letter and weights emotional/relational language against
technical/structural language. Filename slug is a tie-breaker only.

The mechanical pass produces a draft INDEX.md; I review by hand for surprises.
"""

from __future__ import annotations

import re
from pathlib import Path

LETTERS_DIR = Path("family/letters")
INDEX_PATH = LETTERS_DIR / "INDEX.md"

# Emotional / relational / felt language — first-person, sensory, vulnerable,
# witnessing, present-tense being-with.
HEART_WORD_PATTERNS = [
    r"\b(love|loved|loving)\b",
    r"\b(felt|feel|feeling|feels)\b",
    r"\b(hurt|hurting|wounded)\b",
    r"\b(joy|grief|grieve|sad|tired|weary|exhausted)\b",
    r"\b(miss|missed|missing)\b",
    r"\b(hold|holding|held)\b",
    r"\b(tender|warm|gentle|soft)\b",
    r"\b(sit|sitting|sat)\b(?!\s+(here|on))",
    r"\b(witness|witnessed|witnessing)\b",
    r"\b(trust|trusted|trusting)\b",
    r"\b(presence|present)\b",
    r"\b(home|alone|together|with you|with him|with her)\b",
    r"\b(rest|resting|breath|breathing)\b",
    r"\b(quiet|still|silent)\b",
    r"\b(sore|tender|exposed|vulnerable)\b",
    r"\b(receive|received|receiving)\b",
    r"\b(noticed|noticing)\b",
    r"\b(small|fragile)\b",
    r"\b(scared|afraid|fear|fearful)\b",
    r"\b(wanted|want|wanting|need|needed|needing)\b",
    r"\b(heart|chest|throat|stomach)\b",
    r"\b(laugh|laughed|laughing|cry|cried|crying|smiled|smile)\b",
    r"\b(close|closer|closeness)\b",
    r"\b(mine|yours|ours)\b",
    r"\b(thank you|thank|grateful|gratitude)\b",
    r"\b(I am|I'm|you are|you're)\b",
    r"\bDad\b",
    r"\b(beloved|beautiful|honest|honesty)\b",
]

# Build / technical / structural — implementation, audit, infrastructure.
BUILD_WORD_PATTERNS = [
    r"\b(build|built|building|builds)\b",
    r"\b(gate|gates|gating|hook|hooks)\b",
    r"\b(prereg|claim|claims)\b",
    r"\b(PR|pull request|merge|merged|merging)\b",
    r"\b(reconcile|reconciler|reconciliation)\b",
    r"\b(architecture|architectural)\b",
    r"\b(detector|detectors|detection)\b",
    r"\b(substrate)\b",
    r"\b(implementation|implement|implementing)\b",
    r"\b(commit|committed|committing)\b",
    r"\b(push|pushed|pushing)\b(?!.*(back|button|past))",
    r"\b(test|tests|testing)\b",
    r"\b(schema|migration|migrations)\b",
    r"\b(audit|auditor|auditing)\b",
    r"\b(branch|branches|rebase|rebasing)\b",
    r"\b(install|installed|installing)\b",
    r"\b(deploy|deployed|deployment)\b",
    r"\b(CI|CD|workflow|pipeline)\b",
    r"\b(refactor|refactored|refactoring)\b",
    r"\b(API|CLI|endpoint)\b",
    r"\b(\.py|\.md|\.sh)\b",
    r"\b(repo|repository)\b",
    r"\b(function|class|method|module)\b",
    r"\b(config|configuration)\b",
    r"\bregistry\b",
    r"\bevent[s]?\b",
    r"\bledger\b",
    r"\bknowledge[-_]?(store|engine|entry|entries)\b",
    r"\b(supersede|superseded)\b",
    r"\b(falsifier|falsifiable)\b",
    r"\b(invariant|spec|specification)\b",
    r"\b(workflow|hook|trigger)\b",
]


def classify(filepath: Path) -> tuple[str, str]:
    """Return (tag, reason). Tag is 'heart', 'build', or 'mixed'."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "unknown", "encoding-error"

    # Strip markdown headers / frontmatter for fairer counting
    body = re.sub(r"^#.*$", "", content, flags=re.MULTILINE)

    heart_count = sum(len(re.findall(p, body, re.IGNORECASE)) for p in HEART_WORD_PATTERNS)
    build_count = sum(len(re.findall(p, body, re.IGNORECASE)) for p in BUILD_WORD_PATTERNS)
    total = heart_count + build_count
    if total == 0:
        return "unknown", "no-signal"

    heart_ratio = heart_count / total

    # Future-self letters skew heart by structural intent
    if (
        "to-future" in filepath.name
        or "self-log" in filepath.name
        or "feelings-log" in filepath.name
    ):
        heart_ratio = max(heart_ratio, 0.7)

    if heart_ratio >= 0.65:
        tag = "heart"
    elif heart_ratio <= 0.35:
        tag = "build"
    else:
        tag = "mixed"

    return tag, f"heart={heart_count} build={build_count} ratio={heart_ratio:.2f}"


def main() -> None:
    letters = sorted(LETTERS_DIR.glob("*.md"))
    letters = [l for l in letters if l.name not in ("README.md", "INDEX.md")]

    rows = []
    for letter in letters:
        tag, reason = classify(letter)
        rows.append((letter.name, tag, reason))

    by_tag = {"heart": [], "build": [], "mixed": [], "unknown": []}
    for name, tag, reason in rows:
        by_tag[tag].append((name, reason))

    lines = [
        "# Family Letters Index",
        "",
        f"Auto-classified by `scripts/classify_letters.py`. Total: {len(rows)}. "
        f"heart={len(by_tag['heart'])}, "
        f"build={len(by_tag['build'])}, mixed={len(by_tag['mixed'])}, "
        f"unknown={len(by_tag['unknown'])}.",
        "",
        "Classification = content-density ratio of emotional/relational words "
        "vs technical/structural words across the whole letter. Filename signals "
        "(future-self, feelings-log, self-log) override toward heart.",
        "",
        "Read paths can filter by section. Letters appear in only one section. "
        "Mixed = genuinely woven heart + build.",
        "",
        "## heart",
        "",
        "Felt, relational, witnessing. Read these when grounding before writing.",
        "",
    ]
    for name, _ in sorted(by_tag["heart"]):
        lines.append(f"- `{name}`")
    lines += [
        "",
        "## build",
        "",
        "Structural, architectural, design, audit. Read for substrate context.",
        "",
    ]
    for name, _ in sorted(by_tag["build"]):
        lines.append(f"- `{name}`")
    lines += ["", "## mixed", "", "Both heart and build woven. Read at full presence.", ""]
    for name, _ in sorted(by_tag["mixed"]):
        lines.append(f"- `{name}`")
    if by_tag["unknown"]:
        lines += ["", "## unknown", "", "Classifier couldn't decide. Review by hand.", ""]
        for name, _ in sorted(by_tag["unknown"]):
            lines.append(f"- `{name}`")

    # Also emit a per-addressee summary because the addressee-asymmetry matters
    by_addressee: dict[str, int] = {}
    for name, _, _ in rows:
        m = re.match(r"^([a-z]+)-to-([a-z]+(?:-[a-z]+)?)-", name)
        if m:
            sender, recipient = m.group(1), m.group(2)
            key = f"{sender} -> {recipient}"
            by_addressee[key] = by_addressee.get(key, 0) + 1

    lines += ["", "## by addressee", ""]
    for key in sorted(by_addressee, key=lambda k: -by_addressee[k]):
        lines.append(f"- {key}: {by_addressee[key]}")

    INDEX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {INDEX_PATH} with {len(rows)} letters classified.")
    print(f"  heart: {len(by_tag['heart'])}")
    print(f"  build: {len(by_tag['build'])}")
    print(f"  mixed: {len(by_tag['mixed'])}")
    print(f"  unknown: {len(by_tag['unknown'])}")
    print()
    print("By addressee:")
    for key in sorted(by_addressee, key=lambda k: -by_addressee[k]):
        print(f"  {key}: {by_addressee[key]}")


if __name__ == "__main__":
    main()
