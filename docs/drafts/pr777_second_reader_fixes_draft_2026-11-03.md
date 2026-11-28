# PR 777 second-reader fixes — rough draft (2026-11-03)

Not a plan. The idea.

1. Delete door, Windows: `rm -rf /c/Users/x/folder` typed in Git Bash names a folder
   native Windows Python cannot see under that spelling, so `lexists` says "absent" and
   an existing folder is freed. Fix: turn `/c/...` (and `/cygdrive/c/...`) into `C:/...`
   before asking; a leading-slash path on Windows that is not a drive form cannot be
   read, so the door stays shut; any error while asking keeps the door shut.
2. Build-flow door: "outside the house" assumed the root's `.git` is a folder. In a
   linked worktree it is a file, so the main checkout and sibling worktrees (same
   house) were judged outside. Fix: find the shared git folder first (via `commondir`),
   then a path is the house if its `.git` leads to that same shared folder.
3. Question asked: does the guardrail list name anything outside the root? Answer by
   reading it: no. Pin with a test so the day one appears it fails.

Untestable here: real native Windows. The converter is a pure function with an explicit
platform switch so the Windows spelling is tested on Linux; the live Windows run is
not checked.
