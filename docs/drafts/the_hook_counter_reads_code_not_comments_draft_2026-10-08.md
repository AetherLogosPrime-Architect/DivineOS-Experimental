# The hook counter reads code, not comments (draft, 2026-10-08)

`divineos hook-layer show` is the number the migration to seven doors is sized from, and it was wrong in both directions. The cloud helper's round-five recount (`round5/hook_counter_recount.md`, branch `cloud/pile-sorting-2026-10-08`) found it, and I had half of it already: the counter did not know the doorbell form, `python -m divineos.<module>`, so ten scripts that already hand their thinking to the OS were listed as detached (45 files on main; 35 once they are taken out).

The other half is new: the pattern matched anywhere in a line, comments included, so scripts were "attached" because a comment said `divineos briefing`. Two of the five the helper named make no call at all (`continuity-frame-prime.sh`, `log-session-end.sh`).

Idea: add the `-m divineos` form, and match only on lines that are not whole-line comments. Two new tests written first and shown failing on the old counter: a doorbell next to a script that holds its own logic (the control that must stay detached), and a script that only mentions the OS in comments next to one that really calls it.

Result on the real hooks folder at this base: 38 detached, 5,561 lines. That is not the 35 I had said, and the difference is stated, not tuned: `lepos-channel-reflect.sh` builds its `divineos` command inside embedded Python in a form the text pattern cannot read, so it now reads detached while really calling the OS. It was attached before only by a comment's luck. The counter stays a text match; the proper repair for that script is a pattern for the quoted-argument form, which I have not written and would not guess at.

Not decided: whether a script that only asks for an interpreter (`find_divineos_python`) counts as attached. Dad's plan keeps the thinking in the OS, so I read it as detached; it matches neither pattern today, so nothing changes.
