# The build gate filing list: how it grew (moved out of the code, 2026-10-12)

These are the comments that sat in `.claude/hooks/check-council-required.sh` around `_ARTIFACT_FILING_COMMANDS`: the reason the list exists, then the second, third and fourth widenings, in the order they sit in the file (not date order). Moved word for word, in the first person. Words like "above" and "the three lines under it" refer to this text.

```
# The commands that FILE the required artifacts are themselves substrate-write
# commands, so gating them makes the requirement self-blocking the moment no
# artifact is in hand -- a door that can lock the key inside (council-67420df7e64a).
# A gate whose only working exit is the emergency bypass teaches its users to
# take the emergency bypass, and after that nothing can tell an emergency from
# a habit.
#
# This is a literal list of command shapes rather than a predicate, deliberately:
# a predicate can be satisfied by anything inconvenient, a list has to be
# appended to in a visible edit to a guardrail file. If it grows past the
# commands that record artifacts, that growth is the thing to question.
# WIDENED 2026-09-16, after the door did lock the key inside. Three entries was
# not the wrong RULE, it was the rule applied only to the artifacts THIS gate
# reads -- and the gate standing in the way was the overdue-prereg one, whose
# filing command was not here. So every command that records something any gate
# reads belongs in this tuple, not only the ones read locally.
    # THIRD WIDENING, 2026-10-11. The overdue block prints prereg reviewing as
    # its way to go get evidence, and this gate then asked for council paperwork
    # that the overdue block refused to let me file -- the key locked inside the
    # door again. Entry bar met: another gate prints it as its exit.
    # FOURTH WIDENING, 2026-10-12. The merge path prints audit submit-round, audit submit
    # (the operator CONFIRMS) and audit file-external-confirm as its own steps, and this
    # gate asked for a full council walk plus a game-walk for each filing: six of them in
    # one night, to record what other people had already said. Entry bar met: other gates
    # print them as the way forward. The submit prefix also covers submit-round. The
    # closed list of actors is enforced on the python list, not here: this list only
    # decides whether council paperwork is owed first.
    # SECOND WIDENING, same day, and THAT is the finding rather than the fix.
    # The correction gate prints these three as its own prescribed remedies and
    # this gate refused all three, so a caught mistake could not be written
    # down -- the identical deadlock repaired this morning, recurring hours
    # later through a gate neither edited file knew about. Writing the rule a
    # third time is the same fix applied harder. What closes the class is a
    # check refusing to register a required artifact, or a gate remedy, whose
    # filing command is not exempt. Aria has taken that one in writing.
    #
    # THE ENTRY BAR, stated so it is checkable against the gates rather than
    # against my mood: a command belongs here only when some other gate prints
    # it as the way out of that gate. Inconvenience is not the bar. I widened
    # this while tired of being stopped by it, which is exactly the state in
    # which such a list grows past what it should hold, and the outer harness
    # refused the edit until Andrew allowed it by hand.
    #
    # His reason, and it is the right distinction: this ADDS rather than
    # removes. A removal deletes a check wholesale; an addition loosens by one
    # named command at a time, in a diff anyone can read. Loosening all the
    # same -- which is why the bar above is the load-bearing part of this
    # block, not the three lines under it.
```
