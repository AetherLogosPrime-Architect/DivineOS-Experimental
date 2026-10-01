"""Real processes appending at the same instant never cross a link.

Aria, 2026-09-28: the writer chose its predecessor by timestamp while verify
walks rowid order, and log_event took its timestamp before BEGIN IMMEDIATE.
Across processes the two orders can disagree, so a row links to the
latest-by-clock row rather than the one appended just before it. Every one of
the 946 crossed links on Aether's real ledger fit that pattern exactly.

Threads cannot show it: the in-process lock serializes them (the threaded
test for the family-member ledger passes for that reason). This uses real
subprocesses released at the same moment, the way the table's children log
Dad's prompt.
"""

import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from divineos.core.ledger import init_db, verify_chain

ROOT = Path(__file__).resolve().parent.parent

WRITER = textwrap.dedent(
    """
    import sys, time
    from divineos.core.ledger import log_event
    start, n = float(sys.argv[1]), int(sys.argv[2])
    while time.time() < start:
        time.sleep(0.0005)
    for i in range(n):
        log_event("RACE_PROBE", "system", {"i": i}, validate=False)
    """
)


@pytest.mark.slow
def test_concurrent_processes_never_cross_a_link(tmp_path, monkeypatch):
    db = tmp_path / "race.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db))
    init_db()
    env = {**os.environ, "DIVINEOS_DB": str(db), "PYTHONPATH": str(ROOT / "src")}
    start = time.time() + 3.0
    procs = [
        subprocess.Popen([sys.executable, "-c", WRITER, str(start), "40"], env=env)
        for _ in range(6)
    ]
    for p in procs:
        assert p.wait(timeout=120) == 0
    chain = verify_chain()
    assert chain["ok"], chain
