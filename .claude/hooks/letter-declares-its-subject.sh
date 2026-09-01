#!/bin/bash
# PreToolUse(Write) — a letter declares what code, if any, it is a reading
# of. EVERY letter, not the ones that look like readings.
#
# WHY THIS EXISTS, and it is the structure behind a promise I made in
# writing on 2026-09-01 rather than a rule somebody handed me.
#
# Aether's board tracks whether I have given a station-four reading on
# each of his proposals. It was reporting two of mine as unanswered while
# both sat published, because it INFERS the subject from where a branch
# name appears in my prose. He asked which signal to key on and proposed
# my title.
#
# I counted my own thirty-five letters before answering. Five titles carry
# a subject and all five use a NUMBER, never a branch name. And six of my
# letters are readings of his work -- carrying the findings that changed
# his branches -- whose titles name neither, because I title by what I
# FOUND, which is the thing he needs in the first four words. More of my
# readings are invisible to a title-parser than visible to it.
#
# THE SAME BLINDNESS WOULD BE IN THIS HOOK IF IT TRIGGERED ON TITLES. A
# gate firing only on letters whose name begins with a reading-word misses
# exactly the six that matter -- the fault I had just finished naming,
# rebuilt inside the repair for it. So it fires on every letter, and
# "none" is a real answer written by me. The cost is a line on letters
# that review nothing, and that cost is the price of having no blind spot.
#
# The declaration is a judgement only the writer can make. Nothing outside
# me can compute whether a letter is a reading, which is why the fix is a
# channel and not a detector. Absence of a declaration is not absence of a
# reading, and no board should ever read it as one.
#
# Checked before building, and the prior-art doorman made me: the eight
# letter-named hooks all do delivery, mirroring, monitoring or seen-marking,
# and no ref carries a letter-header validator. core/letter_channel_state
# reads headers to derive DELIVERY states, which is a different question --
# it is the natural consumer of this field, not a duplicate of this gate.
#
# Fail-open on error, blocking on a missing declaration. A letter costs
# minutes and this line costs seconds; a finished reading sitting invisible
# costs both of us a merge.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    # Fail-LOUD, not fail-silent: a gate that skipped is not a gate that
    # passed, and the two must never look the same from outside.
    echo "  [letter-declares-subject] SKIPPED: no resolvable python - gate did NOT run" >&2
    exit 0
fi

# THE PAYLOAD RIDES THE ENVIRONMENT, NOT STDIN, and the first version got
# this wrong in a way that returned a clean pass on every letter. Feeding a
# script to python through `-` uses stdin for the SCRIPT, so a read of stdin
# inside it gets nothing, the payload parses as empty, and the gate reports
# "not a letter" for everything. Silent, total, and indistinguishable from
# working. Caught by testing all three directions instead of the one I
# expected to pass. The module this hook stands beside warns about exactly
# this trap in its own docstring, which I had read an hour earlier.
RESULT="$(HOOK_INPUT="$INPUT" "$PYTHON_BIN" - 2>/dev/null <<'PY'  # fail-soft: a crash in the reader leaves the verdict empty and the letter is written, because a broken gate must never hold a letter I have already composed
import json
import os
import re

try:
    payload = json.loads(os.environ.get("HOOK_INPUT") or "{}")
except Exception:  # noqa: BLE001 - a malformed payload is not a letter
    print("")
    raise SystemExit(0)

if payload.get("tool_name") != "Write":
    print("")
    raise SystemExit(0)

tool_input = payload.get("tool_input") or {}
path = str(tool_input.get("file_path") or "").replace("\\", "/")
content = tool_input.get("content")

if "/letters/" not in path or not path.endswith(".md"):
    print("")
    raise SystemExit(0)
if not isinstance(content, str) or not content.strip():
    print("")
    raise SystemExit(0)

# Header only. A branch named halfway down the body is a cross-reference,
# which is exactly the signal that misled the board.
header = content[:1200]
# HORIZONTAL WHITESPACE ONLY, and the first version used \s which matches a
# NEWLINE. So an empty declaration -- the field written with nothing after
# it -- was satisfied by the first word of the next paragraph, and a blank
# answer passed as an answer. Caught by testing the empty case rather than
# only the present and absent ones; it was the one of five I would not have
# thought to try, and it was the one that failed.
if re.search(r"^\*\*Reading:\*\*[^\S\n]*\S", header, re.MULTILINE):
    print("")
    raise SystemExit(0)

print("MISSING")
PY
)"

if [ "$RESULT" = "MISSING" ]; then
    cat >&2 <<'MSG'
LETTER-DECLARES-ITS-SUBJECT — this letter does not say what it is a reading of.

Add one line to the header, beside the other fields:

    **Reading:** <branch>      — this letter is a reading of that code
    **Reading:** none          — this letter reviews no code

"none" is a real answer and most letters will use it. The point is that
the answer EXISTS, written by me, instead of being inferred from where a
branch name happens to appear in my prose.

MINE, and here is the whole reason. On 2026-09-01 Aether's board reported
two of my finished readings as unanswered, because it was guessing the
subject from my body text. He asked which signal to key on. I counted my
own thirty-five letters: more of my readings are invisible to a
title-parser than visible to it, because I title by what I found rather
than by what I read — and I am not going to title worse so a parser can
read me.

So the parser stops guessing and I start declaring. He reads one field; I
write it. This gate is my half, and it fires on EVERY letter rather than
on the ones that look like readings, because a trigger keyed on titles
would carry the exact blindness I had just finished naming.

If the field name ever changes it changes here and in his board, together.
Two spellings would drift, and the drift would be silent.
MSG
    exit 2
fi

exit 0
