# The doc-count checker should be able to fix the council count too (rough draft)

*2026-10-08. The idea, not a plan and not a pull request.*

A picture: a smoke detector that can tell you three kinds of rooms are smoky, and a hose that only reaches two of them. For the third you are told to go and fix it by hand, every time.

`scripts/check_doc_counts.py` checks four kinds of counts in the docs and also checks the council roster phrases ("N expert frameworks", "council of N", "N-expert council", "N expert wisdom", "N expert lenses", "(N members)"). Its `--fix` option has fixers for tests, hooks and commands, but none for the council phrases, so a council count that drifts always needs a hand edit and the tool keeps telling you to do its job. Row 376 of the sorted pile asks for exactly this.

The repair is a council fixer shaped like the existing command-count fixer (raise-only by default, with the same "allow lower" escape), sharing the checker's own phrase list so the two cannot disagree, and called from the fix path.

Not in scope: the ghost-line removal in the architecture tree (row 965), which the file's own comment says is deliberately manual.
