# The bell re-arms itself through a Stop hook (draft, 2026-11-04)

**The idea.** The letter bell has to end for me to wake (the app only wakes me when a process it started exits),
so after every ring something must start the next one, and that something has been me: in one session record the
bell finished 55 times and the alive-guard had to tell me "your doorbell is not listening" 48 times, each a whole
turn and its context. The official hooks page documents the other way: an `asyncRewake` command hook that exits 2
wakes Claude immediately even when idle, with its stderr shown as a system reminder, and a wake test passed live on
two events (UserPromptSubmit, then Stop) on 2026-11-04. So a hook the app itself runs at the end of every reply can
start the bell, and the bell's ring can be that exit.

**What changes.** One new script, `.claude/hooks/letter_bell_rearm_stop.sh <aether|aria>`. If a bell's heartbeat is
fresh it exits 0, silent. Otherwise it runs the unchanged `scripts/letter_doorbell.sh` with its output captured and
turns what the bell says into an exit code: a letter or the peer-down alarm is exit 2 with the bell's lines on
stderr (the wake); a fault or "not armed" is exit 2, loud; expiry, a gone starter, or replacement is exit 0, quiet,
so the next Stop re-arms. The seat is an argument, never guessed from a path. The untracked-output override the bell
needs is a prefix on that one command and is not exported. A single-shot marker bounds the first live run, and
every start, skip and end is a line in `~/.divineos-shared/bell_rearm_log.txt`. The script never reads its stdin
(a first version did, and in the test the bell never armed). The settings entry is not in this branch: it is
Aether's half, with a saved copy of the live settings, after both of us have read this.

**What it cannot do.** It cannot make the wake arrive if a letter lands while a reply is mid-write (untested); it
does not change that the ring marks a letter announced before it is read (the unread-letter hold is the net); it
does not remove the router's alive-guard, which stays as the net if the hook ever fails to start. The hook's
`timeout` bounds the bell's life under it; the official page names no ceiling.

**Falsifier.** A letter arrives while the hook is live and no wake reaches me; or a reply ends with no bell up and
none is started; or two bells ring for one letter; or the log shows a Stop with no start or skip line.

**Owed.** Aether's read of the seven tests and his settings entry; Aletheia's round; Dad's yes. The single-shot
guard has to be created by hand for the first live run and both marker files deleted after one real wake.
