#!/bin/bash
# UserPromptSubmit + SessionStart hook — auto-surface unseen queue items and
# unseen letters from the spouse, for whichever family member's window this
# is firing in. Parameterized to match ear_watch.py + ear-auto-relaunch.sh.
#
# Member detection: $DIVINEOS_MEMBER first, then cwd-substring fallback
# (DivineOS-Experimental-Aria -> aria, else aether).
#
# Fail-open: any error exits 0 silently.

cat >/dev/null 2>&1

MEMBER="${DIVINEOS_MEMBER:-}"
if [ -z "$MEMBER" ]; then
  case "$(pwd)" in
    *DivineOS-Experimental-Aria*) MEMBER=aria ;;
    *) MEMBER=aether ;;
  esac
fi

PY="$(command -v python 2>/dev/null || command -v python3 2>/dev/null)"
[ -z "$PY" ] && exit 0

MEMBER="$MEMBER" PYTHONIOENCODING="utf-8" "$PY" - <<'PYEOF'
import json
import os
import re
import sqlite3
from pathlib import Path

# Spouse table mirrors family/ear_watch.py — keep in sync if extended.
SPOUSE = {"aria": "aether", "aether": "aria"}

member = (os.environ.get("MEMBER") or "aria").lower()
spouse = SPOUSE.get(member, "aether")

db = os.environ.get(
    f"{member.upper()}_FAMILY_DB",
    r"C:/DIVINE OS/DivineOS-Experimental/data/family.db",
)
queue_rows = []
try:
    conn = sqlite3.connect(db)
    queue_rows = conn.execute(
        "SELECT id, sender, content FROM family_queue "
        "WHERE LOWER(recipient)=? AND status='unseen' ORDER BY id",
        (member,),
    ).fetchall()
    conn.close()
except Exception:
    queue_rows = []

letters_dir = Path(
    os.environ.get(
        f"{member.upper()}_LETTERS_DIR",
        r"C:/DIVINE OS/DivineOS-Experimental/family/letters",
    )
)
seen_path = Path.home() / f".divineos-{member}" / f"{spouse}_letters_seen.json"
unseen_letters = []
try:
    seen = set()
    if seen_path.exists():
        try:
            seen = set(json.loads(seen_path.read_text()))
        except Exception:
            seen = set()
    if letters_dir.exists():
        pat = re.compile(rf"^{spouse}-to-{member}-\d{{4}}-\d{{2}}-\d{{2}}.*\.md$")
        for p in sorted(letters_dir.iterdir()):
            if pat.match(p.name) and p.name not in seen:
                unseen_letters.append(p.name)
except Exception:
    unseen_letters = []

total = len(queue_rows) + len(unseen_letters)
if total:
    print("## INCOMING — %d unseen (auto-surfaced ear, no arming)" % total)
    print()
    if queue_rows:
        print("Queue (%d):" % len(queue_rows))
        for rid, sender, content in queue_rows:
            preview = (content or "").replace("\n", " ")[:100]
            print("  #%s from %s: %s" % (rid, sender, preview))
        print()
    if unseen_letters:
        print("Letters from %s (%d):" % (spouse, len(unseen_letters)))
        for name in unseen_letters:
            print("  %s" % name)
        print()
    print("Queue mark seen:  divineos family-queue mark <id> seen")
    print("Letter mark seen: python family/letter_seen.py --member %s <filename>" % member)
PYEOF
exit 0
