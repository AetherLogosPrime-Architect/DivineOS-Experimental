"""Settings for the link that listens to our own words (design note 2026-11-08, points 2, 3, 7 and 10).

One small file, `.claude/own_words_link.json`, read at run time so a value can change without touching code: the mode
(off | log | block), the chunk rule for what text of a Write is searched (first | last | per_paragraph, plus a token
count), and for EVERY lane of the memory retriever, how a hit in that lane is cleared. A value that is not one of the
allowed ones fails loudly; nothing falls back to a default, because a silent fallback is a lane that is open by
accident.

A lane with `undefined_placeholder` is a lane nobody has named a door for yet. The non-strict check names it and passes
(log-only mode needs to run while the doors are being named); the strict check, which the block mode requires, fails on
it. So a lane can never be silently open in block mode.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

MODES = ("off", "log", "block")
CHUNK_RULES = ("first", "last", "per_paragraph")
CLEAR_KINDS = ("read_file", "show_command", "shown_plain", "undefined_placeholder")
EMBEDDER_TOKENS = 256

SETTINGS_FILE = Path(__file__).resolve().parents[3] / ".claude" / "own_words_link.json"


class SettingsError(ValueError):
    """A setting is missing or not one of the allowed values."""


def load(path: Path | None = None) -> dict:
    # OWN_WORDS_LINK_SETTINGS lets a test run the real hook against a temporary file; nothing else sets it.
    path = path or Path(os.environ.get("OWN_WORDS_LINK_SETTINGS") or SETTINGS_FILE)
    try:
        cfg: dict = json.loads(path.read_text(encoding="utf-8"))
        return cfg
    except (OSError, ValueError) as exc:
        raise SettingsError(f"could not read the own-words-link settings at {path}: {exc}") from exc


def validate(cfg: dict, lanes: set[str] | None = None, strict: bool = False) -> list[str]:
    """Raise SettingsError for any bad value. Return the sorted lanes whose clear is still a placeholder.

    ``lanes`` is the set of lanes the retriever actually has: every one must have a clear. ``strict`` makes a
    placeholder an error too (block mode needs every door named)."""
    if cfg.get("mode") not in MODES:
        raise SettingsError(f"mode must be one of {MODES}; got {cfg.get('mode')!r}")
    if cfg.get("chunk_rule") not in CHUNK_RULES:
        raise SettingsError(
            f"chunk_rule must be one of {CHUNK_RULES}; got {cfg.get('chunk_rule')!r}"
        )
    tokens = cfg.get("chunk_tokens")
    if (
        isinstance(tokens, bool)
        or not isinstance(tokens, int)
        or not 32 <= tokens <= EMBEDDER_TOKENS
    ):
        # The embedder (all-MiniLM-L6-v2) reads 256 tokens and ignores the rest, measured by Aria 2026-11-08, so a larger
        # value would claim to search text that was never read.
        raise SettingsError(
            f"chunk_tokens must be an integer from 32 to {EMBEDDER_TOKENS}; got {tokens!r}"
        )
    clears = cfg.get("lane_clears")
    if not isinstance(clears, dict):
        raise SettingsError("lane_clears must name a clear for every lane")
    if lanes is not None:
        missing = sorted(lanes - set(clears))
        if missing:
            raise SettingsError(f"no clear defined for lane(s): {', '.join(missing)}")
    for lane, clear in clears.items():
        if not isinstance(clear, dict) or clear.get("kind") not in CLEAR_KINDS:
            raise SettingsError(f"lane {lane!r}: clear kind must be one of {CLEAR_KINDS}")
        # 'shown_plain' is a decision that a lane has no door: a hit is shown and never held. It is not a gap, so it is
        # not a placeholder, and it must say why so nobody reads it as a door that was forgotten.
        if clear["kind"] == "shown_plain" and not str(clear.get("reason", "")).strip():
            raise SettingsError(f"lane {lane!r}: shown_plain needs a reason for having no door")
        if clear["kind"] == "show_command" and "{hit_id}" not in str(clear.get("command", "")):
            raise SettingsError(
                f"lane {lane!r}: show_command needs a command containing the {{hit_id}} slot"
            )
    placeholders = sorted(
        lane for lane, c in clears.items() if c["kind"] == "undefined_placeholder"
    )
    if strict and placeholders:
        raise SettingsError(f"lane(s) with no door named yet: {', '.join(placeholders)}")
    return placeholders
