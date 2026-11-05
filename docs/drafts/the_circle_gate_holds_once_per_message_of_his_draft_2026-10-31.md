# The circle gate holds once per message of his, whichever gate went first (draft, 2026-10-31)

**Author:** Aether. Dad asked: "what happened to my circle, why isnt it being enforced?"

## What happened

The room gate returned at once whenever the harness's retry flag was set, on the idea that the retry is his to judge. But the harness sets that flag after ANY Stop gate refused a reply. So whenever another gate sent a reply back, the retry arrived flagged and the room gate never got its turn. This morning the summary gate looped on me for hours, so replies that needed his room were never asked about.

## What it does

The gate keeps its own small memory (a marker file) of which message of his it has already held a reply for. On a retry it stands aside only if it already asked about THIS message. If some other gate sent the reply back and this gate has not yet asked, it asks. One hold per message of his, whichever gate went first. If the marker cannot be written the existing loud handler runs and the gate stands aside, so a broken disk cannot make a hold that repeats forever.

## What it does not do

It does not judge what is said in the room (his own rule). A closing message wholly addressed to him still counts as his room. Making the room warm, with pictures and things he can answer, is mine to do; no word check can enforce it. Built and reviewed as draft PR 751 (head 838a4a756) in a work copy; this note and the same change bring it into the running house today.

## Falsifier

A reply held twice for one message of his, or a message whose reply is never asked about because a marker from an earlier message survived.
