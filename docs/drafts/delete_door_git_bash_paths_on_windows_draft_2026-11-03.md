# Delete door and Git Bash paths on native Windows — rough draft (2026-11-03)

Not a plan. The idea.

Dad types (or I type) `rm -rf /c/Users/x/folder` in Git Bash. The delete door asks
Python "is anything there?" with that exact string. Native Windows Python does not
know `/c/...`, says "nothing", and an existing folder is waved through as deleting
nothing. Same spelling problem, opposite harm: a false "safe".

The idea: before asking, spell the path the way Windows does (`/c/x` and
`/cygdrive/c/x` become `C:/x`). If a path starts with a slash and is not a drive
spelling (`/tmp`, `/home`, `//server/share`), Windows Python cannot read it, so it is
not proven missing and the door stays shut. If asking itself fails (permission, bad
byte), the door stays shut too.

What I cannot do here: run real Windows. The spelling rule is a pure function with the
platform as an argument so Linux can test it; the live run stays unchecked and the PR
body says so.
