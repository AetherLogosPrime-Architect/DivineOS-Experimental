# One shared operating-system lock (draft, 2026-11-23)

**What we are trying to achieve.** Two seats (Aria's and mine) write the same small files. A lock that
judges a holder by the age of a lock file is wrong two ways: a check then a write leaves a gap, and a
slow holder gets presumed dead (Aletheia's holds on #686 and #736). The operating system already knows
who holds a lock and releases it the instant the holder's process ends, however it ends. So nobody
here judges; the system answers.

**Prior art in this repo.** `suite_slot.py` and `his_words_bundle.py` each carry their own copy of the
two calls (take without waiting, release). The kept-out list (#867) needed a third. This piece makes
one shared module so there is not a fourth.

**The module.** `src/divineos/core/os_file_lock.py`: `try_lock(fh)`, `unlock(fh)`, `held(path, wait, poll)`
(raises `LockBusy`), and `is_free(path)` (asks without keeping anything: takes the lock and gives it
back at once, so a test or a status line can ask "is anyone holding this" without becoming a holder).
The lock is on byte 0. The lock file is created and never deleted: deleting it is where a second
holder sneaks in on the other side of a unlinked file.

**Not in this piece.** Moving `suite_slot` and `his_words_bundle` onto it (owed, named, separate);
Aria's #869 `run`/`on_write` resting on it (her piece).

**Falsifier.** A leftover file with no holder reads busy; or a held lock reads free; or `is_free`
leaves the lock taken; or the file is gone after a use. Tests below each fail if the module does that.

**Tests.** leftover file never blocks; a real child process holding the lock reads busy and
`held` raises `LockBusy` within its wait; once the child exits (even killed) the lock is free;
`is_free` releases what it took; the file persists after use; control: a handle that never locked
cannot make `is_free` lie.
