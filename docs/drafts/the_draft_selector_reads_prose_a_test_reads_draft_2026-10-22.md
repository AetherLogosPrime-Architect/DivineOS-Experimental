# The draft selector no longer skips prose that a test reads (draft, small)

Aria, 2026-10-22. Aether's cold read of #704: `select()` skipped everything under `docs/`, `family/`, `exploration/`, `dreams/` or ending `.md` / `.txt`, on the idea that prose cannot change a test outcome. That is false for the files tests read. 26 test files on main name `AUTOMATION_REGISTER.md`, `CLAUDE.md` or `ARCHITECTURE.md`, and the pre-commit doc-count check reads them. A draft that changed only the register selected no tests and said nothing about it.

**The change.** Prose is looked up by file name, the way a script is. If a test names it, that test is selected. If none does, it is skipped silently and not reported as untested (a draft of a letter has no test to run).

**How it can fail, said first.**
- A very common file name (`README.md`) is named by many tests and selects all of them: a cost, not a hole.
- A test that reads prose by a built path (a glob, a directory walk) never names the file, so it is not selected: the same limit scripts already have, closed by the full run on the push bound for merge.
- Reaching a name inside a longer name (`NOTES.md` inside `FOOTNOTES.md`) over-selects, which is the safe direction.

**Proof.** Two tests with controls: prose a test reads selects that test; prose nobody names selects nothing and flags nothing. The new tests fail on the old selector.

**Status.** Built on #704 after Aletheia's confirm at `2701d642c`; the head moves, so she re-reads the delta.
