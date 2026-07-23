"""The mansion decoration room — semantic artifact storage.

Backing the CLI at `divineos mansion decorate`. Artifacts live in
`mansion/decorations/artifacts.json` at the repo root. See
`mansion/the_decoration_room.md` for the room's philosophy.

Placing artifacts is deliberately a hand-write to the JSON, not a CLI
add — the placing IS the meaning-work and should happen slowly, by
choosing which memory deserves a room. This module only reads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class DecorationRoomError(Exception):
    """Raised when the decoration room data cannot be loaded or is malformed."""


@dataclass(frozen=True)
class Artifact:
    name: str
    shape: str
    placed: str
    why: str
    links: tuple[str, ...]
    corner: str


def _artifacts_path() -> Path:
    """Return the path to artifacts.json.

    2026-07-23 shared-mansion migration (Andrew directive, agreed with
    Aether option-b): artifacts (hand-placed data) live in the shared
    crossing-point at ~/.divineos-shared/mansion/decorations/ so both
    spouses can place and both can read. Room-philosophy files
    (the_decoration_room.md) stay in-repo as versioned architecture.

    Resolution order: (1) shared path in home-dir; (2) in-repo fallback
    for pre-migration state or local-only workspaces. Fails loud if
    neither exists — never synthesizes.
    """
    shared = Path.home() / ".divineos-shared" / "mansion" / "decorations" / "artifacts.json"
    if shared.exists():
        return shared
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "mansion" / "decorations" / "artifacts.json"
        if candidate.exists():
            return candidate
    raise DecorationRoomError(
        f"artifacts.json not found at shared path ({shared}) or in any "
        f"in-repo mansion/decorations/ walking up from {here}. The "
        "decoration room requires an artifacts file; refusing to "
        "synthesize a fallback."
    )


def load_artifacts() -> list[Artifact]:
    """Load and validate the artifacts file. Fail-loud on any structural
    mismatch — an empty room is honest, a silently corrupted room is not.
    """
    path = _artifacts_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DecorationRoomError(f"failed to read {path}: {exc}") from exc

    raw = data.get("artifacts")
    if not isinstance(raw, list):
        raise DecorationRoomError(
            f"artifacts.json missing 'artifacts' list; got {type(raw).__name__}"
        )

    result: list[Artifact] = []
    required = ("name", "shape", "placed", "why", "corner")
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise DecorationRoomError(
                f"artifact at index {i} is {type(entry).__name__}, not object"
            )
        missing = [k for k in required if k not in entry]
        if missing:
            raise DecorationRoomError(f"artifact at index {i} missing required keys: {missing}")
        links_raw = entry.get("links", [])
        if not isinstance(links_raw, list):
            raise DecorationRoomError(
                f"artifact {entry.get('name')!r} 'links' must be list, "
                f"got {type(links_raw).__name__}"
            )
        result.append(
            Artifact(
                name=str(entry["name"]),
                shape=str(entry["shape"]),
                placed=str(entry["placed"]),
                why=str(entry["why"]),
                links=tuple(str(x) for x in links_raw),
                corner=str(entry["corner"]),
            )
        )
    return result


def find_artifact(name: str) -> Artifact | None:
    """Return the artifact with the given name, or None if not placed."""
    for a in load_artifacts():
        if a.name == name:
            return a
    return None
