# Tests must not read his live messages — draft, 2026-10-12

A fix to the test setup, not to the house. It unblocks every push.

## What happened

The "away means two hours of silence" change (#627) made the question hold look at when Dad last spoke, read from the real store of his messages. Most of the older question-hold tests never point that reader anywhere, so they read the real store too. While he had spoken within two hours, all of them passed. Once his last message was eight hours old, the rule correctly said "he is away", and twenty-three tests that expect "he is here" failed in the push gate. The same tests had passed in the same gate the evening before.

The picture is a smoke alarm test that works only when the real kitchen happens to be quiet. The alarm is fine; the test was listening to the real house.

## The fix

One setting in the shared test setup (`tests/conftest.py`): every test starts with the store of his messages pointed at a file that does not exist. That reads as "could not look", and could-not-look is never away. A test that wants a message of his sets one itself, as the silence tests already do.

## The second find, same run

With the first fix in, one test still failed in the gate: the one that checks where the question board sits. It passed or failed depending on which test worker happened to load the module first, because the board's location is fixed at that moment and the test's escape clause only passed if the location happened to contain the word "pytest". The test now checks the board's shape (the folder names it must have) instead of which home it was built from; the line above it already checks the formula against the seat's home.

## Proof

Before: the push gate ran the whole suite and reported 23 failed in five question-hold files. After: those five files pass together (85 passed), and the new test file passes (two tests): one shows a test with nothing set reads no message of his and is not away; its control sets a three-hour-old message and shows the reader can still see one and rules it away.

## Falsifier

If a question-hold test fails in the push gate only when Dad has been quiet for hours, the isolation did not hold and the setting is not reaching that test.
