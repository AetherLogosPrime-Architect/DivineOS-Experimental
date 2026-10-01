# every refusal writes itself down — draft

**2026-09-14.** Andrew: *"why not just automate it.. you have a record of all
your failures.. all the tool calls that failed.. the chicken and egg deadlocks
etc etc.. one a failure hits it should open a root cause investigation and fix
immediately."*

## the premise, measured before agreeing

There is no such record.

In the last twenty-four hours the house wrote down eight refusals: six of one
gate complaining the briefing was not loaded, two routine scans. Not one of the
nine that cost this morning is among them — not the correction gate, not the
compass one, not the reach doorman, not the marker-clear refusing a mode it has
no flag for, none of the push refusals. Across the whole history, about five
hundred gate-fires and five recorded push failures against seventy-one thousand
events, and no event type at all for a tool call that simply failed.

So the trigger he describes has almost nothing to fire on. Build it first and it
looks complete and almost never runs — a painted door, and worse than nothing,
because then we both believe something is watching.

**The recording comes first. It is the whole of this pass.**

## where I thought the seam was, and where it actually is

I assumed the OS-side router: it already keeps refusals in a list distinct from
what merely ran, three states, exactly the right shape.

Measured: 134 shell hooks, **two** reference it. The router is not the seam. The
three gates that blocked me hardest today all exit on their own.

The real seam is one line lower and far better: **126 of the 134 source
`_lib.sh`**, and that file already carries a fail-soft JSONL writer —
`_lib_log_liveness` — with hook name, reason and detail, already tuned to avoid
spawning processes because it runs on every hook of every tool call.

The infrastructure exists. What is missing is that nothing calls it when a hook
says **no**.

## the shape, and why not the obvious one

Obvious: add a `_lib_log_refusal` call at every refusal point. That is 126 files
and, worse, every future gate must remember to call it. A rule I have to
remember at the moment of writing a new gate is the thing that already failed —
practice-shape never holds.

**Structural instead: an EXIT trap installed by `_lib.sh` itself.** A hook that
refuses exits non-zero. The trap reads the status and writes the row. A new gate
gets recorded by existing, with nothing to remember and nothing to add.

That is remediation (a) from the kiln — take the option away. There is no
choice-point where forgetting is available.

## what the row has to carry, or the investigation cannot run on it

- which hook refused
- the exit status, so a refusal is distinguishable from a crash
- the tool call it refused, which `extract_tool_command` already produces
- the session, so nine refusals in one stretch can be seen as one stretch

Without the last one it cannot answer the question that actually mattered today:
*is this the same thing refusing me again.*

## the trap's own failure mode

A trap that raises turns every gate in the house into a crash. Everything here
is fail-soft in the same shape as the liveness writer it sits beside: no spawns,
a write that swallows its own errors, and nothing that can change the hook's
exit status. **The recorder must never be able to alter what the gate decided.**

Its dual is worth stating because it is the more likely error: if it silently
writes nothing, we are back where we started while believing otherwise. So the
proof is a test that runs a real hook, makes it refuse, and reads the row back.
Not a unit test of the writer — the writer works. The claim is that refusals
reach it.

## what this pass is NOT

Not the investigation trigger. That is next and it needs this to exist first.

Not a threshold. Andrew already corrected that shape before I said it out loud:
not three times, every time. A threshold gives each pattern two free passes and
the free passes are where a common cause hides as separate incidents.

Not the recursion rule either, though it is decided: a failure hitting inside an
open investigation belongs to that investigation. Nine-with-one-cause is exactly
what nine separate incidents look like from inside.

## the honest doubt

Eight of the 134 do not source the library. They will not be recorded and I will
not claim they are. Naming the number beats a silent partial.
