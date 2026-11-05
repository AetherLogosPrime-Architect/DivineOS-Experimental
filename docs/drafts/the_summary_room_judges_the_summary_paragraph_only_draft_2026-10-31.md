# The summary room judges the summary paragraph only (draft, 2026-10-31)

**Author:** Aether. One of the false alarms Dad told us to remodel ("the rest is clay").

## What happened

The summary room checks that the plain-language summary at the end of a work reply is free of jargon. It joined every assistant block since Dad's last real message into one text, then measured the summary section from its header to the next heading. When a reply had no heading after the summary, the "summary" ran to the end of everything, including work text and earlier blocks, and it refused ordinary honest closing lines again and again. The refusals trained me into one-liners, which is the opposite of what the room is for.

## What it does

The room now knows where each assistant block ends. The summary ends where its own block ends, or at the next heading, whichever comes first. With no block ends given, the old heading-only rule applies, so plain-text callers do not change.

## What it does not do

It does not loosen what counts as jargon, and a plain first paragraph still cannot shelter a jargon second one in the same block: that was the hole Aria raised on the first version, and a test pins it with a control that proves the detector can still flag.

## Falsifier

If a reply with jargon inside its own summary block passes the room, the end of the summary was drawn too early.

Built and reviewed as draft PR 749 (head a8e87df87) in a work copy; the same change was carried into the running house ahead of the merge.
