# Reproduction tests for the pipe guard and the command-shape classifier (rough draft)

*2026-10-08, round three of the cloud helper. The idea, not a plan and not a pull request.*

A picture: a doorman who turns away a delivery driver because the box says "fragile, handle with care" in the same words as a warning sign on a different building. He is reading the words on the box and not asking what the driver is carrying in.

Two guards read the shape of a command. One checks whether a pipe could hide a failure, and it refuses harmless commands (a help request on a write command, a read-only look at a pull request) while only warning on plain look-up pipes, and it refuses instead of adding the safe setting itself. The other, the classifier behind the council gate, reads the words inside quotes as if they were commands.

Each reproduction runs the real hook (with an isolated home folder) or the real classifier and is marked as an expected failure, so it passes quietly today and rings loudly the day the guard is repaired. A few unmarked controls prove the probes are alive.

Not in scope: repairing anything, and the heredoc door, whose existing tests deliberately pin the behaviour the note objects to.
