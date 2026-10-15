# label-fire clears the marker the labelled fire armed (draft, 2026-10-16)

**Author:** Aether, 2026-10-16. Built from the 2026-10-16 deadlock, and it turns out to be most of the earlier design B in `label_fire_labels_and_clears_the_lock_it_set_draft_2026-10-09.md`, which I did not find before I built: I looked only after the code was pushed. Read that draft first; this one says where it differs.

## The problem

A false alarm from the correction-shape Stop gate cost three commands: `label-fire`, then a marker clear with quoted clauses, then a compass dismissal for the cascade the marker raised. Each manual clear landed in the escape log and read as gates being routed around. On 2026-10-16 the chain ran for hours and, with the redirect fault (the companion branch), locked every command including the doorbell.

## The design

The label is the dissent, recorded with its reason. It answers the exact claim the marker makes, so the marker clears with it. Narrow by construction: only a stop-gate marker whose trigger text equals what this fire would have written (rebuilt from the fire record's reason and confidence, cut at 200 characters). His own marker, a marker with no source, and a marker armed by a later fire all stay. Anything that fails to match leaves the marker up. The clear goes through `clear_marker()`, so the compass cascade clears with it, which closes the open item named at the end of the earlier draft.

## Where this differs from design B (2026-10-09)

- B added a `--misread-clauses` quote and ran the key's own clear, so an escape-log row was written. This does neither: the label's 40-character reason is already the quoted dissent and is appended to the corpus, so a second quote and a second record would be the toll the command was built to remove. If you want the telemetry row back, it is one line.
- B matched on `source == stop-gate` alone; this also requires the trigger to equal this fire's own text, so a stop-gate marker armed by a different fire stays.
- B refused with printed explanations for his-message and unknown-source markers; this prints "left as it was (not armed by this fire)" for every non-match. A fuller message is a follow-up.

## What it does not do

It adds no new power: `clear_correction_marker.py` with quoted clauses could already do this. It does not touch the 40-character reason minimum or the append-only corpus. A seat could still label real fires as misreadings; the corpus and the audit are the check, and Aletheia asked that the count of labels per seat stay visible to Dad (owed).

## Evidence

Eight tests; removing the clear call fails three. Walks `walk-306fba3bedc1` and `walk-bee30071bb4b`. Companion: the shared splitter fix.
