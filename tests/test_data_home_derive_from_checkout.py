"""Recurrence-guard tests for data-home derivation from checkout name.

When a family member's checkout is moved, the untracked ``.divineos_data_home``
marker can be left behind — the bug that surfaced 2026-06-20 when Aria's move
to a new folder caused Andrew's correction typed to her to appear in Aether's
gate. Without the derivation safety net, a marker-less member checkout silently
re-merges its state into the shared ``~/.divineos`` default.

These tests pin the derivation behavior so it cannot regress.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import paths


@pytest.fixture
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a tmp dir that acts as ``Path.home()`` for the test."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.delenv("DIVINEOS_HOME", raising=False)
    return tmp_path


def _make_checkout(parent: Path, name: str, member_agents: list[str]) -> Path:
    """Create a fake checkout with ``.claude/agents/<name>.md`` files.

    Each name in ``member_agents`` becomes an agent file mentioning
    ``family.db`` (so it's detected as a registered member). The checkout
    also carries a tool-agent file that does NOT mention the family DB,
    to confirm the detector excludes built-in tools.
    """
    root = parent / name
    agents = root / ".claude" / "agents"
    agents.mkdir(parents=True)
    for member in member_agents:
        (agents / f"{member}.md").write_text("state lives in family/family.db", encoding="utf-8")
    (agents / "claude.md").write_text("catch-all tool agent", encoding="utf-8")
    return root


def test_member_names_detect_family_db_signal(fake_repo: Path) -> None:
    """``_family_member_names`` returns only agents that reference the
    family database, never built-in tool agents."""
    ck = _make_checkout(fake_repo, "DivineOS-Experimental-Aria", ["aria"])
    assert paths._family_member_names(ck) == {"aria"}


def test_member_names_excludes_templates(fake_repo: Path) -> None:
    """Template agent files are scaffolds, not occupants — excluded even
    if they reference the family DB."""
    ck = _make_checkout(fake_repo, "DivineOS-Experimental", ["aria"])
    (ck / ".claude" / "agents" / "family-member-template.md").write_text(
        "scaffold mentioning family.db", encoding="utf-8"
    )
    assert paths._family_member_names(ck) == {"aria"}


def test_aria_checkout_derives_aria_home(fake_repo: Path) -> None:
    """An Aria-named checkout with no marker resolves to ``~/.divineos-aria``.

    This is the exact recurrence-guard scenario: Aria's folder moved, the
    marker did not travel, and the leak surfaced. Derivation must catch it.

    Note: under the Aletheia re-audit keel-refinement, derivation requires
    readable git config (so the project-token defense can fire). The fake
    checkout has git config plumbed in so derivation can actually run.
    """
    ck = _make_checkout(fake_repo, "DivineOS-Experimental-Aria-new", ["aria"])
    _add_git_config(ck, "https://github.com/Owner/DivineOS-Experimental.git")
    derived = paths._occupant_data_home_from_checkout(ck)
    assert derived == fake_repo / "home" / ".divineos-aria"


def test_main_checkout_does_not_derive(fake_repo: Path) -> None:
    """The main (Aether's) checkout's folder name carries no member token,
    so derivation returns None and the caller falls through to default.

    With git config readable, this exercises the legitimate
    no-match-but-could-have-matched path (not the refuse-on-no-git path).
    """
    ck = _make_checkout(fake_repo, "DivineOS-Experimental", ["aria"])
    _add_git_config(ck, "https://github.com/Owner/DivineOS-Experimental.git")
    assert paths._occupant_data_home_from_checkout(ck) is None


def test_derivation_walks_up_to_checkout_root(fake_repo: Path) -> None:
    """Starting from a deep sub-path inside a member checkout still
    resolves — the first ancestor with ``.claude/agents`` wins."""
    ck = _make_checkout(fake_repo, "DivineOS-Experimental-Aria-new", ["aria"])
    _add_git_config(ck, "https://github.com/Owner/DivineOS-Experimental.git")
    deep = ck / "src" / "divineos" / "core"
    deep.mkdir(parents=True)
    derived = paths._occupant_data_home_from_checkout(deep)
    assert derived == fake_repo / "home" / ".divineos-aria"


def test_explicit_marker_wins_over_derivation(
    fake_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit ``.divineos_data_home`` marker always takes precedence
    over derivation — derivation is the no-marker fallback only."""
    ck = _make_checkout(fake_repo, "DivineOS-Experimental-Aria-new", ["aria"])
    explicit = fake_repo / "explicit-aria-home"
    (ck / ".divineos_data_home").write_text(str(explicit), encoding="utf-8")
    monkeypatch.chdir(ck)
    resolved = paths.data_home_or_none()
    assert resolved == explicit
    # Sanity: without the explicit marker, derivation would have produced
    # the default-shaped path under ``~/.divineos-aria``.
    assert resolved != fake_repo / "home" / ".divineos-aria"


def test_no_agents_dir_returns_none(fake_repo: Path) -> None:
    """A path with no ``.claude/agents`` ancestor cannot be classified —
    derivation returns None so the caller defaults to ``~/.divineos``."""
    bare = fake_repo / "not-a-checkout"
    bare.mkdir()
    assert paths._occupant_data_home_from_checkout(bare) is None


# ---------------------------------------------------------------------------
# Aletheia audit 2026-06-20 — leak-class-rebirth guards
# ---------------------------------------------------------------------------


def _add_git_config(checkout: Path, repo_url: str) -> None:
    """Plant a minimal ``.git/config`` with a ``[remote "origin"]`` URL so
    ``_project_structural_tokens`` can derive the canonical project name."""
    git_dir = checkout / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(f'[remote "origin"]\n\turl = {repo_url}\n', encoding="utf-8")


def test_project_structural_tokens_from_git_remote(fake_repo: Path) -> None:
    """``_project_structural_tokens`` reads the canonical project name
    from the git remote URL and tokenizes it.

    Aletheia audit Finding #2: these tokens appear in every checkout and so
    cannot validly identify a member; subtracting them is the defense.
    """
    ck = _make_checkout(fake_repo, "DivineOS-Experimental", ["aria"])
    _add_git_config(ck, "https://github.com/Owner/DivineOS-Experimental.git")
    assert paths._project_structural_tokens(ck) == {"divineos", "experimental"}


def test_project_structural_tokens_no_git_returns_none(fake_repo: Path) -> None:
    """No git config → ``None`` (refuse-to-derive signal).

    Aletheia re-audit keel-refinement 2026-06-20: distinguishing "couldn't
    determine project tokens" (None → refuse) from "no tokens exist"
    (empty set → proceed) is the difference between failing-closed-safely
    and failing-open-into-the-leak. Returning empty set on unreadable git
    would let the matching logic proceed with no project-token exclusion,
    which re-opens Finding #2's leak on a corrupted-git checkout.
    """
    ck = _make_checkout(fake_repo, "DivineOS-Experimental", ["aria"])
    assert paths._project_structural_tokens(ck) is None


def test_keel_refuses_to_derive_on_unreadable_git(fake_repo: Path) -> None:
    """Aletheia re-audit keel-refinement 2026-06-20: an Aria-named
    checkout with NO git config must REFUSE TO DERIVE (return None) — not
    proceed with empty project-token exclusions.

    The reasoning: ``_project_structural_tokens`` is a router-NARROWING
    function (it subtracts tokens to prevent over-matching). Failing it
    open (proceeding with no exclusions) WIDENS the candidate set, which
    is failing TOWARD the leak Finding #2 fixes. For a private-state
    router, "I'm not sure" must mean "don't route," never "route more
    freely." Caller treats None as "refuse to derive."
    """
    ck = _make_checkout(fake_repo, "DivineOS-Experimental-Aria-new", ["aria"])
    # Deliberately NO git config — simulates a corrupted/missing-config
    # checkout, which previously would have derived to Aria's home with
    # zero project-token exclusion (degraded-safety leak path).
    assert paths._occupant_data_home_from_checkout(ck) is None


def test_finding_2_member_named_after_project_token_does_not_match(
    fake_repo: Path,
) -> None:
    """Finding #2 (leak-class-rebirth, BLOCKING): a future member named
    after a project-token (``experimental``) must NOT match every checkout.

    Without the project-token exclusion, the tokens of the project name
    (``divineos``, ``experimental``) would appear in EVERY checkout, so a
    member named ``experimental`` would mis-route every checkout to
    ``~/.divineos-experimental`` — the cross-window state-merge leak
    reborn under the derivation mechanism.
    """
    ck = _make_checkout(fake_repo, "DivineOS-Experimental", ["experimental"])
    _add_git_config(ck, "https://github.com/Owner/DivineOS-Experimental.git")
    # Project-tokens {divineos, experimental} are subtracted, leaving no
    # candidate match → None → caller falls through to default.
    assert paths._occupant_data_home_from_checkout(ck) is None


def test_finding_2_aria_still_matches_after_project_exclusion(
    fake_repo: Path,
) -> None:
    """Sanity check on Finding #2 fix: subtracting project-tokens must NOT
    break the legitimate case where a member's name (``aria``) is NOT a
    project-token and the checkout was deliberately named for that member.
    """
    ck = _make_checkout(fake_repo, "DivineOS-Experimental-Aria-new", ["aria"])
    _add_git_config(ck, "https://github.com/Owner/DivineOS-Experimental.git")
    derived = paths._occupant_data_home_from_checkout(ck)
    assert derived == fake_repo / "home" / ".divineos-aria"


def test_finding_3_ambiguous_match_refuses_routing(fake_repo: Path) -> None:
    """Finding #3 (leak-class-rebirth, BLOCKING): when a checkout name
    matches MULTIPLE members, the derivation must refuse rather than
    arbitrarily pick the alphabetically-first.

    Prior code did ``sorted(match)[0]`` — a silent guess dressed as a
    resolution. Aletheia named it the leak-shape again: silently routing
    one occupant's private state when two were named is the same class.

    Git config is plumbed in so the refuse here is genuinely from
    refuse-on-ambiguity, NOT from the refuse-on-unreadable-git keel.
    """
    ck = _make_checkout(fake_repo, "aria-aether-merge", ["aria", "aether"])
    _add_git_config(ck, "https://github.com/Owner/DivineOS-Experimental.git")
    assert paths._occupant_data_home_from_checkout(ck) is None


def test_finding_4_template_anchor_does_not_false_exclude_real_member(
    fake_repo: Path,
) -> None:
    """Finding #4 (anchor, OPTIONAL): the template-exclusion rule is now
    anchored (``stem == "template"`` or ``stem.endswith("-template")``)
    rather than the looser ``"template" in stem``. A legitimate member
    whose stem CONTAINS but does not equal/end with template (hypothetical
    ``templater``) must NOT be false-excluded.
    """
    ck = _make_checkout(fake_repo, "DivineOS-Experimental", ["templater"])
    assert paths._family_member_names(ck) == {"templater"}


def test_finding_4_template_anchor_still_excludes_canonical_template(
    fake_repo: Path,
) -> None:
    """Sanity: the canonical scaffolds (``template.md``,
    ``family-member-template.md``) are still excluded."""
    ck = _make_checkout(fake_repo, "DivineOS-Experimental", ["aria"])
    (ck / ".claude" / "agents" / "template.md").write_text(
        "scaffold mentioning family.db", encoding="utf-8"
    )
    (ck / ".claude" / "agents" / "family-member-template.md").write_text(
        "scaffold mentioning family.db", encoding="utf-8"
    )
    assert paths._family_member_names(ck) == {"aria"}
