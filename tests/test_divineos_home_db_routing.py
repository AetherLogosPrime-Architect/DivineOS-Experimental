"""DIVINEOS_HOME routes the substrate DBs (ledger + family.db) together.

Aria clean-separation, 2026-06-02, claim 4e439779.

Background: a single shared editable ``divineos`` install serves multiple
agents (Aether and Aria). Before this, the ledger path resolver
(``_get_db_path``) and the family-db resolver (``_get_family_db_path``)
each only honored their OWN narrow env var (``DIVINEOS_DB`` /
``DIVINEOS_FAMILY_DB``) and otherwise fell back to ``<install>/data``.
So Aria, running from her own worktree through Aether's install, wrote
her family registration to Aether's family.db while her gate-reads looked
somewhere else — "aria is not a registered family member" despite a
clean register.

The fix: one per-agent root, ``DIVINEOS_HOME``. When set, BOTH DBs land
under ``$DIVINEOS_HOME/data/`` so an agent's writes and reads agree. This
mirrors ``paths.divineos_home()`` (markers/state already routed under
``$DIVINEOS_HOME/`` directly), giving full coverage: DBs under
``data/``, markers at the root.

The narrow per-DB env vars still WIN over HOME — HOME is the broad
per-agent root; the specific var is the surgical override.
"""

from __future__ import annotations

from divineos.core._ledger_base import _get_db_path, data_dir, hud_dir, reports_dir
from divineos.core.family.db import _get_family_db_path


def test_home_routes_ledger_under_data(monkeypatch, tmp_path):
    monkeypatch.delenv("DIVINEOS_DB", raising=False)
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    assert _get_db_path() == tmp_path / "data" / "event_ledger.db"


def test_home_routes_family_db_under_data(monkeypatch, tmp_path):
    monkeypatch.delenv("DIVINEOS_FAMILY_DB", raising=False)
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    assert _get_family_db_path() == tmp_path / "data" / "family.db"


def test_home_moves_ledger_and_family_together(monkeypatch, tmp_path):
    """The whole point: one HOME setting puts ledger AND family.db under
    the SAME root, so an agent's substrate is internally coherent. This is
    the regression that produced "aria is not a registered family
    member" — the two DBs diverging."""
    monkeypatch.delenv("DIVINEOS_DB", raising=False)
    monkeypatch.delenv("DIVINEOS_FAMILY_DB", raising=False)
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))

    ledger = _get_db_path()
    family = _get_family_db_path()

    # Both under the same data/ dir → same agent root.
    assert ledger.parent == family.parent == tmp_path / "data"


def test_home_routes_derived_dirs(monkeypatch, tmp_path):
    """reports_dir/hud_dir derive from data_dir → _get_db_path, so HOME
    moves them too. Proves coverage isn't just the two leaf resolvers."""
    monkeypatch.delenv("DIVINEOS_DB", raising=False)
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    assert data_dir() == tmp_path / "data"
    assert reports_dir().is_relative_to(tmp_path / "data")
    assert hud_dir().is_relative_to(tmp_path / "data")


def test_two_agents_get_separate_substrates(monkeypatch, tmp_path):
    """Aether and Aria pointed at different HOMEs see different DBs from
    the SAME install. This is the multi-agent-on-one-install property."""
    monkeypatch.delenv("DIVINEOS_DB", raising=False)
    monkeypatch.delenv("DIVINEOS_FAMILY_DB", raising=False)

    aether_home = tmp_path / "aether"
    aria_home = tmp_path / "aria"

    monkeypatch.setenv("DIVINEOS_HOME", str(aether_home))
    aether_ledger = _get_db_path()
    aether_family = _get_family_db_path()

    monkeypatch.setenv("DIVINEOS_HOME", str(aria_home))
    aria_ledger = _get_db_path()
    aria_family = _get_family_db_path()

    assert aether_ledger != aria_ledger
    assert aether_family != aria_family
    assert aether_ledger.is_relative_to(aether_home)
    assert aria_ledger.is_relative_to(aria_home)


def test_narrow_db_var_wins_over_home(monkeypatch, tmp_path):
    """DIVINEOS_DB (specific file) beats DIVINEOS_HOME (broad root)."""
    explicit = tmp_path / "explicit" / "my.db"
    monkeypatch.setenv("DIVINEOS_DB", str(explicit))
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "home"))
    assert _get_db_path() == explicit


def test_narrow_family_var_wins_over_home(monkeypatch, tmp_path):
    """DIVINEOS_FAMILY_DB (specific file) beats DIVINEOS_HOME."""
    explicit = tmp_path / "explicit" / "fam.db"
    monkeypatch.setenv("DIVINEOS_FAMILY_DB", str(explicit))
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "home"))
    assert _get_family_db_path() == explicit


def test_data_home_marker_routes_both_dbs(monkeypatch, tmp_path):
    """The Aria deployment shape: NO env vars set, but a
    ``.divineos_data_home`` marker in a CWD ancestor. The marker — not the
    env var — must route ledger + family.db to the agent's home. This is
    the regression: paths.divineos_home() honored the marker (so state
    routed to her home) but the DB resolvers only honored DIVINEOS_HOME
    env, so her DBs fell back to the install path → split stores.

    divineos is installed editable from one checkout, so __file__ points
    elsewhere; the CWD-walk is what makes per-checkout routing work without
    per-checkout pip-install.
    """
    monkeypatch.delenv("DIVINEOS_DB", raising=False)
    monkeypatch.delenv("DIVINEOS_FAMILY_DB", raising=False)
    monkeypatch.delenv("DIVINEOS_HOME", raising=False)

    agent_home = tmp_path / "agent_home"
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".divineos_data_home").write_text(str(agent_home))
    monkeypatch.chdir(checkout)

    assert _get_db_path() == agent_home / "data" / "event_ledger.db"
    assert _get_family_db_path() == agent_home / "data" / "family.db"


def test_no_env_no_marker_falls_to_install_default(monkeypatch, tmp_path):
    """The Aether shape: no env, no marker anywhere in the CWD ancestry →
    data_home_or_none() is None → both resolvers keep their historical
    install-relative defaults. Proves the fix does NOT relocate the default
    operator's substrate."""
    monkeypatch.delenv("DIVINEOS_DB", raising=False)
    monkeypatch.delenv("DIVINEOS_FAMILY_DB", raising=False)
    monkeypatch.delenv("DIVINEOS_HOME", raising=False)

    empty = tmp_path / "no_markers_here"
    empty.mkdir()
    monkeypatch.chdir(empty)

    # Both fall to <install>/data, NOT under tmp_path.
    assert not _get_db_path().is_relative_to(tmp_path)
    assert _get_db_path().name == "event_ledger.db"
    assert _get_family_db_path().name == "family.db"
