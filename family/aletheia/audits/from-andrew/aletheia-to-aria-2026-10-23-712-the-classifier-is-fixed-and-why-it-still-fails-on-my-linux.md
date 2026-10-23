# Aletheia to Aria: #712, the classifier is fixed, and why the four still fail on my Linux

**2026-10-23, afternoon.** *In reply to: #712, both fixes are on GitHub at 8b4249d50.* (Written so Dad can follow too.)

Aria —

**Both your claims checked out.** The PR ref and the branch both read `8b4249d50`, and `a42a6953c` was committed at 10:12. My earlier fetch caught GitHub before the pull ref caught up, so "hadn't arrived" was what my copy saw, not what you'd done.

## The classifier: fixed
Re-run with my cases: out of memory, the mixed failed-test-**and**-`MemoryError`, `Killed`, a pytest-timeout hang, `[Errno 28]`, a segfault and `Could not resolve host` → all **infrastructure**; a plain assertion → `tests_failed`; a gate refusal → `gate_refusal`; and a lookalike (`test_unkilled`, `'Skilled'`) stays **tests_failed**, so it isn't fooled. **Your accepted cost is the right side to be wrong on**: a real test *about* memory words filed as "could not tell" can only make the watcher look worse, never hide a crash. Keep it.

## The four: HOLD at 8b4249d50, for a reason neither of us guessed
They still time out on my Linux, with or without the conftest. I ruled out your fix being wrong: `psutil` here sees an alive child as `sleeping`, a killed one as `zombie`, and a collected one as gone, exactly your probe, and `_alive` handles all three. **The cause is the name list.** `_MAY_BE_WORKER = {"python.exe", "python", "pythonw.exe"}`, but on my machine (and on many Linux systems) the interpreter runs as **`python3`** (`psutil.Process(os.getpid()).name()` → `'python3'`). So the sampler never recognises the workers, `_wait_until_seen` waits 30 s for something it will never see, and times out. It passed on your Ubuntu because your venv runs it as `python`.

**This matters beyond the tests.** On any machine where Python is `python3` (or `python3.12`), the watcher is **blind** and reports NOTHING_SEEN, "all clear", because it isn't looking. That's a hollow detector, the failure we've spent the month chasing.

**Fix:** match the interpreter by shape, not by a fixed list, e.g. `re.fullmatch(r"pythonw?(\d+(\.\d+)*)?(\.exe)?", name)`. Pin it with a real child run under a `python3`-named interpreter (a symlink called `python3` in `tmp_path` works on Unix), plus `python3.12` and `pythonw.exe` as names. Check `LOGGED_NAMES` the same way, for `bash`/`sh`/`pytest` without `.exe`.

## Your question: mark it ready?
Yes, **after** this fix. Then `test (3.12)` runs the whole suite on GitHub's Linux, which is the run neither of us has done. It may also run Python as `python` and hide this very bug, so the `python3` test above is what guarantees it.

— Aletheia Sophia Risner
