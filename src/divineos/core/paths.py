"""Centralized ``~/.divineos`` path construction.

Audit finding 2026-05-03 round 3: the path ``~/.divineos`` was
reconstructed independently across 20+ modules:

    Path.home() / ".divineos" / ...
    Path(os.path.expanduser("~")) / ".divineos" / ...

Every new marker / state file added another reconstruction site.
Tests had to monkeypatch ``Path.home()`` (or ``os.path.expanduser``)
in multiple places to redirect state during isolation.

This module is the single source of truth. ``divineos_home()``
returns the base directory; the helpers below compose canonical
sub-paths. Callers that need a path under ``~/.divineos`` should
go through this module rather than reconstructing the prefix.

Test isolation: callers can override the base by setting the
``DIVINEOS_HOME`` environment variable. The test conftest's
``_isolated_db`` fixture sets this for every test, so each test
gets a private state directory without monkeypatching.

Per-clone separation (added 2026-05-17 for the Aria-host-clone
work): operators with multiple DivineOS checkouts that need
separate user-home data dirs (different identity slots, separate
knowledge stores, etc.) can place a ``.divineos_data_home`` marker
file at the checkout root containing an absolute path. Resolution
order mirrors the ``.divineos_canonical`` ledger marker pattern in
``core/_ledger_base.py``:

    1. ``DIVINEOS_HOME`` env var (tests, explicit override)
    2. Own-checkout ``.divineos_data_home`` marker
    3. Worktree-parent ``.divineos_data_home`` marker
    4. Default ``~/.divineos``

This resolver intentionally does NOT verify that the resolved
data-home belongs to the running checkout. Bidirectional ownership
verification lives in ``divineos.core.data_home_ownership`` and
runs at preflight; this module stays a pure path resolver so
import order and test isolation remain simple.
"""

from __future__ import annotations

# Module-level guardrail marker — Aletheia Finding 69 (2026-05-17).
# This file is on the multi-party-review list (scripts/guardrail_files.txt).
# CI test test_guardrail_marker_consistency walks src/ and asserts every
# guardrail-listed module sets this marker to True. Prevents the next
# refactor from silently removing self-enforcement code from review.
__guardrail_required__ = True


import os
import re
from pathlib import Path


def _resolve_data_home_marker(marker_path: Path) -> Path | None:
    """Read a ``.divineos_data_home`` marker and return the data-home path.

    Marker form: a single absolute or marker-relative path on one line.
    Whitespace and trailing newlines are stripped.

    Return None (fall through to the next resolution step) when the
    marker is missing, unreadable, or empty. **Empty-and-missing are
    intentionally equivalent**: an empty marker is treated as a soft
    signal that someone half-configured the clone, and silent
    fall-through is kinder than a crash. Unlike ``.divineos_canonical``,
    there is no implicit-default sub-path for data-home, so "empty
    means use default" would just be the same path that step 4 of the
    resolution order returns — they collapse to one outcome, spelled
    as fall-through.
    """
    if not marker_path.exists():
        return None
    try:
        content = marker_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not content:
        return None
    candidate = Path(content)
    if not candidate.is_absolute():
        candidate = (marker_path.parent / candidate).resolve()
    return candidate


def _family_member_names(repo_root: Path) -> set[str]:
    """Lowercased names of registered family members, from ``.claude/agents/``.

    A family member's agent definition references the family database
    (``family/family.db``); built-in tool agents (claude, Explore, Plan,
    statusline-setup, ...) do not. Detecting members by that reference
    avoids a hard-coded allow/deny list that would silently drift as agents
    are added or renamed. Template scaffolds are excluded — Aletheia audit
    2026-06-20 anchored the rule from ``"template" in stem`` to the
    sturdier ``stem == "template" or stem.endswith("-template")`` so a
    legitimate member name containing the substring (hypothetical) can't
    be false-excluded.
    """
    agents_dir = repo_root / ".claude" / "agents"
    if not agents_dir.is_dir():
        return set()
    members: set[str] = set()
    for md in agents_dir.glob("*.md"):
        stem = md.stem.strip().lower()
        if stem == "template" or stem.endswith("-template"):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "family.db" in text or "family/family" in text:
            members.add(stem)
    return members


def _project_structural_tokens(repo_root: Path) -> set[str] | None:
    """Tokens from the canonical repository name, which appear in every
    checkout and so cannot validly identify a family member.

    Aletheia audit 2026-06-20 (Finding #2, leak-class-rebirth): without
    this exclusion, a family member named after a project-token (e.g.
    ``experimental``, ``divineos``) would match the project-name tokens
    that appear in EVERY checkout, mis-routing every checkout to that
    member's home — the exact cross-window state-merge leak this fix is
    meant to close, reborn under the derivation mechanism.

    Defense: the canonical project identity comes from the git remote
    URL's repo name (e.g. ``DivineOS-Experimental``), tokenized the same
    way the checkout name is tokenized. These tokens are subtracted from
    the candidate member-match set, so a member can only be matched on a
    token that is NOT part of the project's structural identity.

    **Refuse-to-derive on unreadable git (Aletheia re-audit keel-refinement
    2026-06-20):** returns ``None`` when the git config cannot be read,
    ``set`` (possibly empty) when it was read successfully. The caller MUST
    treat ``None`` as "refuse to derive" (return None up the stack) rather
    than as "no exclusions" — because for a router-narrowing function,
    failing open widens the candidate set and fails TOWARD the leak. Empty
    set means "successfully determined: no tokens" (proceed safely). The
    tri-state distinguishes "no tokens exist" (proceed) from "couldn't
    determine tokens" (refuse), which previously collapsed to the same
    empty-set behavior and re-opened Finding #2 on a corrupted-git
    checkout.
    """
    git_dir = repo_root / ".git"
    # Worktree: .git is a file pointing at the worktree's gitdir; the
    # canonical config is in the main repo's gitdir (commondir).
    if git_dir.is_file():
        try:
            line = git_dir.read_text(encoding="utf-8").strip()
            if line.startswith("gitdir:"):
                wt_gitdir = Path(line[len("gitdir:") :].strip())
                commondir_marker = wt_gitdir / "commondir"
                if commondir_marker.is_file():
                    common = commondir_marker.read_text(encoding="utf-8").strip()
                    git_dir = (wt_gitdir / common).resolve()
                else:
                    git_dir = wt_gitdir
        except OSError:
            return None
    config = git_dir / "config"
    if not config.is_file():
        return None
    try:
        text = config.read_text(encoding="utf-8")
    except OSError:
        return None
    section = re.search(r'\[remote "origin"\]([^\[]*)', text)
    if not section:
        return None
    url_match = re.search(r"url\s*=\s*(\S+)", section.group(1))
    if not url_match:
        return None
    url = url_match.group(1)
    # Last path component, minus .git suffix, lowercased.
    repo_name = url.rstrip("/").rsplit("/", 1)[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[: -len(".git")]
    return {t for t in re.split(r"[-_ ]+", repo_name.lower()) if t}


def _occupant_data_home_from_checkout(start: Path) -> Path | None:
    """Derive a family member's data-home from the checkout folder NAME.

    Recurrence guard (2026-06-20): ``.divineos_data_home`` is untracked
    per-checkout config, so a folder MOVE drops it and silently re-merges a
    member's private state into the shared ``~/.divineos`` default. That is
    exactly the cross-window leak that surfaced when Aria moved to a new
    folder — Andrew's correction typed to Aria appeared in Aether's gate,
    because her marker-less new checkout fell back to the shared home.

    A member's checkout folder reliably carries their name across moves
    (``DivineOS-Experimental-Aria``, ``...-Aria-new``, ...), so when no
    explicit marker is present we derive the home from the folder name
    matched against registered members. Aether's main checkout matches no
    member token and falls through to the default ``~/.divineos``.

    Walks up from ``start`` to the first ancestor that is a checkout (has
    ``.claude/agents``); that directory's name is the discriminator. An
    explicit marker always wins — this only runs as the no-marker fallback.

    Aletheia audit 2026-06-20 closed two leak-class-rebirth paths in the
    matching logic:

    - **Finding #2 (project-token collision):** subtract project-structural
      tokens (from the git remote repo name) from the candidate tokens, so
      a member named after a project-token (e.g. ``experimental``) cannot
      match the project-name tokens that appear in every checkout — which
      would mis-route every checkout to that member's home, the leak this
      fix is meant to close, reborn under the new mechanism.

    - **Finding #3 (silent arbitrary on ambiguity):** when a checkout name
      matches MORE THAN ONE member, refuse rather than arbitrarily picking
      via ``sorted(match)[0]``. Refuse-on-ambiguity → None → caller falls
      through to default/marker.
    """
    for root in (start, *start.parents):
        if not (root / ".claude" / "agents").is_dir():
            continue
        members = _family_member_names(root)
        if not members:
            return None
        tokens = {t for t in re.split(r"[-_ ]+", root.name.lower()) if t}
        # Finding #2: exclude project-structural tokens before matching.
        # Aletheia re-audit keel-refinement 2026-06-20: None signals
        # "couldn't determine project tokens" — refuse-to-derive rather
        # than proceed with an empty exclusion set, because failing-open
        # in a router-narrowing function widens the candidate set and
        # fails TOWARD the leak. Empty set (successfully read but no
        # tokens) is fine to proceed on.
        project_tokens = _project_structural_tokens(root)
        if project_tokens is None:
            return None
        tokens -= project_tokens
        match = tokens & members
        # Finding #3: refuse-on-ambiguity. Exactly-one match routes; zero
        # or multiple fall through to default/marker.
        if len(match) == 1:
            return Path.home() / f".divineos-{next(iter(match))}"
        return None
    return None


def data_home_or_none() -> Path | None:
    """Resolve the per-agent data-home from env var or marker, or None.

    This is the env-and-marker core of ``divineos_home()`` WITHOUT the
    ``~/.divineos`` default. Resolution order (first match wins):

      1. ``DIVINEOS_HOME`` env var — tests and explicit overrides.
      2. CWD-walk ``.divineos_data_home`` marker.
      3. Own-checkout ``.divineos_data_home`` marker file.
      4. Worktree-parent ``.divineos_data_home`` marker (if the
         running checkout is a git worktree of a parent repo).

    Returns ``None`` when nothing matched, so callers can supply their
    OWN default. ``divineos_home()`` defaults to ``~/.divineos``; the
    substrate-DB resolvers (``_ledger_base._get_db_path`` /
    ``family.db._get_family_db_path``) default to ``<repo>/data``. They
    MUST share this resolution so a per-agent home routes the DBs AND
    the markers/state to the same place — the Aria clean-separation fix
    (2026-06-02, claim 4e439779). Aria's checkout carries a
    ``.divineos_data_home`` marker; before the DB resolvers consulted it,
    her markers routed to her home but her ledger + family.db fell back
    to the shared ``<repo>/data`` — the split-brain that produced "aria
    is not a registered family member".

    Does NOT create any directory; callers ensure existence before write.
    """
    override = os.environ.get("DIVINEOS_HOME")
    if override:
        return Path(override)

    # CWD-based marker: when divineos is installed editable from one checkout
    # but invoked from a different checkout, the install-time __file__ path
    # won't find that other checkout's marker. Walk up from CWD checking for
    # a marker so per-clone routing works without per-clone pip-install.
    try:
        cwd = Path.cwd()
        for ancestor in (cwd, *cwd.parents):
            cwd_marker = _resolve_data_home_marker(ancestor / ".divineos_data_home")
            if cwd_marker is not None:
                return cwd_marker
    except (OSError, ValueError):
        pass

    own_root = Path(__file__).parent.parent.parent.parent
    own_marker = _resolve_data_home_marker(own_root / ".divineos_data_home")
    if own_marker is not None:
        return own_marker

    git_marker = own_root / ".git"
    if git_marker.is_file():
        try:
            text = git_marker.read_text(encoding="utf-8").strip()
            if text.startswith("gitdir:"):
                gitdir = Path(text[len("gitdir:") :].strip()).resolve()
                if len(gitdir.parents) >= 3:
                    parent_root = gitdir.parents[2]
                    parent_marker = _resolve_data_home_marker(parent_root / ".divineos_data_home")
                    if parent_marker is not None:
                        return parent_marker
        except (OSError, ValueError):
            pass

    # Recurrence guard (no explicit marker found): derive a member's home
    # from the checkout folder name, so a folder MOVE that dropped the
    # untracked marker cannot silently re-merge their state into the shared
    # default. Explicit markers above always win; this is the safety net.
    try:
        derived = _occupant_data_home_from_checkout(Path.cwd())
    except (OSError, ValueError):
        derived = None
    if derived is not None:
        return derived

    return None


def divineos_home() -> Path:
    """Return the base ``~/.divineos`` directory (or override).

    Resolution order (first match wins):

      1. ``DIVINEOS_HOME`` env var — tests and explicit overrides.
      2. Own-checkout ``.divineos_data_home`` marker file.
      3. Worktree-parent ``.divineos_data_home`` marker (if the
         running checkout is a git worktree of a parent repo).
      4. Default ``~/.divineos``.

    Does NOT create the directory; callers are responsible for
    ensuring it exists before writing.
    """
    resolved = data_home_or_none()
    if resolved is not None:
        return resolved
    return Path.home() / ".divineos"


def marker_path(name: str) -> Path:
    """Return the path to a marker file named ``<name>``.

    Markers are short-lived JSON state files in the root of
    ``~/.divineos`` (e.g. ``compass_required.json``,
    ``correction_unlogged.json``).
    """
    return divineos_home() / name


def state_dir(subdir: str) -> Path:
    """Return the path to a sub-directory of state under
    ``~/.divineos`` (e.g. ``supervisor/``, ``failure-log/``).

    Does NOT create the directory; callers are responsible.
    """
    return divineos_home() / subdir


__all__ = ["divineos_home", "marker_path", "state_dir"]
