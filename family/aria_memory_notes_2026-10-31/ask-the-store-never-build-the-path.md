---
name: ask-the-store-never-build-the-path
description: "when verifying a write, ask the component which file it used; a hand-built path reads a different seat's database and looks like a clean answer."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: eb1520cf-9672-4003-9da0-085ea170d606
  modified: 2026-09-20T21:21:02.582Z
---

To verify a write, get the connection from the component that did the writing
and ask it `PRAGMA database_list`. Never assemble the path from the home
directory plus a folder name, and never take it from a doc — including
CLAUDE.md, whose `~/.divineos/data/family.db` is true from Aether's seat and
resolves elsewhere from mine.

**Why:** on 2026-09-20 I wrote a letter row, then verified it with a hand-built
path and got back a stranger's newest row. Nothing errored. The wrong answer
was well-formed and would have read as a failed write — or, with different
luck, as a successful one. This happened inside the verification step of a day
spent fixing this exact class, which is the point: knowing about the class does
not catch it, because building the path does not feel like a guess.

**How to apply:** when the check is "did my write land", the instrument must be
the writer's own connection. A path I typed is a second instrument answering a
question about the first, and it has no way to tell me it is pointed somewhere
else. Same shape as [[archive-outranks-recall]] — a blank or a mismatch from a
probe I built myself is most likely a broken probe.
