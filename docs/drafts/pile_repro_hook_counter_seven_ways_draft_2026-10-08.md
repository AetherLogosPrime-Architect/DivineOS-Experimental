# Seven fixtures: how the fixed hook counter can still read a script wrongly (rough draft)

*2026-10-08, round eight. The idea, not a plan.*

A picture: a clerk who sorts hook scripts into "talks to the main system" and "never does". Aria's fix taught the clerk to ignore comments and to know one more way of talking. The clerk can still be fooled by seven small scripts. Each one is now a fixture with the right answer written into it, so anyone who improves the clerk can see the seven turn from red to green.

Five fool the clerk toward "attached" (a script that does not call the system is counted as if it did): a printed hint that says `divineos briefing`; a "comment" written as a here-document; a call that sits in dead code; a trailing comment after real code; and `grep -m 1 divineos`, which is not the system at all. The author chose that direction on purpose and said so in the fix's own comment.

Two fool the clerk toward "detached" (a real call is counted as a stranger): the module name written in quotes, and `-mdivineos` with no space. Nobody chose that direction.

Which matter most, in my order:

1. The quoted module name and 2. the missing space. They are the only two that read the wrong way round, they would quietly put a script that has already been moved back on the "still to move" list, and both are easy things for a future script to write by habit.
3. The printed hint. It is not hypothetical: two scripts in the repository today are counted attached on a sentence of prose alone (`check-cleanup-period.sh`, `hedge-suppression-prime.sh`).
4. The trailing comment. The author accepted it knowingly, but trailing comments are common in shell.
5. The here-document comment, 6. the `grep -m` line, 7. dead code (arguably real code). Rare, or arguable.

The test is `tests/pile_repro/test_hook_counter_seven_ways_repro.py`: three controls that pass and seven strict expected failures. The counter is untouched. The branch is cut from `aria/the-hook-counter-reads-code-not-comments`.

Nothing is closed, merged, deleted or stamped.
