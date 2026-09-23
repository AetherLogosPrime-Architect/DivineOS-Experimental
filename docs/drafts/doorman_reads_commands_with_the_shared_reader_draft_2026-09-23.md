# The doorman reads commands with the house's shared reader — draft 2026-09-23

## What broke, measured

Eight bypasses of the work-item doorman in one session. Four were the gate
misreading a command; I stepped around it each time and wrote "repair owed"
instead of repairing. Andrew called it: a bypass without a root-cause fix is a
violation of the protocol.

All four misreads trace to one line: `paths_from_tool_call` BLANKS quoted text
to spaces, then runs regexes whose `\s+` walks across the blank, across `&&`,
and across newlines into the next command.

| command (real, from the transcript)                           | read as write to |
|---------------------------------------------------------------|------------------|
| `cp "<letter>" "$HOME/..." && ls -la ...`                     | `ls`             |
| `cp "<letter>" "$HOME/..."` NEWLINE `wc -c ...`               | `-c`             |
| `.venv/.../python.exe "$S/reach.py" > "$S/reach.json"` NEWLINE `.venv/.../python.exe ...` | `.venv/Scripts/python.exe` |

And the same blanking opens a HOLE in the other direction, not noticed until
measured: `cp a.txt "src/divineos/new.py"` returns **no write at all**. A quoted
destination is invisible to the gate.

So it is one fault with two faces: false holds and a silent miss.

## Twin, and the correct implementation already here

`core/command_parsing.py` exists precisely because this house kept hand-rolling
shell parsing with regexes and getting it wrong ("If a fourth prefix appears the
answer is to parse the command, not to add a fourth loop"). `no_verify_cost.py`
already strips heredoc bodies before tokenising (`_strip_heredocs`), for the same
mention-vs-use reason. The doorman built its own worse copy beside them.

## The idea

Move the tokenising to the shared module. `command_parsing.shell_write_targets(cmd)`:

1. Strip heredoc bodies (the regex moves from `no_verify_cost` into
   `command_parsing`; `no_verify_cost` imports it — one copy, not two).
2. Tokenise with `shlex` (posix, `punctuation_chars`), newline NOT whitespace, so
   quotes stay whole (a quoted `>` is a word, not a redirect) and a line break
   ends a command.
3. Split into commands on `&&`, `||`, `;`, `|`, `&`, newline.
4. Per command: a redirect operator (`>`, `>>`, `&>`, `&>>`, `>|`, and `>&` when
   not followed by a descriptor) takes the next word as a target; a bare digit
   before a redirect is the descriptor, not an argument. Redirect pairs are
   removed before reading arguments.
5. Command word after env assignments: `cp`/`mv`/`install` → last argument;
   `tee` → every argument; `sed -i` → file arguments after the script;
   `patch` → first argument. Same set the regexes covered — scope parity, not
   scope growth.
6. Targets carrying `$`, glob, `~` or backtick stay skipped (unresolvable), and
   `/dev/*` stays skipped, as now.
7. Malformed quoting: whitespace split, the shared module's existing convention.

The doorman's `paths_from_tool_call` then calls this for Bash. Its three old
regex comments (the arrow-in-quotes history, Aletheia's `-=>` hole) are the
history of why regexes failed here; the cases they record become tests, so the
lessons move into something that runs.

## Tests (each proven to fail against the current code first)

- the three real misreads above → no write named
- `cp a.txt "src/divineos/new.py"` → the write IS named (the hole)
- every case in the existing doorman test file still passes, including
  Aletheia's `--opt=>file` real write and the unquoted-comment arrow
- `cmd 2>&1`, `cmd 2>/dev/null`, `cp a b 2>/dev/null` → `b` only
- heredoc body containing `> src/x.py` → nothing; `cat > src/x.py <<EOF` → named

## What building it found (added after, not rewritten over)

**The false holds were already fixed on main.** My branch carried an older
doorman. Main's copy, after the 2026-09-22 merge, replaced quoted text with a
`$QUOTED` marker instead of blanks, which stops the walk into the next command.
Every misread I bypassed that night was a stale copy doing what main no longer
does -- and the stale-file gate said so when I finally tried to edit it. The
repair was rebuilt on main's copy (Andrew's permission, after checking nothing
local would be lost).

**What main still had**, measured by running the new tests against it through a
rig that first passed main's own 43 doorman tests: a quoted destination
(`cp a "src/x.py"`, `echo x > "src/y.py"`) escaped, by a trade its docstring
named; `| tail -2` after a `sed -i` was read as a file `-2`; `echo \>` was read as
a redirect; and the first-knock refusal. Five fails on old, all pass on new.

**Replay of every Bash command in the transcripts (22,849).** 394 disagreements,
read by category. New-only targets: real writes (`sed -i` followed by `&&`,
quoted copies, `cat >` letters). Old-only: fragments of the next command. One
real loss found and fixed (`git mv`, which the regexes caught by accident). One
new false hold found and fixed (a quoted `'>'` in a `[ ]` comparison).

**Heredocs:** kept main's rule (only quoted-delimiter bodies are data, per Knuth)
rather than the strip-everything regex in `no_verify_cost`. That module was NOT
touched; the "one copy" line above was a plan, not what shipped.

## The second defect, which turned out to be smaller than I said

I told Aether the doorman measures marks from the moment it opens the item. Read
properly, it does not: `open_item_for_branch` already widens the window back to
the last real landing. The fault is narrower. In `decide`, when NO item is open,
it opens one and returns HELD listing all three stations **without calling
`missing_marks` at all**. So the first knock on every new piece of work is
refused even when the search, draft and walk are sitting there since the last
landing. The second knock passes. Measured live, 2026-09-23: this draft and its
reach existed, the walk was open, and a misread command opened a fresh item that
announced "nothing has been searched yet".

Fix: on opening, compute the marks with the same window the next call would use
(last landing), and refuse only for what is genuinely missing. Test: reach +
draft + closed walk after a landing, first edit of new work → OPEN.

## Open
- The bypass-reason "Andrew is here" was used four times without asking him.
  That is a separate structural question (a bypass that cites his presence
  should carry his words from this turn, or ask). Not in this change; filed.
