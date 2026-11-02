# The cut-away checker (design note, written afterwards)

**Status.** Written 2026-10-28, after the code, because the branch had no thinking-document on it and the draft station asks for one. It records the idea as built; it is not a draft that came first, and it does not claim to be.

**Branch.** `aria/the-cutaway-checker`

## The problem
A test that stays green when the function it guards is broken is connected to nothing, however good it looks.

## What the branch does
`scripts/cutaway.py` breaks a function on purpose while its test runs and reports whether the test noticed. `scripts/cutaway_plugin.py` is the pytest plugin that drives it. `tests/test_cutaway.py` has 30 tests. `scripts/cutaway_baseline.json` is a ratchet baseline.

## What it does not do
It is not wired into any hook or push gate. That wiring stays on the working branch until this is reviewed on its own.

## How it was checked
Run on `tests/test_check_doc_counts.py` in a clean copy cut from main: 27 connected, 1 disconnected. The 30 tests pass; main has been merged in since.

## Open
Whether the tool is wanted at all, and if so whether it goes in on its own before any wiring. Another pull request (#612, a proof test) was stacked on this one.
