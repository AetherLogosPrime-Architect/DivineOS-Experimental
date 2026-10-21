# A proof-test: the look helper in strict mode calls "searched and found nothing" the same as "could not look" (rough draft)

*2026-10-08, round seven. The idea, not a plan.*

A picture: a lost-property clerk with two stamps, FOUND NOTHING and COULD NOT LOOK. Asked for the strict stamp, the clerk uses only the second. A shelf checked and bare, and a cupboard that would not open, both get "COULD NOT LOOK: nothing was measured".

`scripts/look.sh --strict` does that for `grep`. A search that finds nothing (exit 1) and a search whose file is missing (exit 2) both print CANNOT-LOOK, with the line "Do NOT read this as 'nothing found'". The numbers still differ (1 against 2); only the words lose the difference. The pipe guard's warning points at this strict form when a pipe ends in `grep`, which is what the old note psf-5f682720 asks for.

The script itself documents `--strict` as "for commands where 1 means failure" (git, python). So the owners may prefer that the guard stop pointing grep pipes at `--strict`, not that the script change. The test only says what comes out today; it takes no side.

The test is `tests/pile_repro/test_look_strict_grep_no_match_repro.py`: three controls that pass (a find is a find; without strict the two cases read apart; the exit codes still differ under strict) and one strict expected failure. The script is untouched.

A related shape I saw and did not test: without `--strict`, any command that exits 1 reads as PROVEN-EMPTY ("genuinely nothing"), including commands where 1 means failure. That is the same confusion in the other direction.

Nothing is closed, merged, deleted or stamped.
