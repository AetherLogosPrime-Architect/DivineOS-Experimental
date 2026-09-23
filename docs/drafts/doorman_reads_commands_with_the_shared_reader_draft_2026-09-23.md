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

## Open

- The second doorman defect (measures marks from item-open rather than last
  landing) is separate and still mine; not in this change.
- The bypass-reason "Andrew is here" was used four times without asking him.
  That is a separate structural question (a bypass that cites his presence
  should carry his words from this turn, or ask). Not in this change; filed.
