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

Known misuse case (out of scope, find-bdd0090493bc): a symlinked
data-home shared across two checkouts would bypass the ownership
check because both checkouts read the same marker through the link.
Not defended against — the design assumes data-homes are real
directories. Symlink to a shared backing store is operator-deliberate
configuration, not the failure mode this check was built for.

This module deliberately lives separately from core/paths.py so
that paths.py stays a pure path resolver (no filesystem mutation,
no fail-loud raising). The two layers compose: paths.py decides
WHERE the data-home is; this module decides whether the data-home
agrees with the running checkout.
"""

from __future__ import annotations

import os

# Module-level guardrail marker — Aletheia Finding 69 (2026-05-17).
# This file is on the multi-party-review list (scripts/guardrail_files.txt).
# CI test test_guardrail_marker_consistency walks src/ and asserts every
# guardrail-listed module sets this marker to True. Prevents the next
# refactor from silently removing self-enforcement code from review.
__guardrail_required__ = True


from pathlib import Path

from divineos.core.paths import divineos_home


OWNER_MARKER_NAME = ".divineos_checkout_owner"


class DataHomeOwnershipError(RuntimeError):
    """Raised when the resolved data-home is owned by a different checkout."""


def _checkout_root() -> Path:
    """Return the absolute path of the running checkout's root directory.

    Resolution order:

    1. **CWD-based**: walk up from CWD looking for a marker that identifies
       a checkout root (``.divineos_data_home`` or ``.divineos_canonical`` or
       a ``.git`` entry). Handles the case where divineos is installed
       editable from one clone but invoked from another. Mirrors the CWD
       resolution that ``core/paths.divineos_home()`` uses.

    2. **__file__-based**: fall back to four parents up from this file, then
       follow worktree-parent if it is a worktree of a parent repo.
    """
    try:
        cwd = Path.cwd().resolve()
        for ancestor in (cwd, *cwd.parents):
            if (ancestor / ".divineos_data_home").exists():
                return ancestor
            if (ancestor / ".divineos_canonical").exists():
                return ancestor
            git = ancestor / ".git"
            if git.is_dir():
                # Real repo root.
                return ancestor
            if git.is_file():
                # Worktree marker — follow to parent's working tree, which is
                # the canonical repo root for ownership purposes.
                try:
                    gtxt = git.read_text(encoding="utf-8").strip()
                    if gtxt.startswith("gitdir:"):
                        gd = Path(gtxt[len("gitdir:") :].strip()).resolve()
                        if len(gd.parents) >= 3:
                            return gd.parents[2].resolve()
                except (OSError, ValueError):
                    pass
                # Fallback if we can't parse: return the worktree itself.
                return ancestor
    except (OSError, ValueError):
        pass

    own = Path(__file__).parent.parent.parent.parent.resolve()
    git_marker = own / ".git"
    if git_marker.is_file():
        try:
            text_g = git_marker.read_text(encoding="utf-8").strip()
            if text_g.startswith("gitdir:"):
                gitdir = Path(text_g[len("gitdir:") :].strip()).resolve()
                if len(gitdir.parents) >= 3:
                    return gitdir.parents[2].resolve()
        except (OSError, ValueError):
            pass
    return own


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
    # 2026-06-14 (find-c607cd1e071a): normalize before comparison.
    # Plain str() leaves the path sensitive to platform quirks —
    # macOS case-folding, symlink-vs-not, UNC-vs-drive-letter on
    # Windows — that can falsely report ownership mismatch. realpath
    # resolves symlinks; normcase folds case on Windows/Mac.
    # Applied only to the comparison key; display strings keep the
    # original form so error messages show the path the user typed.
    checkout_key = os.path.normcase(os.path.realpath(checkout_str))

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
        # 2026-06-14 (find-107b00b725e8): atomic claim via O_EXCL.
        # The prior exists()-check-then-write_text() had a TOCTOU
        # race window — two concurrent first-boots could both pass
        # the exists() check, both write, and both think they
        # claimed. O_EXCL fails atomically if the file already
        # exists, so only one writer wins; the loser falls through
        # to the read-and-verify branch below.
        try:
            fd = os.open(
                marker,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o644,
            )
            try:
                os.write(fd, checkout_str.encode("utf-8"))
            finally:
                os.close(fd)
            return {
                "status": "claimed",
                "data_home": home_str,
                "owner": checkout_str,
                "checkout": checkout_str,
                "detail": "claimed ownership (first boot)",
            }
        except FileExistsError:
            # Race-lost: another process claimed during our window.
            # Fall through to read-and-verify their claim below.
            pass

    try:
        owner = marker.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise DataHomeOwnershipError(
            f"DivineOS data-home {home_str} has an unreadable owner marker "
            f"at {marker}: {exc}. Either fix permissions or remove the marker "
            f"to re-claim ownership from {checkout_str}."
        ) from exc

    owner_key = os.path.normcase(os.path.realpath(owner))
    if owner_key == checkout_key:
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
