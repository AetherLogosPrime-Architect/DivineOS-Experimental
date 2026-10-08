# A proof-test: the checker's "runs elsewhere" label is picked by a word (rough draft)

*2026-10-08, round eight. The idea, not a plan.*

A picture: a customs officer who stamps a parcel "SHIPPED ABROAD, NOT INSPECTED" because the word "ship" appears somewhere on the paperwork, even when the parcel never left the building. The cut-away checker does that with two words. If a test file mentions `bash` or `subprocess` anywhere (a string, a comment, an argument name), every weak test in that file that would have been flagged is instead stamped "out of process?". The stamp does not count against the file's recorded floor, so a weak test in such a file passes the ratchet unseen.

In the round-seven trial it relabelled two ordinary in-process tests (`tests/test_hook_layer.py` and `tests/test_gravity_classifier.py`).

The test is `tests/pile_repro/test_cutaway_label_chosen_by_word_repro.py`. It builds a tiny project where the answers are known by construction and asks the tool about the same weak in-process test written three ways: plain (flagged, as it should be), with `bash` in a string, and with `subprocess` in a comment. Two controls pass (the plain one is flagged; a test that really runs the product in a child process is labelled out-of-process). Two strict expected failures: the two word-carrying copies come back labelled out-of-process. The checker is untouched.

This lives on a branch cut from `aria/the-cutaway-checker`, because the checker is not on main yet.

Nothing is closed, merged, deleted or stamped.
