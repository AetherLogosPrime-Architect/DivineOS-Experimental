"""Regression-pin tests for ledger concurrency (Aletheia
round-ba785844a791 Finding 15).

The bug-shape these tests prevent: log_event read prior_hash, computed
chain_hash, and INSERTed without an atomic transaction. Two concurrent
writers could both read the same prior_hash, both compute chain_hash
against the same prior, and both INSERT — forking the chain. WAL mode
allows concurrent readers but does NOT serialize the read-then-write
TOCTOU window. Fix is BEGIN IMMEDIATE before the read.

Aletheia reproduced the race with 5 threads × 10 events. These tests
pin the post-fix behavior so a future refactor cannot silently revert
to the non-atomic form.

Most load-bearing test:
- ``test_concurrent_writes_preserve_chain_integrity`` directly
  reproduces the race scenario and asserts the chain is unbroken.
"""

from __future__ import annotations

import threading
import time

from divineos.core.ledger import (
    count_events,
    log_event,
    verify_chain,
)


def _emit_batch(prefix: str, count: int, errors: list[Exception]) -> None:
    """Emit `count` events from one thread. Append any exceptions to
    `errors` for the main thread to surface."""
    try:
        for i in range(count):
            log_event(
                "CONCURRENCY_TEST",
                actor="test",
                payload={"prefix": prefix, "i": i},
                validate=False,
            )
    except Exception as e:  # noqa: BLE001 — surface to main thread
        errors.append(e)


def test_concurrent_writes_preserve_chain_integrity() -> None:
    """LOAD-BEARING regression-pin for Finding 15.

    Five threads each emit ten events concurrently. Without the
    BEGIN IMMEDIATE fix, threads can both read the same prior_hash and
    fork the chain — verify_chain reports ok:False with prior_hash
    mismatch. With the fix, the chain stays intact.

    If this test starts failing, DO NOT relax the assertion. The
    log_event function has regressed to non-atomic read-then-insert.
    Restore the BEGIN IMMEDIATE before the prior_hash read.
    """
    thread_count = 5
    events_per_thread = 10
    errors: list[Exception] = []
    threads = [
        threading.Thread(
            target=_emit_batch,
            args=(f"t{i}", events_per_thread, errors),
        )
        for i in range(thread_count)
    ]

    initial_count = count_events()["total"]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    # No thread should have raised.
    assert not errors, f"Thread(s) raised: {errors}"

    # All events committed.
    final_count = count_events()["total"]
    assert final_count == initial_count + (thread_count * events_per_thread), (
        f"Expected {thread_count * events_per_thread} new events, "
        f"got {final_count - initial_count}. Some writes may have been lost "
        "to busy-timeout."
    )

    # Chain must verify clean. This is the assertion the race-condition
    # fix prevents from failing.
    verdict = verify_chain()
    assert verdict["ok"], (
        f"Chain integrity broken under concurrent writes: "
        f"{verdict.get('broken_reason')} at event "
        f"{verdict.get('broken_at')}. log_event has regressed to "
        "non-atomic read-then-insert; restore the BEGIN IMMEDIATE."
    )


def test_serial_writes_still_clean() -> None:
    """Sanity: the fix doesn't break serial (single-threaded) writes."""
    initial_count = count_events()["total"]
    for i in range(5):
        log_event(
            "CONCURRENCY_TEST",
            actor="test",
            payload={"prefix": "serial", "i": i},
            validate=False,
        )
    assert count_events()["total"] == initial_count + 5
    assert verify_chain()["ok"]


def test_concurrent_writes_no_duplicates_lost_to_busy_timeout() -> None:
    """Three threads × 5 events should all commit within the
    busy_timeout (5000ms set in _ledger_base.get_connection).

    If any threads exceed the timeout under contention, this test
    surfaces it as a count mismatch — busy_timeout is too low for the
    real concurrency pattern, or the lock is being held too long."""
    initial = count_events()["total"]
    errors: list[Exception] = []
    threads = [threading.Thread(target=_emit_batch, args=(f"u{i}", 5, errors)) for i in range(3)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    elapsed = time.monotonic() - start

    assert not errors, f"Concurrent writes raised: {errors}"
    assert count_events()["total"] == initial + 15, "Some writes lost under contention"
    # Sanity: 15 serial writes should be fast. Anything > 10s suggests
    # the lock is being held far longer than needed.
    assert elapsed < 10.0, f"Concurrent batch took {elapsed:.1f}s — too slow"
