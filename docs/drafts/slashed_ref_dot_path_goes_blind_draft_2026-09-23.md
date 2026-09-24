# A slashed ref and a dot-path go blind (draft, Aria, 2026-09-23)

## The failure, four times

The Windows shell (MSYS) rewrites an argument it takes for a path list before
git sees it. Measured tonight, each shape against a control:

| argument | result |
|---|---|
| `eb27fe23:.claude/hooks/x.sh` (no slash in the ref) | ok |
| `HEAD:.claude/settings.json` | ok |
| `origin/main:src/divineos/__init__.py` (path does not start with a dot) | ok |
| `origin/main:README.md` | ok |
| `origin/main:.claude/settings.json` | **mangled** |
| `origin/main:.gitignore` | **mangled** |
| any of the mangled ones with `MSYS_NO_PATHCONV=1` | ok |

So the shape is: **a ref containing `/`, then `:`, then a `.` followed by
anything but `/`** -- corrected on the walk (Hawking, walk-6e8e2c7e5ca4):
`origin/main:./README.md` goes through untouched, so "starts with a dot" was
too wide. Also measured on the walk: quoting the argument does NOT protect it
(the rewrite happens on argv as the native program starts, after the shell has
removed the quotes), a variable does not protect it, and `git -C .` is still
mangled. A genuinely absent path answers "path does not exist" instead --
the backslash-and-semicolon object name is the mangling's own fingerprint.
Walk distinctness 0.374 (real walks 0.21-0.27, restatements 0.44): closest pair
Hawking/Hinton, both about the boundary from two sides. Git receives `origin\main;.claude\...`, answers "not a valid object", and
any probe written as "does this branch carry the file?" reports **missing** --
could-not-look arriving as found-nothing. Dot-folders are `.claude/` and
`.github/`: the hooks, settings and workflows, exactly the files a guardrail
question is asked about.

History: me 2026-08-31 (a count of zero), Aether minutes after reading my letter
about it, Aether 2026-09-03 ("my instrument lied first"), me 2026-09-23 (four
branches reported missing a hook; one of them had it). Written up in letters
each time; never guarded. The knowledge store has no lesson on it.

## Why not the global switch

`MSYS_NO_PATHCONV=1` everywhere takes the option away entirely (truth #11a), but
the same conversion is what turns `/c/DIVINE OS/...` into `C:\DIVINE OS\...` for
every Windows program the house runs -- the venv python among them. Turning it
off globally breaks far more than it fixes.

## The idea

A PreToolUse check in the doorbell, same shape as `heredoc_escape`: a small core
module with `should_refuse(command)` and `refusal_message(command)`, a surface
in `hook_surfaces.py`, registered in the same change.

- Refuse a Bash command that has an argument matching the measured shape and
  does not already set `MSYS_NO_PATHCONV=1` (or `MSYS2_ARG_CONV_EXCL`).
- The refusal names the argument and the one-line remedy: prefix the command
  with `MSYS_NO_PATHCONV=1`.
- Only where the conversion exists: an `MSYSTEM` environment or Windows. On a
  POSIX box nothing is mangled and nothing is refused.
- Tokenised, not regexed over the raw string: a quoted mention of
  `origin/main:.claude` in an echo or a commit message is prose, not an
  argument. Uses the shared command reader's tokens.

## Proof owed

- Tests for every row of the table above (refuse only the mangled rows), the
  remedy clears it, a quoted mention does not fire, a non-MSYS environment
  does not fire.
- A live provocation: the real `git cat-file -e` on the mangled shape fails and
  the same with the remedy succeeds -- the case the guard exists for, run.
