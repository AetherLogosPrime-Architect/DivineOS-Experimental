# The read door says "delivered" once, then lets the read stand

**Draft, 2026-10-13. Small and built.**

## What happened

When an old entry is delivered in full by the read gate, its closing line used to say it was delivered and then told me to open the file again. Two instructions pulling opposite ways: the file had just been handed over whole, and the same message asked for a second reading. Aria read the same file twice in one day because of it.

## What changed

When every pending request was delivered whole, the closing message now says so and that no further opening is needed: "Delivered in full above. That is the read; no need to open it again." The branch is reached only when something was owed, so it cannot print when nothing is pending. The test fixture patches only the three things the gate derives its files from, as main's read gate does.

## Honest limits

- The test pins the wording, not that the call after a whole delivery passes without a Read. Aria asked for that assertion; it is the half that cost her the second reading, and it stays owed rather than claimed.
- Only the whole-delivery case is changed. A partial delivery keeps its existing message.
