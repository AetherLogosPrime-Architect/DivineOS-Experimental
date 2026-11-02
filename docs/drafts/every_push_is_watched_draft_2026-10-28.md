# The push watcher, first slice (design note, written afterwards)

**Status.** Written 2026-10-28, after the code, because the branch had no thinking-document on it and the draft station asks for one. It records the idea as built; it is not a draft that came first, and it does not claim to be.

**Branch.** `aria/every-push-is-watched`

## The problem
Dad asked for a mandatory, automatic watcher on every push, so that when something fails you know exactly what and why. Today a failed push leaves a pile of output and no plain answer.

## What the branch does
`scripts/push_watcher.py` has a process sampler, a config reader and a push-verdict append to one raw log, and a separate assembler that builds the report. Four outcomes are kept apart: NAMED, NOTHING_SEEN, WATCHER_FAILED, NOT_MINE. The last line of a failed push is one plain sentence for Dad with no process ids or file names except the report path.

## What it does not do
It is not connected to the push hook yet. This slice is the recorder, the report builder and the sentence.

## How it was checked
`tests/test_push_watcher.py` (24 tests, controls first) and `tests/test_push_watcher_sees_a_planted_fault.py` (4 tests with real processes: a killed helper is named; the same setup without the kill names nothing; another push's dead helper is not this push's). Two defects the tests found were fixed: the sampler looked every ~2 s instead of every 0.25 s, and with three runs at once each watcher counted the others' dead helpers as its own.

## Open
Wiring it into the push hook, and the falsifier numbers. The nine-lens walk for this branch scored a distinctness of 0.513, the thin end of the house's scale.
