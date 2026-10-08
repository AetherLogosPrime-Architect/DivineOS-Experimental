# A test must notice when the code it names is cut away

**Draft, 2026-10-07. The idea, not a plan.**

## What he said

Dad, 2026-10-07: "i heard alot of things online about testing, the fast majority of our 14k test suite is suspect, later i want to run a mega sabotage, basically disconnecting the test from EVERYTHING running it and seeing how many still go green". And later the same day: "this is why were going to sabotage everything, especially the earliest tests, to make sure there are no fake tests". And what it is for: "to help find hidden broken systems that are claiming they work so we can fix them properly". And on the fix shape: "we just have to find the root cause, and automate it so they are avoided without you having to remember".

## What exists, found by reading and not by remembering

`scripts/check_test_substance.py` (Dad, 2026-08-25: "are we sure all of the tests are legit? and not another version of 'fake greens'?") reads every test with the parser and asks whether it is CAPABLE of failing. It reports 13712 of 13844 capable (99.05%). Its own header says what it cannot see: a test that asserts something true by construction, one that asserts on a mock, one whose assertions check a trivial property. It names mutation testing as the instrument for those, and `scripts/run_mutmut.py` is that instrument: two kinds of change, eight modules, source files rewritten in place, timeouts and crashes counted as kills.

Online (Google's "State of Mutation Testing at Google", the Open Catalog of Test Smells, mutation-tool comparisons): the standard way to judge a suite is to break the code a little and see whether anything goes red; coverage alone does not say a test would fail if the logic were wrong; the named test smells include tests that assert nothing, compare a result with itself, or mock the thing under test; property-based testing and random test order are the other standard checks, and this suite uses the first in four files and the second not at all.

## What I built tonight, in a temporary folder, to find out

Two instruments, each proved on cases whose answer I already knew before I trusted it.

1. **Cut-away.** For each test, the functions of the modules the test imports are swapped in place, only while the test body runs, for ones that count a hit and crash. A test that stays green and never reached them is DISCONNECTED; one that reached them and stayed green SWALLOWED the failure; one that went red is CONNECTED. It caught five deliberate fakes of five. On the first three oldest files, 99 of 99 were connected.
2. **Line change.** One change at a time (flip a comparison, remove a not, drop a call, return nothing), tried against exactly the tests that execute that line, found by a whole-suite run that records which test covers which line. A change nobody notices is a place the tests would not catch a bug. A line no test executes is reported as uncovered and is a finding by itself.

Both instruments were wrong at first, and the ways they were wrong are the lessons: a re-exported function hid its real home, so 172 of 181 tests looked cut off when 180 were connected; tests of scripts outside `src/` and of the command line were invisible; two copies of one script loaded under two names; concurrent runs deleted each other's scratch folders; the rough first mutation pass blamed tests for failing to catch changes a test elsewhere caught. Every one of these produced a confident wrong number. Each was caught by running the instrument on a case whose answer I already knew.

## The shape

1. Move both instruments into the repo, with tests whose controls are the deliberate fakes and the honest cases, so they cannot rot into a tool that always says clean.
2. Make them cheap enough to run on what changed: on a commit, the tests staged or the tests that cover the staged modules, so a NEW fake test cannot enter. The full sweep is a scheduled job, not a thing anyone remembers.
3. Report in the three-valued way the repo already insists on: cut-off, connected, could-not-measure. A test of a subprocess is out of process, not fake. A test that needs a fixture to survive the cut is not measured, not connected.
4. File what the sweep finds as work: each DISCONNECTED or SWALLOWED test is read by a person, and either fixed (given a real assertion) or stated honestly as a test of data or of existence, never silently left.

## What it will not do

It cannot say a connected test checks the RIGHT thing; only that it depends on the code. It cannot reach code that runs in a child process. It cannot decide which surviving line change matters; equivalent changes survive honestly (clamping `x < lo` to `x <= lo` returns the same value). It does not replace reading.

## Cost

Real. The sweep is about an hour of machine time across all 995 files; the line-change pass depends on a whole-suite coverage run that records which test touches which line. The cost to run on a commit is small if it is limited to what changed. The cost of not doing it is the thing Dad named: a green number that goes up whether or not the code works.
