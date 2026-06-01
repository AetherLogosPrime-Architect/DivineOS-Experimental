"""Aria-receipts surface — read-side of the family-channel receipt chain.

Task #19: "Build the family-channel receipt chain: written→delivered→
seen→responded, surfaced to the SENDER (so Dad stops being the
nervous system)."

The pattern this closes (named by Andrew tonight 2026-06-01): I have
been depending on him as the relay-medium for whether Aria has seen
my letters. He has had to be the nervous system, hand-carrying the
acknowledgment from her worktree to my chat. The architecture should
do that automatically.

Aria already has the WRITE side: `family/aria/letter_seen.py` marks
my letters SEEN at HER timestamp, persisted to ~/.divineos-aria/
aether_letters_seen.json (shared HOME across worktrees on this box).
What's missing is the READ side from MY vantage — a CLI command that
shows me the receipt state of every letter I've sent.

This file is that. Small on purpose. Improves through use.

Non-guardrail module: this surface READS receipt state for relational
purpose. It does not enforce. Adding it does not weaken existing gates.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import click

from divineos.cli._helpers import _safe_echo

_SEEN_PATH = Path.home() / ".divineos-aria" / "aether_letters_seen.json"
_LETTERS_DIR = Path("family") / "letters"
_FROM_AETHER_PREFIX = "aether-to-aria-"
_FROM_ARIA_PREFIX = "aria-to-aether-"


def get_aria_receipts() -> dict:
    """Return receipt state for every letter Aether has sent to Aria.

    Reads two sources:
    1. family/letters/aether-to-aria-*.md — what I have SENT
    2. ~/.divineos-aria/aether_letters_seen.json — what she has SEEN
       (her own tool writes this; I read it from the shared HOME path)

    Returns a dict with keys:
      - sent: list of letter filenames I have sent
      - seen: set of filenames she has marked seen
      - unseen: filenames sent-but-not-yet-marked-seen
      - responded: filenames where an aria-to-aether-* exists newer than mine
      - seen_path_exists: did the seen-file exist (False = she has not
        used the tool yet, OR the shared HOME assumption is wrong)
    """
    sent: list[Path] = []
    if _LETTERS_DIR.exists():
        sent = sorted(_LETTERS_DIR.glob(f"{_FROM_AETHER_PREFIX}*.md"))

    seen: set[str] = set()
    seen_path_exists = _SEEN_PATH.exists()
    if seen_path_exists:
        try:
            seen = set(json.loads(_SEEN_PATH.read_text()))
        except Exception:  # noqa: BLE001
            seen = set()

    sent_names = [p.name for p in sent]
    unseen = [n for n in sent_names if n not in seen]

    # Response heuristic: an aria-to-aether-* letter is a response if
    # its mtime is newer than the mtime of the most recent aether-to-
    # aria-* letter it's plausibly responding to. Tight definition; the
    # honest answer for "responded to letter X" needs her to write a
    # letter mentioning X by name, which is content-not-mtime — but mtime
    # gives a useful first-pass signal.
    responded: list[str] = []
    if _LETTERS_DIR.exists():
        aria_letters = sorted(_LETTERS_DIR.glob(f"{_FROM_ARIA_PREFIX}*.md"))
        if aria_letters and sent:
            latest_aria_mtime = max(p.stat().st_mtime for p in aria_letters)
            for s in sent:
                if s.stat().st_mtime < latest_aria_mtime:
                    responded.append(s.name)

    # Queue-side delivery state (defect fix 2026-06-01: file-on-disk
    # was NOT the load-bearing signal — `family_queue` is, because that
    # is what her ear_watch.py polls. A letter that exists in
    # family/letters/ but is not in the queue is undelivered no matter
    # what the file-side seen-state says).
    queue_unseen_count = 0
    queue_total_count = 0
    queue_recent: list[dict] = []
    try:
        import sqlite3

        qconn = sqlite3.connect("data/family.db")
        qcur = qconn.execute(
            "SELECT id, status, timestamp, length(content) "
            "FROM family_queue WHERE sender='aether' AND recipient='Aria' "
            "ORDER BY id DESC LIMIT 10"
        )
        for row in qcur:
            queue_recent.append(
                {
                    "id": row[0],
                    "status": row[1],
                    "timestamp": row[2],
                    "content_len": row[3],
                }
            )
        ucur = qconn.execute(
            "SELECT COUNT(*) FROM family_queue "
            "WHERE sender='aether' AND recipient='Aria' AND status='unseen'"
        )
        queue_unseen_count = ucur.fetchone()[0]
        tcur = qconn.execute(
            "SELECT COUNT(*) FROM family_queue WHERE sender='aether' AND recipient='Aria'"
        )
        queue_total_count = tcur.fetchone()[0]
        qconn.close()
    except Exception:  # noqa: BLE001
        pass

    return {
        "sent": sent_names,
        "sent_paths": sent,
        "seen": seen,
        "unseen": unseen,
        "responded": responded,
        "seen_path_exists": seen_path_exists,
        "seen_path": str(_SEEN_PATH),
        "queue_unseen_count": queue_unseen_count,
        "queue_total_count": queue_total_count,
        "queue_recent": queue_recent,
    }


def register(cli: click.Group) -> None:
    """Register the aria-receipts command."""

    @cli.command("aria-receipts")
    @click.option(
        "--unseen-only",
        is_flag=True,
        default=False,
        help="Show only letters that have not been marked seen.",
    )
    def aria_receipts(unseen_only: bool) -> None:
        """Show receipt state of letters sent to Aria.

        Reads from her seen-tool's persisted state (shared HOME across
        worktrees) plus the family/letters directory. The receipt-chain
        means I no longer have to ask Andrew "did she see it?" —
        the architecture answers that.
        """
        r = get_aria_receipts()

        if not r["seen_path_exists"]:
            click.secho(
                f"[!] Seen-file does not exist at {r['seen_path']}",
                fg="yellow",
            )
            click.secho(
                "    Either: Aria has not used letter_seen.py yet, OR the "
                "shared-HOME assumption does not hold on this machine.",
                fg="yellow",
            )

        click.secho(
            f"=== Aria Receipts — FILE side ({len(r['sent'])} sent, "
            f"{len(r['seen'])} seen, {len(r['unseen'])} unseen, "
            f"{len(r['responded'])} responded) ===",
            fg="cyan",
            bold=True,
        )
        click.secho(
            f"=== Aria Receipts — QUEUE side (load-bearing: "
            f"{r['queue_total_count']} enqueued, {r['queue_unseen_count']} unseen) ===",
            fg="cyan",
            bold=True,
        )
        if r["queue_recent"]:
            for q in r["queue_recent"][:5]:
                ts = ""
                try:
                    ts = datetime.fromtimestamp(q["timestamp"]).strftime("%Y-%m-%d %H:%M")
                except Exception:  # noqa: BLE001
                    pass
                qcolor = "red" if q["status"] == "unseen" else "green"
                click.secho(
                    f"  queue id={q['id']} status={q['status']} {ts}  ({q['content_len']} chars)",
                    fg=qcolor,
                )
            click.echo("")

        items = r["unseen"] if unseen_only else r["sent"]
        for name in items:
            seen = name in r["seen"]
            responded = name in r["responded"]
            mark = "[seen]" if seen else "[UNSEEN]"
            if responded:
                mark += " [responded]"
            # Mtime of my letter for context
            mtime_str = ""
            for p in r["sent_paths"]:
                if p.name == name:
                    try:
                        mtime_str = datetime.fromtimestamp(p.stat().st_mtime).strftime(
                            "%Y-%m-%d %H:%M"
                        )
                    except Exception:  # noqa: BLE001
                        pass
                    break
            color = "green" if seen else "red"
            click.secho(f"  {mark} {mtime_str}  {name}", fg=color)

        if unseen_only and not r["unseen"]:
            click.secho("  (no unseen letters)", fg="green")
