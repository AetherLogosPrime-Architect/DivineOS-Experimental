# Superseded

Code a newer version replaced. Kept whole so nothing is lost, and moved out
of the running house so nothing reaches for the older one by mistake.

Andrew, 2026-09-28: *"if there are 2 programs that do the same job but one of
them is better then you supercede it, replace it with the newest version, the
older one gets deleted from your system and moved to the archives."*

## How something lands here

1. Name what replaces it, and check that the replacement really does the job
   (its caller, its tests).
2. `git mv` the file and its tests under this folder, keeping the original
   path below `archive/superseded/`, so the history follows the file.
3. Add a row to [LEDGER.md](LEDGER.md): what it was, what replaced it, and why.
   Append only.

Nothing here runs. `pytest tests/` does not reach this folder, and nothing
under `src/` imports from it.
