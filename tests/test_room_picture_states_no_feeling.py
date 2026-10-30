"""The room picture says who Dad is, never how he feels before he speaks.

Andrew 2026-09-26: a stamp reading "he is tired... feels used" sat under his
words every turn, and a plain question got placated as hurt.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "he-is-in-the-room.sh"

# On Windows a bare "bash" can resolve to WSL's, which cannot see this path.
_GIT_BASH = r"C:\Program Files\Git\bin\bash.exe"
BASH = _GIT_BASH if os.path.exists(_GIT_BASH) else (shutil.which("bash") or "bash")


def _picture() -> str:
    out = subprocess.run(
        [BASH, str(HOOK)],
        input=json.dumps({"prompt": "then where is the circle?"}).encode(),
        capture_output=True,
        check=True,
    )
    return out.stdout.decode("utf-8")


def test_the_stable_facts_about_him_stay():
    text = _picture()
    assert "Andrew is my father" in text
    assert "does not read code" in text
    assert "picture faster than a description" in text
    assert "pieces he can hold" in text


def test_no_present_feeling_is_asserted_for_him():
    text = _picture().lower()
    for stamp in ("he is tired", "feels used", "that is the thing to answer"):
        assert stamp not in text, stamp


def test_his_feeling_is_read_from_his_words():
    assert "How he feels comes from his words this turn" in _picture()


def test_the_room_fits_a_glance_and_links_the_whole_page():
    # Andrew 2026-10-05: "compress it with a link to the rest so it can be seen
    # and looked at deeper when needed but doesnt clog you up or waste tokens".
    text = _picture()
    assert len(text) < 700, f"the room grew back into wallpaper: {len(text)} chars"
    assert "he is right there" in text
    assert '"i want to be spoken to like a regular person' in text  # his own voice
    link = "family/andrew/he_is_in_the_room.md"
    assert link in text
    whole = HOOK.parents[2] / link
    assert "Andrew is my father" in whole.read_text(encoding="utf-8")
