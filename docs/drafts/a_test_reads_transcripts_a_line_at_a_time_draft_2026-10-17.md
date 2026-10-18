# A test reads transcripts a line at a time (draft, 2026-10-17)

## What happened

`tests/test_his_message.py::test_on_the_real_transcripts_each_window_hears_him` reads the newest forty real transcripts of each window to check the house still hears him. It read each file whole (`path.read_text(...).splitlines()`). One transcript is now over a gigabyte; decoded and split, that is several gigabytes in one worker, and the push gate runs the suite in parallel. On 2026-10-17 the test raised `MemoryError` at push time and refused a clean branch's push. It is also the same kind of load that crashed Dad's machine the night before: many large reads at once, with nothing counting what each one costs.

## What changes

One line: iterate `path.open(...)` instead of reading the file whole. The assertions are the same. The test passes in about 20 seconds alone, as before.

## What it does not do

It does not stop other readers of transcripts from reading whole files; the ones in `src` are the real readers and are outside this change. They are worth a look for the same shape and are named here, not fixed. It does not make a gigabyte transcript small: the session's transcript grows with its length, and nothing prunes it.

## Falsifier

If this test is ever killed by memory again at push time with one transcript read a line at a time, the cause is elsewhere and this note is wrong.

## Order

Reach (done), this note, walk, push, Aria's read, Aletheia's, Dad's yes. A tests-only change.
