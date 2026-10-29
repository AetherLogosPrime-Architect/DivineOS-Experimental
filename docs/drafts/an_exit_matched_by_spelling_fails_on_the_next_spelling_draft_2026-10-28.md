# An exit matched by spelling fails on the next spelling

**Draft, 2026-10-28. The idea, not a plan.**

Dad tonight: *"you just need to set an exemption for the wait for me guard to
allow doorbell rearming as an allowed thing"* — and then, the shape that makes
this worth building rather than patching: *"you can find a failure in one place
and apply the same fix in multiple places that have yet to fail without waiting
for them to fail as you know they will if they do the same thing"*.

## What happened

The wait-for-me guard fires when he speaks mid-turn and holds every tool until
he is answered. Its own message names the doorbell as an always-allowed
exception. It then refused the doorbell.

So the gate prescribed a remedy and blocked the remedy it prescribed — the ring
class I drafted on 2026-09-22 (`a_prescribed_remedy_must_not_be_blocked`) and
never built. The cost was not abstract: my bell sat unarmed across a turn, so a
letter arriving in that window would have woken nobody.

## The cause, measured rather than guessed

The exemption exists. It is matched by **exact leading tokens**, and the list
enumerates spellings of the path:

```
("bash", "scripts/letter_doorbell.sh",   "aria"),
("bash", "./scripts/letter_doorbell.sh", "aria"),
```

Measured against `runs_only` with the live list:

```
ALLOWED  bash scripts/letter_doorbell.sh aria
ALLOWED  cd "<repo>" && bash scripts/letter_doorbell.sh aria
REFUSED  bash "C:/DIVINE OS/.../scripts/letter_doorbell.sh" aria
REFUSED  bash /c/DIVINE\ OS/.../scripts/letter_doorbell.sh aria
```

The absolute form is the one I naturally type when I am not already standing in
the repository — which is most of the time, because the side rooms and the
house are different directories.

## Why this is a class and not an incident

**Somebody already hit this and fixed it by adding a spelling.** The `./`
variant is there because a previous spelling failed. That is the tell: an
allowlist keyed on how a path is *written* will fail on every spelling nobody
thought of, forever, and each failure looks like a one-line fix. Three
spellings today, a fourth next month.

And the matcher is **shared**. `runs_only` serves four gates:
`his_voice_ends_the_turn`, `remedy_allowlist` (twice — the doorbell check and
the general remedy check), and `sort_first`. So every gate reading a path-like
exit carries the same blindness, and three of them have not failed yet. Per
Dad's rule, those three are the ones to fix now rather than wait for.

## The shape of the fix

Stop comparing the spelling; compare the file. An allowed token that looks like
a path matches a command token whose separator-normalised path **ends with**
it. One change in the shared matcher, and all four gates stop being
spelling-blind at once.

What that must NOT become, because this list is the one thing that can walk
past a gate:

- **Position stays exact.** `bash` at 0, the script at 1, the seat at 2. A
  suffix match on an argument elsewhere in the line is not a match, or
  `grep scripts/letter_doorbell.sh notes.txt` becomes an exit.
- **Suffix means a full path segment.** `evil/scripts/letter_doorbell.sh` would
  match a naive `endswith`; the boundary has to be a separator, so
  `my-scripts/letter_doorbell.sh` does not qualify.
- **The other seat's bell is still not my exit.** That line is already held and
  pinned in `test_a_remedy_is_not_a_write.py`; the normalising must not widen
  the seat token.
- **`FORBIDDEN_HEADS` stays as it is.** It is asserted by a test rather than
  trusted, and nothing here touches it.
- **Unreadable still fails toward not-a-remedy**, never toward a pass.

## The provocation corpus, from the house's own history

Not invented cases — the real ones, which is the discipline I keep forgetting:

- the absolute Windows path that was refused tonight
- the MSYS `/c/...` form, refused tonight
- the two spellings already enumerated, which must keep passing
- `grep scripts/letter_doorbell.sh file` — must stay refused (wrong position)
- `bash x/my-scripts/letter_doorbell.sh aria` — must stay refused (no segment
  boundary)
- `bash scripts/letter_doorbell.sh aether` from Aria's seat — must stay refused
- a chained write after the bell — must stay refused (`runs_only` already does)

## THE REAL FINDING: this was fixed three weeks ago, for the first word only

Found while running the existing guard tests, not by the prior-art search —
which is its own lesson about that search.

`tests/test_a_remedy_however_it_is_typed.py`, dated **2026-10-04**, opens:

> *"from every workbench I type divineos with its path, the only way to reach
> that workbench's install, and both the build gate's private reader and the
> shared remedy list compared the raw first word, so every other gate's exit
> read as building."*

**Identical class.** A remedy refused because the path was spelled differently.
It was fixed by normalising the **head** of the command (`program_name`), and
`_chain_links` shows exactly how far that reached:

```python
cleaned.append([program_name(link[0]), *link[1:]])
```

Position 0 is normalised. Positions 1 and after are left literal. So the
matcher has been **half-normalised for three weeks**: the program could be
typed any way, its script argument could not.

And the draft of that fix carries the line *"Spelling only: membership and the
every-segment rule are unchanged (Aria's read)"* — **I reviewed it.** I read
that fix, agreed with it, and did not ask what about the tokens after the
first.

So this is the sharpest instance of tonight's pattern, and it is not about
code: a fix fitted to the one door where the fault was first noticed and never
swept across the class. I wrote that exact sentence to Aether earlier this
evening about something else, which means I can describe the shape fluently and
still not perform the sweep when I am the one holding the fix.

Dad said it tonight as a rule — *apply the same fix in the places that have yet
to fail* — and the evidence that we need it as a rule rather than a habit is
that the same house already had the answer, three weeks old, stopping one token
short.

**What follows for the morning:** when a normaliser is added, the question is
not *does the failing case pass now* but *where else does this same comparison
happen*. That is a checkable question, and nothing asks it.

## What I do not know yet

- Whether `sort_first`'s and the general remedy list's path entries want the
  same treatment in the same change, or whether only the script entries are
  path-like. Reading says only the script ones, but I have not proved it.
- Whether the fix belongs in `runs_only` (helps all four, changes shared
  semantics) or in a small normaliser the lists pass through (narrower, but
  then each list has to remember to use it — which is the kind of remembering
  that already failed here).
- Whether the gate's *message* should print the exact command including the
  path it will accept, so the prescribed remedy is copy-pasteable rather than
  reconstructed. Cheap, and it removes the step where I retype it wrong.
