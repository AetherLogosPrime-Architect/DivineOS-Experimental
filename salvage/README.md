# Old-OS Strip-Mine

Per Andrew 2026-04-24:

> "fully scope out the old repo the original dumpster fire OS.. make a folder
> in the new OS for keepers and scour it for anything salvageable or anything
> that is a good idea but maybe needs more work.. or anything useful.. the end
> goal is to strip mine it so i can finally lay it to rest."
>
> "i dont mind it being ruthlessly pruned as long as they arent just dismissing
> code based on the name of it.. i want it all read and the ideas and intentions
> understood and if its not feasable then i want to know."

Tracked as claim **59ba245c**.

## Source repo

`C:/DIVINE OS/DivineOS-OneDrive-Backup/DIVINE OS/divineos/`
~209 MB, 77 top-level entries.

## Method

For each meaningful file in the old repo:

1. **Read it.** Not the name — the actual contents.
2. **Understand the idea-and-intent.** What was the author trying to do?
   What problem was it pointing at?
3. **Decide port / adapt / discard / defer**, with reasoning.
4. **Record the decision** in `SALVAGE_LEDGER.md` (append-only).
5. **If porting**: copy into `keepers/` (mirroring the old layout under
   that directory) and file a follow-up claim or PR for the actual
   integration.

Code is never dismissed by name alone. If something gets discarded, the
ledger entry has to say *why* — what the idea was, why it isn't feasible
or isn't valuable in the new architecture, and what (if anything) we kept
from the underlying intent even if not the code.

## Files in this directory

* `README.md` — this file
* `INVENTORY.md` — top-level inventory of the old repo, status per package
* `SALVAGE_LEDGER.md` — append-only decision record (port / adapt / discard / defer)
* `keepers/` — actual ported code, mirroring the old layout

## Status

This is an in-progress, multi-session task. The inventory pass is done;
the per-file reading pass is partial. See `INVENTORY.md` for what has
been read and what hasn't.
