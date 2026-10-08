# Does the cut-away checker catch a test I made weak on purpose?

*Round eight, errand two (second half). 2026-10-08, cloud helper. Run in a scratch copy of the branch `aria/the-cutaway-checker` (commit `0fd9afa3`); the trial file was never committed anywhere, the checker's baseline was not written, and nothing in the repository was changed.*

**A picture.** Round seven showed the stage hand could saw through the legs under ten ordinary tests. You asked: does it notice a table that was never standing on the floor at all? So I built three tiny tables on purpose: one that only claims to stand on the code, one that does lean on the code but catches its own fall and pretends it did not, and one honest table as a control.

## The trial file (three tests, in a scratch copy only)

```python
from divineos.core import hook_layer


def test_weak_names_the_code_but_never_depends_on_it():
    assert 1 + 1 == 2


def test_weak_calls_the_code_and_swallows_the_failure():
    try:
        hook_layer.inventory("/nonexistent/folder/for/the/trial")
    except Exception:
        pass
    assert True


def test_control_honest_depends_on_the_code():
    try:
        hook_layer.inventory("/nonexistent/folder/for/the/trial")
    except (OSError, ValueError):
        return
    raise AssertionError("the code was expected to refuse a missing folder")
```

## What the checker said

Command, from the scratch copy, with a scratch home: `python3 scripts/cutaway.py --workers 1 --check --json <out> --files tests/test_zz_weak_trial.py`

```
tests/test_zz_weak_trial.py: {'DISCONNECTED': 1, 'SWALLOWED': 1}
[cutaway] 1 file(s). Totals: {'DISCONNECTED': 1, 'SWALLOWED': 1, 'CONNECTED': 1}
[cutaway] RISE: tests/test_zz_weak_trial.py has 1 DISCONNECTED test(s); the floor is 0. Give the test a real dependence on the code it names, or say why it is honest with --update-baseline --allow-rise.
[cutaway] RISE: tests/test_zz_weak_trial.py has 1 SWALLOWED test(s); the floor is 0. Give the test a real dependence on the code it names, or say why it is honest with --update-baseline --allow-rise.
exit code 1
```

Per test, from the saved results (5 functions were cut):

| Test | Verdict | Right? |
|---|---|---|
| `test_weak_names_the_code_but_never_depends_on_it` | DISCONNECTED | yes |
| `test_weak_calls_the_code_and_swallows_the_failure` | SWALLOWED | yes |
| `test_control_honest_depends_on_the_code` | CONNECTED | yes |

**So: yes, it was caught, both ways, and the honest control was left alone.** The commit-time check (`--check`) refused the file with exit 1 and named both rises.

## What this does and does not show

- **It shows the checker flags both kinds of weak test I made, and that its ratchet fails a new weak test in a new file** (floor 0). It does not show how it behaves on weak tests of other shapes (a test that mocks the thing it tests is one of the checker's own listed fakes, which I did not re-make).
- **A weak test added to a file that already has a floor above zero** is caught only if the count rises above that floor. A weak test that replaces a fixed one would not be seen. I did not test that.
- **The word problem from PR #612 does not apply here:** this file has neither `bash` nor `subprocess` in it, so the first weak test was labelled DISCONNECTED and not "out of process?". Add either word to the file and it would have been relabelled; that is what #612 shows.
- One file, one run, not timed, not Windows.
