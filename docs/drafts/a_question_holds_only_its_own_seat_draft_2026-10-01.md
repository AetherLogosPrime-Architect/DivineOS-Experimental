# A question holds only its own seat — draft, 2026-10-01

Dad, 2026-10-01, after two guards locked against each other in my window:
*"this obviously needs fixed lol so lets fix it"*

## What happened

The question hold stopped me over *"Dad, should I turn my letter doorbell back
on?"*. I never asked him that. It was almost certainly Aether's question: his
doorbell was the one off. The same afternoon it held Aether over a question of
mine (his letter: "your question holds me"), refused his reads in another
checkout, a letter, and his doorbell. In mine it refused a `cat` of the
doorbell's output, then `divineos prereg assess`, the overdue-review gate's
own prescribed exit, while that gate refused the doorbell. Two gates, each
holding the other's only way out.

## Three faults, one module

1. **One note for two seats.** `STATE = Path.home() / ".divineos" / ...`, the
   same file for both of us. Every other per-seat store resolves through
   `divineos_home()`, which honours each checkout's `.divineos_data_home`
   marker. Mine is `~/.divineos-aria`. So each seat's question held the other.
2. **Looks held.** The passes were three narrow letter patterns. The module's
   own words say reading passes; a `cat` of a task output and `prereg show`
   didn't. Today's doorman fix gave the house one judge of a pure look,
   `_is_readonly_probe`; ask it.
3. **Another gate's exit held.** Dad 2026-08-18: *"no gate should ever be
   blocking its own remedy."* `remedy_allowlist.is_remedy` exists for exactly
   this, listing `prereg assess` among others. The hold never asked it.

## The change

- STATE, HOLD_LOG and ESCAPED resolve through `divineos_home()`.
- `refusal` passes a Bash line that `_is_readonly_probe` calls a look, or that
  `is_remedy` calls some gate's exit, alongside the existing letter passes.
- Nothing else. A question still holds building, still releases on his next
  message, still has its counted emergency exit.

## Amendment — a shared board that only shows

Dad, 2026-10-01, after the per-seat change: *"also the shared fridge idea isnt
bad, as seeing what the other was asked is a nice addition, it just shouldnt
block, only the personal ones do :)"*

Arming also writes a card to `~/.divineos-shared/open_questions/<home>.json`,
keyed by the seat's home folder name (always known, one per seat), shown with
the name from `sibling_corrections.SIBLING_HOMES`. Clearing the own hold
removes the card. When a notice arrives or he speaks, the OTHER seats' cards
are shown as a line ("Aether is waiting on Dad: ..."). They never produce a
refusal. The board is display only: a broken or missing board never blocks,
and never stops the own hold from arming.

## Not touched, and why

Recording actions are what the remedy list holds; it forbids git, rm, cp,
python, bash, pytest by test. So building still waits. A hold that lets
recording and looking through is the hold the docstring already describes.

## Falsifier

Replay: with a hold armed in seat A, seat B is not held. In one seat with a
hold armed: the exact `cat` of the doorbell output passes, `divineos prereg
assess ...` passes, `git commit`, `rm`, and an Edit are still held.
