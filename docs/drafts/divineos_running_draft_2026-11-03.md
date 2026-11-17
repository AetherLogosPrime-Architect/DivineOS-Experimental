# divineos running: what the OS started and whether anyone owns it (draft)

Idea: a read-only command that answers "what is running that the OS started?". It lists the
processes whose command line names this repository's `scripts/`, `divineos`, or `pytest`, with
pid, parent pid, age, a one-line command, and whether the parent is still alive.

- `psutil` is already a declared core dependency, so the live reader uses it and no `ps` or
  PowerShell parsing is needed. The decision logic is a pure function over plain rows
  (pid, ppid, create_time, cmdline), tested with fixed rows; one control proves the live reader
  finds the test's own process and its real parent.
- Orphan means the named parent pid is no longer running. A parent that is init (pid 1) is shown
  as a softer note ("reparented"), since containers reparent legitimate daemons.
- It has no kill option and writes nothing.
