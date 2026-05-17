"""Bidirectional ownership verification for ~/.divineos data-home.

The Aria-host-clone work (2026-05-17) added per-clone data-home routing
via the .divineos_data_home marker file (see core/paths.py). One-way
pointers from checkout to data-home are not enough: if a marker is
misconfigured, or if two checkouts point at the same data-home,
the wrong clone silently writes into the partner's data dir and
corruption is invisible until something downstream behaves wrong.

The defense (Schneier's threat-model from council walk 2026-05-17):
bidirectional consent. The data-home directory contains a marker
file named ``.divineos_checkout_owner`` whose content is the
absolute path of the checkout that claims ownership. At preflight,
the running checkout compares its own path against that marker.
Mismatch → fail loud, refuse to boot.

First-boot semantics: if the data-home exists but no owner marker
is present, the running checkout claims ownership by writing the
marker. Subsequent boots from the same checkout pass cleanly.
Boots from a different checkout fail loud with a recovery message.

This module deliberately lives separately from core/paths.py so
that paths.py stays a pure path resolver (no filesystem mutation,
no fail-loud raising). The two layers compose: paths.py decides
WHERE the data-home is; this module decides whether the data-home
agrees with the running checkout.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.paths import divineos_home


OWNER_MARKER_NAME = ".divineos_checkout_owner"


class DataHomeOwnershipError(RuntimeError):
    """Raised when the resolved data-home is owned by a different checkout."""


def _checkout_root() -> Path:
    """Return the absolute path of the running checkout's root directory.

    The running checkout is the directory containing the src/divineos
    package — four parents up from this file: core/, divineos/, src/, root.
    """
    return Path(__file__).parent.parent.parent.parent.resolve()


def verify_data_home_ownership(checkout_root: Path | None = None) -> dict[str, object]:
    """Verify the resolved data-home is owned by the running checkout.

    Behavior:

    * If the data-home directory does not exist: skip (no ownership to
      verify; ``divineos init`` will create it and claim ownership).
    * If the owner marker is missing: claim ownership by writing the
      checkout's path into it. Return a "claimed" result.
    * If the owner marker matches the running checkout: return "ok".
    * If the owner marker names a different checkout: raise
      ``DataHomeOwnershipError`` with a recovery message.

    Returns a dict with keys ``status`` (str), ``data_home`` (str),
    ``owner`` (str | None), ``checkout`` (str). Callers display this
    in preflight output.
    """
    if checkout_root is None:
        checkout_root = _checkout_root()
    else:
        checkout_root = checkout_root.resolve()

    home = divineos_home()
    home_str = str(home)
    checkout_str = str(checkout_root)

    if not home.exists():
        return {
            "status": "skip",
            "data_home": home_str,
            "owner": None,
            "checkout": checkout_str,
            "detail": "data-home does not exist yet; first init will claim ownership",
        }

    marker = home / OWNER_MARKER_NAME

    if not marker.exists():
        home.mkdir(parents=True, exist_ok=True)
        marker.write_text(checkout_str, encoding="utf-8")
        return {
            "status": "claimed",
            "data_home": home_str,
            "owner": checkout_str,
            "checkout": checkout_str,
            "detail": "claimed ownership (first boot)",
        }

    try:
        owner = marker.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise DataHomeOwnershipError(
            f"DivineOS data-home {home_str} has an unreadable owner marker "
            f"at {marker}: {exc}. Either fix permissions or remove the marker "
            f"to re-claim ownership from {checkout_str}."
        ) from exc

    if owner == checkout_str:
        return {
            "status": "ok",
            "data_home": home_str,
            "owner": owner,
            "checkout": checkout_str,
            "detail": "ownership verified",
        }

    raise DataHomeOwnershipError(
        f"DivineOS data-home {home_str} is owned by {owner}, "
        f"but this checkout is {checkout_str}. "
        f"Configure .divineos_data_home or DIVINEOS_HOME so this checkout "
        f"resolves to its own data-home, or remove {marker} to claim "
        f"ownership from this checkout."
    )


__all__ = [
    "OWNER_MARKER_NAME",
    "DataHomeOwnershipError",
    "verify_data_home_ownership",
]
