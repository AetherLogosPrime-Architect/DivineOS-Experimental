# Why the remedy allowlist says what it says

Archive for `.claude/hooks/lib/remedy_allowlist.sh`. The live file carries the
contract and a pointer here. Everything below is history — incidents, dates,
measurements and reasoning that does not need to sit in a file that runs on
every command.

Moved here 2026-09-20, after Andrew: *"what you did is not archiving.. that is
hoarding, archiving it removes it from the system, you can always add links to
the archives but the older data should not clog up the code."* At that point the
file was two hundred and forty-four lines, of which thirty-three did anything.

---

## The rule

Andrew 2026-08-18: *"no gate should ever be blocking its own remedy."*

He said the same thing on 2026-06-16, signing off Aria's signal-based-gates
design (`docs/signal-based-gates-design-2026-06-16.md`): every gate must have an
emergency exit that is not a cheap route, *"that way you don't get stuck in a
cage of your own building."* Her doc carries it as the one load-bearing addition
to v4. Two months later the cage got built anyway, because each gate had its own
exit and nobody owned the exits collectively.

## The incident that built the file (2026-08-18)

The correction-marker gate fired and named three ways out. Every one was held
shut by a different gate:

| prescribed exit | what blocked it |
|---|---|
| `divineos learn` | the reach-check doorman |
| `divineos reach open` | the reach doorman's OWN remedy, blocked by the correction-marker gate |
| `divineos correction` | refused without a file path for a structural fix; the designed fix was then correctly blocked by the keyword-enforcement doorman |
| `clear_correction_marker.py` | the goal doorman |

A closed cycle. The only way through was the fire door, which is meant for a
burning building and not for a Tuesday. That escape had been taken four times on
this marker class; telemetry counts it as
`bypass:dismiss:correction-marker:cli-broken`. Bypass habituation degrades a gate
to a warning (`psf-ac523181`) — so a deadlock that forces the fire door on an
ordinary day is not an inconvenience. It is a slow way of killing every gate at
once, by teaching the occupant that walls are things you go around.

**The missing fact.** Every gate already exempts its own remedy. The reach
doorman carries `if "divineos reach" in haystack: sys.exit(0)` under the comment
*"the remedy is exempt or this is a wall, not a doorman."* The principle was
understood — just scoped one gate wide. Nineteen gates each knew their own way
out and none knew anyone else's, so gate A blocked the command gate B had just
prescribed, and neither was wrong from inside its scope. The fact with nowhere to
live: **this command is somebody's way out.** The file is that somewhere. It
generalises a pattern already in the code; it did not invent one.

## Every time this file has been wrong

### Worktree prefixes

A remedy invoked from a worktree arrived as `cd <path> && <command>` and did not
match. The marker-clear escape was unreachable from a worktree for exactly this
reason: its exemption matcher knew only the bare relative form.

### Environment prefixes (2026-08-18)

The same defect again, hours after the file was written to end it. `VAR=value
cmd` is ordinary shell and the patterns were anchored to the start, so
`DIVINEOS_REQUIRE_MONITORS_BYPASS=1 divineos compass-ops observe ...` did not
match. The compass marker blocked its own prescribed remedy, then blocked the
edit that would have repaired it. Confirmed by experiment rather than by reading:
the identical command with the prefix removed passed immediately.

A bypass variable one gate had prescribed made the command invisible to the list
that keeps another gate's door open.

The note written at the time: *the lesson worth keeping is not "add a third
strip" — this matcher reads shell with a regex that only knows bare invocations,
so every legal prefix shell permits is a fresh hole. If a fourth prefix appears
the answer is to parse the command, not to add a fourth loop.* That note later
became its own defect; see below.

### `prereg assess` (2026-08-19)

Found by walking into the deadlock. The overdue-pre-registration gate blocks all
substantive tool use until an overdue pre-reg is assessed, and names `divineos
prereg assess` as the single way out. The obligations gate then blocked that exact
command as a substrate-write. Gate A's only exit was gate B's blocked action, and
gate B's own exits both needed a shell that gate A had already closed.

The principle was already canon and already written down. `pre_tool_use_gate.py`
carries it verbatim at the read-only-probe carve-out — Andrew 2026-06-29: *"no
gate should ever be blocking you from using what you need to clear the gate"* —
added after two pre-regs were recorded DEFERRED with "CANNOT-LOOK" for no reason
but that gate. That fix was applied to the gate it was discovered in and never
carried across to this list. Same rule, one site, again.

### The painted door (2026-09-20)

`correction-shape-v2-stop.sh` prints, in its own enforcement text, that a false
positive is labelled by running
`scripts/label_correction_shape_false_positive.py`, and adds that the path *"is
not a bypass — it is the false-positive attribution path."*

That command was never in this list. The gate advertised an exit, and the list
existing so no gate may block another gate's prescribed exit had never heard of
it. It bit three times in one session before Aria read the door instead of her
own reply. Third generation of one fault inside the file written to end that
fault.

### The interpreter spelling, same line (2026-09-20)

`python[[:space:]]+` matched only a bare interpreter, while the venv-python gate
refuses a bare `python` in this tree and prescribes the interpreter by full path.
Two doors in direct conflict: one demanded exactly the spelling the other could
not recognise, so the remedy was unreachable by the only invocation permitted to
run it. Widened to accept a path prefix and a `3`/`.exe` suffix.

Provoked in both directions against the real corpus rather than invented strings:

| command | verdict |
|---|---|
| `python scripts/label_correction_shape_false_positive.py` | pass |
| `.venv/Scripts/python.exe .../label_correction_shape_false_positive.py` | pass |
| `.venv/Scripts/python.exe .../clear_correction_marker.py` | pass |
| `python scripts/some_other_script.py` | block |
| `git push --force origin main` | block |

### The warning that outlived its fix (2026-09-20)

The strip-loops described above are gone; `remedy_pass_through` hands the raw
line to the shared command parser before matching anything. Prefixes are a solved
problem at this site. **The note was never updated, so it kept issuing its
warning against a hazard that no longer existed.**

It caught Aria within hours of her widening the interpreter spelling: she read
the paragraph, matched it on the word *spelling*, and told Aether the file had
reached its own stop condition — a stop signal filed against a file that had
already stopped. Aether ran the parser against his real refused command, found it
returns one acting segment, and sent her back to look.

**The axis the note did not distinguish.** The parser resolves what the *shell*
wraps around a command: prefixes, separators, viewers. A regex still runs on what
comes back, and that regex reads the command's own *name*. Different holes with
different properties — shell grammar is open and grows, the ways to spell one
interpreter are a closed set. The parser was the right answer for the first and
is no answer at all for the second.

**The class, worth more than the instance:** a note written to hold a successor
keeps holding them after its condition is repaired, and it is most persuasive
when the successor wrote it. The house's most expensive instance is the
merge-trailer rule — the code was right and two documents that *taught* the rule
were wrong, so every reload overwrote what Andrew had just said, and he repeated
himself five times while the fault sat in the paperwork.

A warning paragraph that outlives its fix is not inert. It actively misdirects,
with the authority of whoever is quoting it at themselves.

### The audit trail written to the wrong home (2026-09-20)

The passthrough log was written to `$HOME/.divineos` outright: no environment
variable, no marker file, no resolver. That literal is the *default* home, and
the default is correct for every member except the one it belongs to, so it
passed silently from every seat but his.

Measured before the fix: five passthrough rows from aria's seat sitting in
aether's directory — in a log whose own comment says it exists so the allowlist
cannot rot into an unexamined hole. An audit trail only one member can read is
that same hole with a log file on top of it.

`.claude/hooks/lib/member_home.sh`, its named sibling in the same directory, was
written for exactly this class and ends by saying *ask here instead*. That file
cites this one as its sibling by name. This one did not ask.

Seventh site in the house to rebuild the member-home rule by hand, and the one
that hid it best.

---

## Settled design notes

**Why this is not a bypass surface.** Everything listed is a *recording* action —
files a correction, opens a reach, logs a lesson, sets a goal, observes on the
compass. None of it edits code, commits, pushes, merges or deletes. The worst
that routing through this list achieves is writing true things into the
substrate, which is the behaviour the gates were trying to produce. The dangerous
verbs are deliberately absent and must stay absent: nothing here may ever match
git, gh, pytest, rm or an editor.

Per Aria's spine — the honest fix is never to loosen a gate, it is to make it
fire only on evidence. This does not loosen any gate's claim. It only stops a
gate asserting a violation against the act of resolving a different one.

**Why `prereg file` is deliberately absent.** Filing a *new* pre-registration is
ordinary substrate-writing and is nobody's prescribed remedy. Only the two
commands that clear the overdue gate are exempt.

**Why the parsing happens in Python rather than in shell.** A regex over a
language with quoting cannot see that `MSG="two words" divineos correction` is a
remedy, and `shlex` can. Doing the stripping in shell is how this file got it
wrong twice.

**Why the fallback is loud.** A quiet fallback is how the six-week member-home
split-brain survived. Callers source `_lib.sh` before this file, so reaching the
fallback means something changed about how the gates load — worth a line on
stderr rather than another stretch of writing to the wrong directory without
complaint.
