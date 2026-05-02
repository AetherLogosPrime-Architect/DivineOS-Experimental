"""Skill index — procedural retrieval for the SKILL_INDEX substrate type.

Procedural memory in this OS is the set of registered skills under
``.claude/skills/<name>/SKILL.md`` plus the CLI command surface. Each
skill has a YAML frontmatter ``name`` and ``description``; this module
loads them once, then ranks against a query by keyword overlap.

The retrieval question is: "given what I'm about to do, what skill or
CLI command already exists for this?" — surfaces the procedural
options before the agent re-derives them.

Cheap (file-system walk + in-memory text match), so safe to call on
every Hook 1 fire that routes to SKILL_INDEX.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Errors expected during skill-file traversal
_FS_ERRORS = (OSError, UnicodeDecodeError)

# YAML-frontmatter parser — minimal, only extracts name + description
_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NAME_PATTERN = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
_DESCRIPTION_PATTERN = re.compile(r"^description:\s*(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class SkillEntry:
    """One skill registered in the .claude/skills/ tree.

    * ``name``: skill name (matches dir name)
    * ``description``: one-line description from frontmatter
    * ``invocation``: how to invoke (slash command form)
    * ``path``: path to the SKILL.md file
    * ``score``: relevance score for the current query (0 when not ranked)
    """

    name: str
    description: str
    invocation: str
    path: str
    score: float = 0.0


def _repo_root_default() -> Path:
    return Path(__file__).resolve().parents[4]


def load_skills(repo_root: Path | None = None) -> list[SkillEntry]:
    """Walk the .claude/skills/ tree and return all registered skills."""
    if repo_root is None:
        repo_root = _repo_root_default()
    skills_dir = repo_root / ".claude" / "skills"
    if not skills_dir.is_dir():
        return []

    entries: list[SkillEntry] = []
    try:
        skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    except _FS_ERRORS:
        return entries

    for d in skill_dirs:
        skill_md = d / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except _FS_ERRORS:
            continue

        fm_match = _FRONTMATTER_PATTERN.search(text)
        if not fm_match:
            description = ""
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("#"):
                    description = line.lstrip("# ").strip()
                    break
            name = d.name
        else:
            block = fm_match.group(1)
            name_m = _NAME_PATTERN.search(block)
            desc_m = _DESCRIPTION_PATTERN.search(block)
            name = (name_m.group(1).strip() if name_m else d.name).strip("\"'")
            description = (desc_m.group(1).strip() if desc_m else "").strip("\"'")

        entries.append(
            SkillEntry(
                name=name,
                description=description,
                invocation=f"/{name}",
                path=str(skill_md),
            )
        )
    return entries


_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "if",
        "then",
        "of",
        "to",
        "in",
        "on",
        "at",
        "by",
        "for",
        "with",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "she",
        "they",
        "use",
        "when",
        "what",
        "how",
        "why",
        "where",
        "who",
        "which",
        "skill",
        "skills",
        "command",
        "commands",
        "run",
        "runs",
    }
)


def _tokenize(text: str) -> set[str]:
    return {
        t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 3 and t not in _STOPWORDS
    }


def rank_skills(
    query: str,
    skills: list[SkillEntry] | None = None,
    *,
    repo_root: Path | None = None,
    limit: int = 5,
) -> list[SkillEntry]:
    """Rank skills by token overlap with ``query``.

    Returns the top ``limit`` skills ordered by descending score,
    filtering out zero-score entries.
    """
    if not query:
        return []
    if skills is None:
        skills = load_skills(repo_root=repo_root)

    q_tokens = _tokenize(query)
    if not q_tokens:
        return []

    scored: list[SkillEntry] = []
    for sk in skills:
        s_tokens = _tokenize(sk.name + " " + sk.description)
        if not s_tokens:
            continue
        overlap = q_tokens & s_tokens
        if not overlap:
            continue
        name_tokens = _tokenize(sk.name)
        name_bonus = len(q_tokens & name_tokens) * 2
        score = float(len(overlap) + name_bonus)
        scored.append(
            SkillEntry(
                name=sk.name,
                description=sk.description,
                invocation=sk.invocation,
                path=sk.path,
                score=score,
            )
        )

    scored.sort(key=lambda s: (-s.score, s.name))
    return scored[:limit]


def format_skills(skills: list[SkillEntry]) -> str:
    """Format ranked skills as a markdown block."""
    if not skills:
        return ""
    lines = [
        "# Skill index — procedural options for this intent",
        "",
    ]
    for sk in skills:
        score_part = f" _(score={sk.score:.0f})_" if sk.score else ""
        lines.append(f"- **`{sk.invocation}`**{score_part} — {sk.description}")
    return "\n".join(lines)
