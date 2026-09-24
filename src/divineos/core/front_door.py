"""The front door: every message he types is kept before anything else happens.

Andrew, 2026-09-24: the inspector stood at the workshop door and woke on our
hands touching a file; nothing stood where he speaks. This is what stands there.
The record it writes is ``his_asks`` (one store, both seats). This module only
does the two things a door does: keep what came in, and find out whether it was
him.

Two steps, because the platform forces them (measured 2026-09-24, see the design
doc's platform section): when he hits enter the hook gets ``prompt_id`` and the
words, but his record is not in the transcript yet. So the door keeps a
CANDIDATE, and the first time a later hook can see the transcript, ``settle``
reads the record carrying that ``promptId`` and hands the harness's own
``origin.kind`` stamp to ``his_asks.confirm``. Nothing here decides who spoke
by reading the words.

A failure to keep his message never costs him his reply. It is recorded as
could-not-file, loudly, and the prompt goes through.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from divineos.core import his_asks

# The record is written the moment he sends, so by the first tool call or the
# end of the turn it sits near the end of the transcript. Reading only the tail
# keeps this cheap on every tool call; a candidate whose record is not in the
# tail stays a candidate, and an unsettled candidate is counted as could-not-file.
_TAIL_BYTES = 4 * 1024 * 1024


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _loud(message: str) -> None:
    print(f"[front-door] {message}", file=sys.stderr)


def keep(payload: dict, seat: str) -> str | None:
    """Keep what arrived at the door. Returns the prompt id kept, or None.

    Called from UserPromptSubmit with the harness payload. Never raises: the
    prompt goes through whatever happens here.
    """
    prompt_id = str(payload.get("prompt_id") or "")
    text = str(payload.get("prompt") or "")
    if not text.strip():
        return None
    try:
        his_asks.file_candidate(prompt_id, text, _now_iso(), seat)
        return prompt_id
    except Exception as exc:  # his reply must not depend on this write
        _record_failure(prompt_id or "(no prompt id)", exc, seat)
        return None


def _record_failure(ref: str, exc: BaseException, seat: str) -> None:
    error = f"{type(exc).__name__}: {exc}"
    try:
        his_asks.could_not_file(ref, error, seat)
    except Exception as second:
        _loud(f"could not keep his message ({error}) and could not record that ({second!r})")
        return
    _loud(f"could not keep his message: {error}")


def _record_text(rec: dict) -> str:
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(b.get("text", ""))
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _prompt_records(transcript_path: Path, wanted: set[str]) -> dict[str, dict]:
    """The record that carries each wanted promptId, read from the tail.

    Only the record the prompt itself made has an ``origin``; tool results and
    hook feedback share its promptId but not that field.
    """
    try:
        size = transcript_path.stat().st_size
        with open(transcript_path, "rb") as fh:
            if size > _TAIL_BYTES:
                fh.seek(size - _TAIL_BYTES)
                fh.readline()  # the seek lands mid-line
            raw = fh.read()
    except OSError:
        return {}
    found: dict[str, dict] = {}
    for line in raw.decode("utf-8", errors="replace").splitlines():
        if '"promptId"' not in line or '"origin"' not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        pid = rec.get("promptId")
        if rec.get("type") == "user" and pid in wanted and "origin" in rec:
            found.setdefault(pid, rec)
    return found


def settle(transcript_path: str | Path, seat: str) -> dict[str, str] | None:
    """Confirm or withdraw every candidate whose record is now in the transcript.

    Returns ``{prompt_id: state}`` for the ones settled this call, or None when
    the store could not be read. Candidates from the other seat are never in
    this transcript and are left for that seat to settle.
    """
    open_ids = his_asks.unsettled()
    if open_ids is None:
        _loud("his record could not be read, so nothing was settled")
        return None
    if not open_ids:
        return {}
    records = _prompt_records(Path(transcript_path), set(open_ids))
    settled: dict[str, str] = {}
    for pid, rec in records.items():
        kind = str((rec.get("origin") or {}).get("kind") or "unstamped")
        try:
            settled[pid] = his_asks.confirm(
                pid, str(rec.get("uuid") or ""), kind, _record_text(rec)
            )
        except Exception as exc:
            _record_failure(pid, exc, seat)
    return settled
