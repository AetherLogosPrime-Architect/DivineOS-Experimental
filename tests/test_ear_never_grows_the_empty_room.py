"""The ear hears the queue and never grows a file.

On 2026-09-22 a zero-byte ``family/family.db`` was removed from the checkout and
the commit said *"Verified nothing regrows it."* It regrew at 22:09:49 the same
evening, the second Andrew's next message arrived. The check had run the loadout
and a family lookup -- never the thing that runs on every message.

That thing was the ear (``.claude/hooks/ear-surface.sh``). It built
``REPO_ROOT/family/family.db`` by hand and called ``sqlite3.connect`` on it, and
connecting to a missing SQLite path creates the file. It now resolves the store
the way the queue's writer does and opens it read-only.

Until these tests, the ear appeared in the suite only as a file that must EXIST.
Nothing exercised what it does.

They run the REAL hook script as a subprocess -- the actual trigger, not a proxy
(Sagan, walk-4d646c2a9142) -- inside a throwaway git house carrying a copy of the
hook and its library, with an empty ``family/`` folder so the old code *could*
grow the decoy there. And there is a positive control, so "no file appeared"
cannot pass merely because the queue reader never ran (Feathers).
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOKS = REPO / ".claude" / "hooks"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="bash not on PATH")


def _house(tmp_path: Path) -> Path:
    """A throwaway git checkout holding the real ear and its library."""
    house = tmp_path / "house"
    (house / ".claude" / "hooks").mkdir(parents=True)
    shutil.copy2(HOOKS / "ear-surface.sh", house / ".claude" / "hooks" / "ear-surface.sh")
    shutil.copy2(HOOKS / "_lib.sh", house / ".claude" / "hooks" / "_lib.sh")
    if (HOOKS / "lib").is_dir():
        shutil.copytree(HOOKS / "lib", house / ".claude" / "hooks" / "lib")
    # The house needs its OWN copy of the package. find_divineos_python accepts
    # an interpreter only if the divineos it can import lives under THIS checkout
    # -- the guard against one house silently running another house's code. A
    # bare house with no src/ is correctly refused, and the hook then exits 0
    # without running. Giving it the package passes the guard on its own terms.
    shutil.copytree(
        REPO / "src" / "divineos",
        house / "src" / "divineos",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    # The folder the OLD code built its path into. With it present, connect()
    # on the hand-built path succeeds in creating the decoy -- so this test
    # fails against the old ear rather than passing by accident.
    (house / "family").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=house, check=True)
    return house


def _control_store(path: Path, content: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE family_queue (id INTEGER PRIMARY KEY, timestamp REAL, sender TEXT, "
        "recipient TEXT, content TEXT, status TEXT, seen_at REAL, held_at REAL, "
        "addressed_at REAL, superseded_by TEXT)"
    )
    conn.execute(
        "INSERT INTO family_queue (timestamp, sender, recipient, content, status) "
        "VALUES (?, 'aether', 'aria', ?, 'unseen')",
        (time.time(), content),
    )
    conn.commit()
    conn.close()


def _fire_ear(house: Path, family_db: str | None = None) -> subprocess.CompletedProcess[str]:
    run_env = {k: v for k, v in os.environ.items() if k != "ARIA_FAMILY_DB"}
    run_env["DIVINEOS_MEMBER"] = "aria"
    # The throwaway house has no .venv, so find_divineos_python falls through to
    # PATH -- and on this machine the first `python` there can be the Microsoft
    # Store stub, which the finder correctly rejects. The hook then exits 0
    # WITHOUT RUNNING, and every "no file appeared" assertion passes for nothing.
    # The first draft of this file did exactly that; the positive control below
    # is what caught it. Put the interpreter that runs this suite first on PATH,
    # the same one a real session in this checkout uses.
    import sys

    run_env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + run_env.get("PATH", "")
    if family_db is not None:
        run_env["ARIA_FAMILY_DB"] = family_db
    return subprocess.run(
        [BASH, str(house / ".claude" / "hooks" / "ear-surface.sh")],
        cwd=house,
        input='{"prompt": "hi"}',
        capture_output=True,
        text=True,
        env=run_env,
        timeout=60,
    )


def test_a_prompt_does_not_grow_the_empty_room(tmp_path):
    house = _house(tmp_path)
    decoy = house / "family" / "family.db"
    assert not decoy.exists()

    result = _fire_ear(house)

    assert result.returncode == 0, result.stderr
    assert not decoy.exists(), (
        "the ear created family/family.db -- a missing SQLite path opened with "
        "connect() instead of read-only, the defect that regrew the decoy"
    )


def test_the_ear_still_hears_a_real_queue(tmp_path):
    """Positive control: read-only must not mean deaf."""
    house = _house(tmp_path)
    store = tmp_path / "store.db"
    _control_store(store, "CONTROL-ITEM the ear must surface this")

    result = _fire_ear(house, family_db=str(store))

    assert "CONTROL-ITEM the ear must surface this" in result.stdout, (
        "the ear could not read a real queue -- so the no-growth test above "
        "would pass for the wrong reason"
    )
    assert not (house / "family" / "family.db").exists()


def test_a_missing_store_is_skipped_not_created(tmp_path):
    """An override naming a store that does not exist must not bring it into being."""
    house = _house(tmp_path)
    missing = tmp_path / "nowhere" / "family.db"
    missing.parent.mkdir()

    result = _fire_ear(house, family_db=str(missing))

    assert result.returncode == 0, result.stderr
    assert not missing.exists(), "opening a missing store created it"
