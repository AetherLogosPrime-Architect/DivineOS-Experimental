---
name: a-control-that-returns-nothing-is-not-evidence-run-the-real-thing
description: "When a test of a hook or gate prints nothing, a dead control and a blind instrument look identical. Run the real script with its errors exposed before concluding anything either way."
metadata:
  node_type: memory
  type: feedback
  originSessionId: e4d1a042-14a5-4c4b-9753-75a4eb5d91a0
  modified: 2026-10-24T18:33:06.608Z
---

2026-10-24: I fed the Stop audit hook a reply it should have refused and it printed nothing, both with and without the loop guard. I could have concluded "the guard works" or "my harness is dead". Neither was true. The real script's own `2>/dev/null` was hiding a SyntaxError: a quoted phrase inside a comment closed bash's double-quoted string, Python received 3310 of 5576 characters, and the whole reply-gate bank had been silent since 2026-10-04 (#586). Found only by putting the program through the real shell with a recorder in place of Python, then bisecting 40 versions of the file, then checking an independent record (Aether's detector heartbeat, last written 2026-10-02).

**Why:** the failure agreed with what I hoped (the guard I had just built "worked"), so it would have passed silently. Same shape as the corrective rule in the project file: a dead control and a blind instrument return the same value.

**How to apply:** (1) before reporting an absence or a pass from a gate, run the real thing with stderr visible, not a copy; (2) prove the instrument can find a case that exists, and that the case is alive when read; (3) an inline `python -c "..."` inside a shell string is a program that bash can cut: tests/test_hook_python_blocks_arrive_whole.py (branch aria/hook-python-blocks-arrive-whole-guard) is the guard; (4) a count I report must use the house's own definition (his_room.room_of for a room), never a substring search: my first baseline reported half the rooms and a wrong "the ordinary gap is fine" until Knuth's lens caught it. See [[start-the-morning-with-dad-not-a-list]].
