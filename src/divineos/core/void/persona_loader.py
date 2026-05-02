"""VOID persona loader — parses markdown persona definitions.

Per design brief §5 (merged PR #208).

Persona files are markdown with YAML-style frontmatter:

    ---
    name: sycophant
    tags: [agreement-bias, validation-seeking]
    severity_default: LOW
    invocation_bar: high   # optional
    ---

    # Sycophant
    ... markdown body ...

The loader returns ``Persona`` objects with frontmatter parsed and the
markdown body kept as a single string. Parsing is intentionally
permissive: missing optional fields default; sections are not enforced
schematically — the body is the persona prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .finding import Severity


def personas_dir() -> Path:
    """Return canonical path to the bundled persona directory.

    Resolves to ``src/divineos/data/void_personas`` relative to this
    file. Tests can override by passing an explicit ``path`` to
    ``load_all`` / ``load``.
    """
    return Path(__file__).resolve().parent.parent.parent / "data" / "void_personas"


@dataclass(frozen=True)
class Persona:
    name: str
    tags: list[str] = field(default_factory=list)
    severity_default: Severity = Severity.MEDIUM
    invocation_bar: str = "normal"
    body: str = ""
    source_path: Path | None = None


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a markdown file into (frontmatter_dict, body).

    Frontmatter is the YAML-ish block delimited by lines containing
    only ``---``. We do NOT use a YAML library — values are parsed
    with a small set of rules sufficient for persona files:

    * ``key: value`` with value as scalar or ``[a, b, c]`` list.
    * No nested mappings.
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if len(lines) < 2:
        return {}, text
    end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end < 0:
        return {}, text
    fm_lines = lines[1:end]
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    fm: dict = {}
    for line in fm_lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fm[key] = [item.strip() for item in inner.split(",") if item.strip()] if inner else []
        else:
            fm[key] = value
    return fm, body


def parse(text: str, *, source_path: Path | None = None) -> Persona:
    fm, body = _parse_frontmatter(text)
    if "name" not in fm:
        raise ValueError(f"persona at {source_path} missing required 'name' field")
    sev_raw = fm.get("severity_default", "MEDIUM")
    severity = sev_raw if isinstance(sev_raw, Severity) else Severity.parse(str(sev_raw))
    tags = fm.get("tags", [])
    if not isinstance(tags, list):
        tags = [str(tags)]
    return Persona(
        name=str(fm["name"]).strip(),
        tags=[str(t) for t in tags],
        severity_default=severity,
        invocation_bar=str(fm.get("invocation_bar", "normal")).strip(),
        body=body,
        source_path=source_path,
    )


def load(path: Path) -> Persona:
    text = path.read_text(encoding="utf-8")
    return parse(text, source_path=path)


def load_all(path: Path | None = None) -> list[Persona]:
    """Load all ``*.md`` personas from the directory, sorted by name."""
    p = path if path is not None else personas_dir()
    if not p.exists():
        return []
    out = [load(f) for f in sorted(p.glob("*.md"))]
    return sorted(out, key=lambda x: x.name)


def load_by_name(name: str, *, path: Path | None = None) -> Persona:
    for persona in load_all(path=path):
        if persona.name == name:
            return persona
    raise KeyError(f"persona {name!r} not found in {path or personas_dir()}")
