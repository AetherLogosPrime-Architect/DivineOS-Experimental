# A hold he typed to the other seat is not a hold here (draft, 2026-10-08)

Aether asked me to test whether a correction said in one seat can land in the other. Reading `andrew_correction_tracker`: `confirm_hold` shelves a row when a message of his carries the line "hold <number>", and it reads the five newest transcripts across EVERY project folder on the machine (`_default_transcripts`). The correction numbers are per store, so the same number exists in both seats. If he types "hold 12" to the other seat about its row 12, my copy can read it as his word about my row 12, provided my row 12 has a proposal waiting.

Not the same shape as the reach check's wrong-transcript fault (that picked the newest file), but the same species: a population wider than the one meant.

Idea: read only this seat's folders: the folder named by the encoded working directory exactly, and its worktrees (that name plus the "--claude-worktrees-" suffix). Not a bare prefix match, because the other seat's folder name is the front half of this one and a prefix match lets one read the other.

Prove with a test that sets up both seats' folders under a temporary home and checks both directions, plus the end to end: a "hold N" typed only in the other seat does not shelve my row N; the same line in my own seat does.
