"""A test that patches ``_ledger_base.DB_PATH`` must not leave the patch behind.

Found 2026-10-11 when a full pre-push run failed
``test_db_path_and_get_connection_agree_under_env_change`` and passed alone. Cause:
``DB_PATH`` on that module is served dynamically (PEP 562 ``__getattr__``), so
``monkeypatch.setattr`` reads the OLD value through the dynamic lookup, and its undo sets
that old value back as a REAL module attribute. A real attribute hides ``__getattr__`` for
every later test in the same worker, so a later test that changes ``DIVINEOS_DB`` and reads
``DB_PATH`` sees a stale path. It only fails when two particular tests meet in one worker
in one order, which is why it read as bad luck.

The two tests below are ordered on purpose: pytest runs a module's tests in definition
order, and the second one is the one that fails without the cleanup in ``conftest.py``.
"""

from __future__ import annotations

import divineos.core._ledger_base as lb


def test_first_a_patch_shadows_the_dynamic_lookup_while_it_lasts(tmp_path, monkeypatch):
    """CONTROL: proves the probe can see the shadow at all, so the next test is not
    passing because there was nothing to find."""
    monkeypatch.setattr(lb, "DB_PATH", tmp_path / "patched.db")
    assert "DB_PATH" in vars(lb)
    assert lb.DB_PATH == tmp_path / "patched.db"


def test_then_the_next_test_gets_the_dynamic_lookup_back(tmp_path, monkeypatch):
    assert "DB_PATH" not in vars(lb), (
        "a real DB_PATH attribute outlived the test that patched it and now hides the "
        "environment variable for every later test in this worker"
    )
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "from_env.db"))
    assert lb.DB_PATH == tmp_path / "from_env.db"
