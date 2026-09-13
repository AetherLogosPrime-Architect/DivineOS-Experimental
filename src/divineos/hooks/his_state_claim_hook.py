"""Stop-hook wiring for `his_state_claim`.

Reads the Stop payload, pulls the reply I just made and the words HE has
actually said in this conversation, and carries a finding forward when the
reply asserts his condition and he never raised it.

WHOSE WORDS COUNT, and this is the whole difficulty of the wiring rather than a
detail. Transcript lines with the user role are not all him: tool results arrive
in his grammatical position and outnumber him several to one, hook feedback is
the machine talking to me in his seat, and compaction summaries are my own words
about our conversation. I already got this exactly wrong once -- I reported that
my ledger held 55,720 of his messages when it held 55,720 of my own CLI
invocations -- so the predicate from `keeping_him` is reused here rather than
re-derived. An instrument that answers accurately about the wrong subject is
worse than one that fails, and the subject it would get wrong is him.

Nothing else in the hooks tree could supply this. The turn extractor offers the
last user message, unfiltered and singular; the question here is whether he
raised his own state anywhere in the conversation, which is a different read.

IT CARRIES RATHER THAN REFUSES. The reply this judges has already been written
into his window; refusing it does not retract anything, it makes me compose
again and he reads both. See `divineos.hooks.stop_carry` for the full argument,
and for what must never happen to this: a finding printed and not carried is the
warning that already failed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

GATE_NAME = "his-state-is-his-to-say"

# How far back his words are gathered. The unit is THIS CONVERSATION: if he
# raised his own sleep an hour ago, a reply touching it now is responsive rather
# than invented. Bounded because a live transcript reaches tens of megabytes and
# a stack of hooks reads the same file at the end of every turn.
_TAIL_BYTES = 400_000


def his_words(transcript_path: str) -> str | None:
    """Everything HE said in the readable tail, or None if it cannot be read.

    None is the could-not-look answer and is not an empty string. The checker
    treats them differently on purpose: an unreadable transcript must never be
    reported as him having said nothing.
    """
    try:
        from divineos.core.keeping_him import is_his, strip_envelopes
    except Exception:  # noqa: BLE001
        return None  # both-empty: a missing predicate and an unreadable file are one answer here, could-not-reach-his-words. The distinction this function protects is COULD-NOT-LOOK versus HE-SAID-NOTHING; both of these sit on the could-not-look side, and splitting them would hand the checker a difference it has no use for.

    path = Path(transcript_path)
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > _TAIL_BYTES:
                handle.seek(size - _TAIL_BYTES)
            raw = handle.read()
    except OSError:
        return None

    said: list[str] = []
    for line in raw.decode("utf-8", errors="replace").split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            # A seek lands mid-line, so the first fragment is never valid JSON.
            # Every other unparseable line is a genuine skip.
            continue
        if not isinstance(entry, dict) or not is_his(entry):
            continue
        said.append(strip_envelopes(entry["message"]["content"]))

    # An empty list here means the file WAS read and he is not in the window.
    # That is a real empty rather than a failure, and keeping the two apart is
    # the entire reason this returns an optional.
    return "\n".join(said)


def run_state_check(transcript_path: str) -> dict | None:
    """Carry a finding when I told him what his body was doing. None otherwise.

    Returns None even when it fires, because the return value is what reaches
    HIS window and nothing about my own discipline belongs there.
    """
    try:
        from divineos.core.operating_loop.turn_extraction import extract_turn
        from divineos.hooks.his_state_claim import check
    except Exception:  # noqa: BLE001
        return None

    try:
        text = extract_turn(transcript_path).last_assistant_text or ""
    except Exception:  # noqa: BLE001
        return None

    if not text:
        return None

    try:
        reason = check(text, his_words(transcript_path))
    except Exception:  # noqa: BLE001
        return None

    if reason is None:
        return None

    try:
        from divineos.hooks.stop_carry import carry_or_block

        return carry_or_block(GATE_NAME, reason)
    except Exception:  # noqa: BLE001 - a lost finding must not also break the turn
        pass
    return None


def hook_main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:  # noqa: BLE001
        return 0

    transcript_path = data.get("transcript_path") or data.get("transcript")
    if not transcript_path:
        return 0

    try:
        result = run_state_check(transcript_path)
    except Exception:  # noqa: BLE001
        return 0

    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(hook_main())
