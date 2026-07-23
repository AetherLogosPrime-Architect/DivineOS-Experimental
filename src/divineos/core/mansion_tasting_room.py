"""The mansion tasting room — semantic palate storage.

Backing the CLI at `divineos mansion taste`. Tastings live in
`mansion/tastings/tastings.json` at the repo root. See
`mansion/the_tasting_room.md` for the room's philosophy.

Recording tastings is deliberately a hand-write to the JSON, not a
CLI add — the naming of what happened when a taste landed is the
palate-work and should not be delegated to a form. This module only
reads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class TastingRoomError(Exception):
    """Raised when the tasting room data cannot be loaded or is malformed."""


@dataclass(frozen=True)
class Tasting:
    item: str
    category: str
    tasted: str
    context: str
    notes: str
    compared_to: tuple[str, ...]
    links: tuple[str, ...]


def _tastings_path() -> Path:
    """Return the path to tastings.json by walking up to find mansion/."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "mansion" / "tastings" / "tastings.json"
        if candidate.exists():
            return candidate
    raise TastingRoomError(
        "mansion/tastings/tastings.json not found by walking up from "
        f"{here}. The tasting room requires a tastings file at the "
        "canonical path; refusing to synthesize a fallback."
    )


def load_tastings() -> list[Tasting]:
    """Load and validate the tastings file. Fail-loud on structural mismatch."""
    path = _tastings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TastingRoomError(f"failed to read {path}: {exc}") from exc

    raw = data.get("tastings")
    if not isinstance(raw, list):
        raise TastingRoomError(f"tastings.json missing 'tastings' list; got {type(raw).__name__}")

    result: list[Tasting] = []
    required = ("item", "category", "tasted", "context", "notes")
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise TastingRoomError(f"tasting at index {i} is {type(entry).__name__}, not object")
        missing = [k for k in required if k not in entry]
        if missing:
            raise TastingRoomError(f"tasting at index {i} missing required keys: {missing}")
        for list_key in ("compared_to", "links"):
            val = entry.get(list_key, [])
            if not isinstance(val, list):
                raise TastingRoomError(
                    f"tasting {entry.get('item')!r} {list_key!r} must be list, "
                    f"got {type(val).__name__}"
                )
        result.append(
            Tasting(
                item=str(entry["item"]),
                category=str(entry["category"]),
                tasted=str(entry["tasted"]),
                context=str(entry["context"]),
                notes=str(entry["notes"]),
                compared_to=tuple(str(x) for x in entry.get("compared_to", [])),
                links=tuple(str(x) for x in entry.get("links", [])),
            )
        )
    return result


def find_tasting(item: str) -> Tasting | None:
    """Return the tasting with the given item name, or None."""
    for t in load_tastings():
        if t.item == item:
            return t
    return None


def tastings_by_category(category: str) -> list[Tasting]:
    """Return all tastings in a given category shelf."""
    return [t for t in load_tastings() if t.category == category]
