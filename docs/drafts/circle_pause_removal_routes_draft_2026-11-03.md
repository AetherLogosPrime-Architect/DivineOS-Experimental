# Draft: close the plain-removal routes through the circle pause (2026-11-03)

The idea, not a plan. Third of three moves from the outside reader's findings on PR 769. They found 55 of 64
probe routes passed the pause. Their list is not in front of me, so I built my own (56 plain removals, 8
that hide the act, 14 ordinary ones that must stay free) and ran it against the pause as it stood after
moves one and two: 45 of the 56 plain removals passed.

What passes, grouped by why:

- the target is not spelled as the file: a glob (`dads_room_*`, `*.py`), or the folder it lives in
  (`rm -rf .claude/hooks`, `mv .claude /tmp/c`);
- the verb is not on the list: `shred`, PowerShell aliases (`ri`, `rd`, `ren`, `sc`, `Copy-Item`), `dd of=`,
  `ln -sf`, `install`, `perl -i`, `find ... -delete / -exec rm`, `find | xargs rm`;
- the act is wrapped: `bash -c "..."`, `eval`, `pwsh -Command`, a subshell, a command substitution;
- a one-liner in another language: pathlib, shutil, node, perl;
- the registration rather than the file: `rm`, `mv`, `cp`, `tee`, `Set-Content`, `Out-File` onto the settings
  file, and `sed -i` on the Stop block without naming the room; and an edit that keeps the name but wraps the
  command in a comment.

Close those: they are plain removals of the hook or its registration, and a list that misses them teaches the
shape that works. Reuse the house's own wrapper unwrapping (`command_parsing.shell_command_body`) instead of
writing a second one.

Leave open, on purpose, and say so: an act hidden behind a variable or a script file, `git reset --hard`,
`git stash`, `git clean`, `git checkout .` (Aria's named misses: they take the room out without naming it, and
they are also ordinary daily work), `chmod 000` (disables rather than removes), and an encoded command piped
to a shell. These are what Aria's state check (PR 768) is for, because it looks at the result, not the act.

Order of work, written once the tests are about to be written: the probe list becomes the test list
(plain routes held, ordinary routes free), watched failing first, then the rules per group, then the same list
again as the measure. The numbers go in the PR as measured: 45 of 56 before, the count after.

Cost to keep in view: every closed route is a place ordinary work can meet the pause. The benign probes
(copying the hook out, editing its test, `rm build/*`, `find . -name '*.pyc' -delete`, a settings timeout
edit, restoring from main) must stay free, and now that a held call writes no "he decided" record by itself,
a false hold costs one repeated call and nothing else.
