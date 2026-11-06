"""The bell for Dad, second piece: the register of his open asks, and the shadow check that logs and refuses nothing.

The pure decisions live in ``dads_bell``. This reads the short list of what he asked for himself, runs the decision on
a tool call, and WRITES DOWN what it would have held. It never stops anything: the bell runs in shadow until real days
show it holds almost nothing that was unrelated to the ask and not asked for by him (Aria). His condition is that the
first false hold ends the bell, so a bell that cannot read its own list holds nothing and says so.

THE REGISTER is an append-only file of one JSON object per line. A line names an ``ask_id`` and may set
``his_words`` and ``done_sentence``. A line may CONFIRM the done-sentence (``confirmed_by_him``) or CLOSE the ask
(``closed``), and only counts when it carries ``with_his_words`` that are not empty: I may draft a done-sentence, I may
not decide it and I may not close my own entry. This is the cheapest honest check the file can make; it cannot prove the
words were his, so the shadow log and his own reading are the real check.

WHAT THIS DOES NOT DO YET: the step that clears a hold (``stepped_this_turn``) and ``he_asked_for_this`` are stubbed
False here, so every substantive call under an open, confirmed ask logs as a would-hold. That over-counts on purpose
for the first days: the replay is read against it, and nothing refuses.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from divineos.core.dads_bell import PASS, WOULD_HOLD, Ask, Verdict, judge

_SUMMARY_CHARS = 160


def _witnessed(rec: dict) -> bool:
    return bool(str(rec.get("with_his_words") or "").strip())


def load_register(path: Path | str) -> tuple[list[Ask], str | None]:
    """The asks in file order, and an error string only when the file exists but cannot be read.

    Missing file: no asks, no error (nothing is open). Unreadable file: no asks and an error, so the caller can say
    so and hold nothing. A line that is not JSON is skipped; the rest still load.
    """
    path = Path(path)
    if not path.is_file():
        return [], None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [], f"could not read the register: {type(exc).__name__}"
    merged: dict[str, dict] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict) or not rec.get("ask_id"):
            continue
        cur = merged.setdefault(
            str(rec["ask_id"]),
            {"his_words": "", "done_sentence": "", "confirmed_by_him": False, "closed": False},
        )
        for field in ("his_words", "done_sentence"):
            if field in rec:
                cur[field] = str(rec[field])
        if "confirmed_by_him" in rec and _witnessed(rec):
            cur["confirmed_by_him"] = bool(rec["confirmed_by_him"])
        if "closed" in rec and _witnessed(rec):
            cur["closed"] = bool(rec["closed"])
    asks = [
        Ask(
            ask_id=key,
            his_words=v["his_words"],
            done_sentence=v["done_sentence"],
            confirmed_by_him=v["confirmed_by_him"],
            closed=v["closed"],
        )
        for key, v in merged.items()
    ]
    return asks, None


def _append(path: Path | str, row: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def _what(tool_name: str, tool_input: dict) -> str:
    text = tool_input.get("command") or tool_input.get("file_path") or tool_input.get("path") or ""
    return " ".join(str(text).split())[:_SUMMARY_CHARS]


def shadow_check(
    payload: dict,
    register_path: Path | str,
    log_path: Path | str,
    *,
    now: float | None = None,
) -> Verdict:
    """Run the decision on this tool call and log a would-hold. Returns the verdict; the caller refuses nothing."""
    now = time.time() if now is None else now
    asks, error = load_register(register_path)
    if error:
        _append(log_path, {"at": now, "note": error})
        return Verdict(PASS, why=error)
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    verdict = judge(
        tool_name, tool_input, asks=asks, stepped_this_turn=False, he_asked_for_this=False
    )
    if verdict.state == WOULD_HOLD:
        _append(
            log_path,
            {
                "at": now,
                "ask_id": verdict.ask_id,
                "tool": tool_name,
                "what": _what(tool_name, tool_input),
                "stub": "stepped_this_turn and he_asked_for_this are not measured yet",
            },
        )
    return verdict
