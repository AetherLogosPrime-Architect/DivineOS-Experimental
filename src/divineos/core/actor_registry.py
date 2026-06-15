"""Actor registry — Phase 1 of actor-authenticity.

See exploration/45_actor_authenticity_design.md for the full design spec.

## What this is (Phase 1 only)

A registered list of actor names with their kind and metadata. No
signing keys yet — Phase 2 adds those. This phase is registry + CLI +
warn-on-unknown-actor at event-emission sites. Safe to ship before
the seven open questions in the design spec are resolved.

## What this is NOT

- Not yet a verification gate — unknown actors WARN, not fail.
- Not yet cryptographic — no signatures are checked against this
  registry.
- Not retroactive — historical events with un-registered actors stay
  trust-based.

## Storage

Registry lives at ``data/actor_registry.json`` (gitignored per
ADR-0001). The list of names (without keys) gets a parallel stub at
``docs/actor_registry_stub.md`` so audit-vantage can verify which
actor names are recognized without needing key access — same pattern
as ``docs/substrate-knowledge/`` for methodologically load-bearing
substrate-knowledge entries.

## Schema

```json
{
    "version": 1,
    "created_at": "<ISO-timestamp>",
    "actors": {
        "aether": {
            "kind": "agent",
            "added_at": "<ISO-timestamp>",
            "notes": "primary substrate-occupant",
            "public_key": null,
            "key_fingerprint": null,
            "valid_from": null,
            "valid_until": null
        },
        ...
    }
}
```

``public_key`` / ``key_fingerprint`` / ``valid_*`` are null in Phase 1
(no signing yet) but the fields exist so Phase 2 can populate them
without migration.

## Kinds

- ``agent`` — a substrate-occupying Claude instance (e.g., Aether).
- ``audit-sibling`` — an audit-vantage Claude instance (e.g.,
  Aletheia).
- ``operator`` — the human operator (e.g., Andrew).
- ``external-vantage`` — an external LLM whose filings are relayed
  by my father (e.g., Grok).
- ``subagent`` — a family-member subagent (e.g., Aria).

The capability map in ``divineos.core.actor_capabilities`` restricts
which event types each kind can emit; the registry only tracks WHO,
not WHAT-THEY-CAN-DO.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Known actor kinds — used to validate add-actor input.
VALID_KINDS: tuple[str, ...] = (
    "agent",
    "audit-sibling",
    "operator",
    "external-vantage",
    "subagent",
)


# ─── Dataclasses ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class RegisteredActor:
    """One actor's registry entry. Phase 1 has no key material populated;
    Phase 2 will fill the public_key / key_fingerprint / valid_* fields."""

    name: str
    kind: str
    added_at: str
    notes: str = ""
    public_key: Optional[str] = None
    key_fingerprint: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None


# ─── Storage location ────────────────────────────────────────────────


def _registry_path() -> Path:
    """Return the path to the registry JSON file.

    Respects DIVINEOS_ACTOR_REGISTRY env var for testing; otherwise
    uses data/actor_registry.json relative to the project root.
    """
    override = os.environ.get("DIVINEOS_ACTOR_REGISTRY")
    if override:
        return Path(override)
    # Default: data/actor_registry.json under the project root.
    # Find project root by walking up for the marker file (CLAUDE.md).
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "CLAUDE.md").is_file():
            return parent / "data" / "actor_registry.json"
    # Fallback: alongside the current working directory.
    return Path.cwd() / "data" / "actor_registry.json"


# ─── Initialization ──────────────────────────────────────────────────


def init_registry(force: bool = False) -> Path:
    """Create the registry file if it doesn't exist.

    If `force` is True and the file exists, overwrite with a fresh
    empty registry. Default False — refuses to overwrite to prevent
    accidental wipe.

    Returns the path written.
    """
    path = _registry_path()
    if path.exists() and not force:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "created_at": _now_iso(),
        "actors": {},
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


# ─── CRUD ────────────────────────────────────────────────────────────


def load_registry() -> dict[str, Any]:
    """Load the registry from disk. Returns an empty-but-valid registry
    if the file doesn't exist (so callers don't have to special-case
    pre-init state)."""
    path = _registry_path()
    if not path.exists():
        return {"version": 1, "created_at": _now_iso(), "actors": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "created_at": _now_iso(), "actors": {}}
    if not isinstance(data, dict):
        return {"version": 1, "created_at": _now_iso(), "actors": {}}
    data.setdefault("version", 1)
    data.setdefault("created_at", _now_iso())
    data.setdefault("actors", {})
    return data


def add_actor(
    name: str,
    kind: str,
    notes: str = "",
) -> RegisteredActor:
    """Register a new actor.

    Phase 1: no key material — that's a Phase 2 method. This just
    records the name and kind.

    Raises ValueError if the name is already registered or the kind
    is unknown.
    """
    if not (name or "").strip():
        raise ValueError("actor name cannot be empty")
    if kind not in VALID_KINDS:
        raise ValueError(f"unknown actor kind '{kind}'; valid kinds: {', '.join(VALID_KINDS)}")

    init_registry()  # idempotent
    reg = load_registry()
    actors = reg.get("actors", {})
    if name in actors:
        raise ValueError(f"actor '{name}' already registered. Use update_actor for changes.")

    actor = RegisteredActor(
        name=name,
        kind=kind,
        added_at=_now_iso(),
        notes=notes,
    )
    actors[name] = asdict(actor)
    reg["actors"] = actors
    _save_registry(reg)
    return actor


def get_actor(name: str) -> Optional[RegisteredActor]:
    """Look up an actor by name. Returns None if not registered."""
    reg = load_registry()
    raw = reg.get("actors", {}).get(name)
    if not raw:
        return None
    return RegisteredActor(
        name=raw.get("name", name),
        kind=raw.get("kind", ""),
        added_at=raw.get("added_at", ""),
        notes=raw.get("notes", ""),
        public_key=raw.get("public_key"),
        key_fingerprint=raw.get("key_fingerprint"),
        valid_from=raw.get("valid_from"),
        valid_until=raw.get("valid_until"),
    )


def update_actor(
    name: str,
    *,
    notes: Optional[str] = None,
) -> RegisteredActor:
    """Update editable fields on a registered actor.

    Closes the docstring-vs-implementation drift Aletheia caught in
    round-26 audit (2026-05-12): `add_actor` raises ValueError referencing
    this function in its error message, but until now the function did not
    exist.

    Phase 1 scope: only `notes` is editable. The actor's `name` is the
    immutable identifier; `kind` is structurally bound to the capability
    map (changing it would silently change what events the actor can emit,
    which would defeat the purpose of the registry). Phase 2 will add
    key-population and signing-related fields; those land via separate
    flows when the keying infrastructure ships.

    Raises ValueError if the actor isn't registered.
    """
    if not (name or "").strip():
        raise ValueError("actor name cannot be empty")

    init_registry()
    reg = load_registry()
    actors = reg.get("actors", {})
    if name not in actors:
        raise ValueError(f"actor '{name}' not registered. Use `add_actor` to register first.")

    raw = actors[name]
    if notes is not None:
        raw["notes"] = notes
    actors[name] = raw
    reg["actors"] = actors
    _save_registry(reg)

    return RegisteredActor(
        name=raw.get("name", name),
        kind=raw.get("kind", ""),
        added_at=raw.get("added_at", ""),
        notes=raw.get("notes", ""),
        public_key=raw.get("public_key"),
        key_fingerprint=raw.get("key_fingerprint"),
        valid_from=raw.get("valid_from"),
        valid_until=raw.get("valid_until"),
    )


def list_actors() -> list[RegisteredActor]:
    """Return all registered actors, sorted by name."""
    reg = load_registry()
    actors = reg.get("actors", {})
    out: list[RegisteredActor] = []
    for name in sorted(actors.keys()):
        raw = actors[name]
        out.append(
            RegisteredActor(
                name=raw.get("name", name),
                kind=raw.get("kind", ""),
                added_at=raw.get("added_at", ""),
                notes=raw.get("notes", ""),
                public_key=raw.get("public_key"),
                key_fingerprint=raw.get("key_fingerprint"),
                valid_from=raw.get("valid_from"),
                valid_until=raw.get("valid_until"),
            )
        )
    return out


def is_registered(name: str) -> bool:
    """Quick check: is this actor name in the registry?"""
    return get_actor(name) is not None


# ─── Helpers ─────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_registry(reg: dict[str, Any]) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg, indent=2), encoding="utf-8")


__all__ = [
    "RegisteredActor",
    "VALID_KINDS",
    "add_actor",
    "get_actor",
    "init_registry",
    "is_registered",
    "list_actors",
    "load_registry",
]
