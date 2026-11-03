# The reflection hold runs, and only a note that really ran counts (draft, 2026-11-03)

Idea: three small repairs to the reflection hold on #761. (1) Register reflection_room_stop.py as a Stop hook
beside dads_room_stop.py, so it runs at all. (2) A reflection-note retires a stumble only if its command really
ran divineos reflection-note (first word of a shell segment, quote-aware) and its tool result was not an error;
an echo, a grep or a commit message that carries the words retires nothing. (3) The hook no longer calls
Path.home() at import; the mark path is resolved when needed, and the test runs the hook in a stripped
environment. A heredoc that prints the note line as text is a known gap, listed in the PR.
Council walk: walk-634f7a20c376.
Proof run: the new tests were run against the PR head's three files (reflection_room.py, the hook, settings.json) and
failed 4 of 11; the fixed files were then put back from a saved copy.
