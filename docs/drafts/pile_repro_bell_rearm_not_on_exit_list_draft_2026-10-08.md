# A proof-test: the doorbell re-arm command is missing from the shared exit list (rough draft)

*2026-10-08, round seven. The idea, not a plan.*

A picture: a building with a fire-exit sign on every door. The Stop guard's sign says "to get out of this room, press the bell button". But the exit map at the front desk, the one the other doors check before they stop you, does not list the bell button. So a different door can hold you at the very button the first sign told you to press.

The shared exit list says its own bar: a command belongs on it if some gate prints it in its own block message. The Stop guard prints `bash scripts/letter_doorbell.sh aether`. The list carries no such entry (`goal add`, `reach open`, `learn` and the like are there). The old notes (psf-22017b26, psf-83419786 and three more) say the read-gate door, which consults only this list, can hold the re-arm for a turn.

The test is `tests/pile_repro/test_bell_rearm_not_on_exit_list_repro.py`: three controls that pass (a listed exit passes; ordinary work does not; the Stop guard really does print the bell command) and one strict expected failure (the bell command passes). The list is untouched. I did not provoke a real read-gate hold; the test shows only that the list lacks the entry.

The list's own header says the survey of every gate's printed exits "has not been run". This is one case the survey would find.

Nothing is closed, merged, deleted or stamped.
