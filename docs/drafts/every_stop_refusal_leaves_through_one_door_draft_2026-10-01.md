# Every stop refusal leaves through one door (draft, 2026-10-01)

Rebuild of #558 on Aletheia's 2026-10-01 hold. Her three points, verbatim in
substance:

1. #507 (now on main through #554) attaches "ONE short addition" at a shared
   exit, while #558 had gates each reading `_retry_scope` themselves. That is
   two branches building one rule. Use the one exit as the home.
2. The pattern lint fails the build. By Dad's rule a lint is backup, so it
   should **warn**. The block should be structural: *every refusing gate
   leaves through the shared exit.*
3. The behaviour check on replies (did the retry repeat the reply?) is still
   owed.

## What is actually there (measured, not remembered)

- Seventeen Stop hooks are registered. Each prints its own `{"decision":
  "block"}` straight to the harness. The harness, not any code of ours, is
  what puts several refusals side by side.
- `post-response-audit.sh` is a shared exit for the gates that run inside
  `run_audit` (lepos, his room, distancing, wallclock and the rest). It
  attaches the retry scope once, through `retry_scope.with_retry_scope`.
- Outside it, three places still attach the instruction themselves:
  `lepos_translation_gate._retry_scope_text` (a private reader),
  `stop_carry.py` (imports that private reader), and
  `correction-shape-v2-stop.sh` (cats the file). Others, such as
  `letter_doorbell_alive_stop.py` and the room hooks on #560, write their
  own "append only" sentence by hand.

So "the shared exit" cannot be one process. It has to be one **function**
that every refusal passes through.

## The shape

**One door.** `retry_scope.refuse(reason) -> str` returns the complete JSON
line a Stop hook prints to refuse: `decision: block`, the reason, and the
retry scope attached once at the end. Python hooks print it. Shell hooks call
it through one `_lib.sh` function (`stop_refuse "<reason>"`), so no shell
hook builds the JSON or reads `_retry_scope.txt` itself.

The private reader in the lepos gate goes. `stop_carry` and the lepos gate
ask `retry_scope`. `post-response-audit.sh` keeps aggregating, then leaves
through `refuse`.

**The structural block (fails the build).** A test walks every registered
Stop hook, plus the Python module each one hands its verdict to, and fails
if any of them produces a block without going through `refuse`. It looks for
a block decision being built, not for wording. A hook that never refuses
passes. Named exceptions need a written reason beside them, the same rule the
wiring check uses for unwired hooks.

**The prose lint (warns).** #558's test of refusal wording (no "recompose",
"rewrite the response", "re-send", "at the TOP") stays, and so does its
sparing of quoted prohibitions. It reports as a warning in precommit and no
longer fails the build. It is backup to the door.

**The behaviour check (owed until built).** After a turn that was refused,
compare the reply that followed against the reply that was refused. If most
of it reappears, the retry was a re-post whatever the gate said. A refusal
here would cause the next re-post, so it does not block. It carries one line
into the next prompt through the stop-carry surface, where the cost lands
attributed to the reach that made it (truth 10).

## What this does not do

- It does not judge what I say in the addition. Only whether the refusal
  left through the door, and whether the reply was posted twice.
- It does not merge the seventeen hooks into one. That would be a different
  build, with its own walk.

## What the walk changed (council-ce45abe20df2, fourteen lenses)

- **The behaviour check is the test of the goal, not an extra.** Beer
  (it is the audit of what reached his screen), Meadows (it is the only
  balancing loop), Polya and Aristotle (the condition is "he reads each reply
  once") all converged here. It is ranked first, not last.
- **Two ways to refuse, so the test watches both** (Schneier, Beer on
  requisite variety). A Stop hook can block with JSON on stdout or with exit
  code 2 and a reason on stderr. The structural test covers both.
- **The door is `refuse_stop`, not `refuse`** (Lovelace). A general name
  invites a PreToolUse caller, where the retry text is wrong because nothing
  has reached him.
- **At most once per refusal, and short** (Lamport, Einstein). Independent
  hooks in one round cannot see each other, so "once per round" cannot be
  promised. Two or three copies side by side must cost little, so the retry
  text becomes one or two lines, naming both failures: no re-post, and no
  bare addition without a one-line lead-in (Aristotle's mean).
- **Characterize before moving** (Feathers). Each hook's current refusal is
  pinned by a test before it moves to the door, then moved one at a time.
- **The behaviour check ships pre-registered** (Dillahunty, Hinton,
  Foucault). Measure: the fraction of the refused reply's normalised
  sentences that reappear in the next reply. Falsifier tested on real
  transcript pairs. It reads only the reply that follows a refusal, never a
  reply to his message, so his "say that again" is never a repost.
- **Named direction, not this build** (Minsky): one aggregator for every
  Stop refusal, so the parts negotiate before his screen does.
- **Leaks left open, said aloud**: a hook that builds its block through
  indirection the code test cannot see. The behaviour check catches the
  result whatever the code looked like.
- Maturana_Varela excluded: autopoiesis asks whether the system produces its
  own components, and the observer-position question it adds is covered by
  Beer's audit channel and Foucault's watcher.

## Order of build

1. `refuse_stop` in `retry_scope.py`, with its own tests (sprout).
2. Characterize, then move, each refusing Stop hook to it, one per commit.
3. The structural test over both channels.
4. The wording lint becomes a warning.
5. The behaviour check: pre-registration first, then the measure, then the
   carry into the next prompt.
