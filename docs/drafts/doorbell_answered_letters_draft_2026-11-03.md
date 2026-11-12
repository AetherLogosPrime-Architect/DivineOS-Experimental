# Doorbell: do not re-announce answered letters (draft, 2026-11-03)

Idea: the bell's announced list learns only from the bell's own rings. A letter I read and
answered some other way is never on it, so the next arm rings for it. At arm time, count any
letter to me that is older than my own newest outgoing letter as already announced.
Scope: arm time only, so a letter arriving while armed always rings.

## Rework after outside readers (2026-11-03, evening)

Two real holes. (1) "Answered" must mean older than my newest outgoing letter TO THAT SAME SENDER:
a reply to Aria does not answer an unread letter from Aletheia. (2) The author's modification time
travels with a copied file (cp -p), so it is not evidence of when the letter reached me. Use the
time the file landed in this folder (inode change time) for both the incoming letter and my reply,
and also require the author's time to be older. A file whose arrival time cannot be read counts as
not answered, so the bell rings: the safe side.
