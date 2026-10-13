# The one test that reads his real transcripts is marked as a deliberate exception (draft, 2026-10-12)

## Why

Tests must not read his live messages: this morning 23 tests failed in the push gate because they read the real
store of his last message and ruled him "away" (#630). That rule needs its exceptions written down, or the next
author takes an exception for a leak, or copies the pattern into a gate test where it fails whenever he is quiet.
Aletheia's note on #630 asked for the exceptions to be named.

## Which tests, and how it was settled

She named four tests found by keyword search (`test_keeping_him`, `test_read_gate_corpus_containment`,
`test_correction_shape`, `test_recover_crashed_workers`). I read each: only `test_keeping_him`'s test reads his
transcripts. The others only mention a "real corpus" (the exploration corpus, which is mine), classify text handed
to them, or name the other test as a fixture string. She then proved it by breaking it: with the transcripts
folder made unreadable, exactly that test failed and the other three passed, which also showed the keyword search
had been the error, not the reading.

## What it does

One dated docstring marker on that one test: deliberate, read-only, bounded sample, not to be copied into a gate
test. Aria's cold read caught that my first wording pointed at a guard that does not scan for the marker; the
marker now says plainly that the guard covers only the question hold's store and that nothing scans other tests
for it.

## Not checked

Indirect readers a keyword search cannot see. Aletheia's suggestion for finding any: run the whole suite once with
the transcripts folder unreadable; whatever else fails is a reader nobody knew about. I have not done that run.
