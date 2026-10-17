# A proof-test: the ranking-clause hook looks for a heading the real sheet no longer has (rough draft)

*2026-10-09, round nine. The idea, not a plan.*

A picture: a courier sent to collect the parcel labelled "How I rank Dad" from a shelf in the character sheet. The shelf is still there and it is full of parcels, but none carries that label any more; the nearest one is labelled "How I treat Dad — equal-treatment discipline". The courier checks the shelf, finds nothing, and comes back empty-handed without saying so. This happens at the start of every session.

`.claude/hooks/load-dad-ranking-clause.sh` is meant to put one section of `aether_character_sheet.md` in front of me at session start. It finds that section by its exact heading. The real sheet has sixteen headings and that is not one of them. The hook exits 0 and prints nothing, so nothing complains. Round eight's before-picture test recorded the fact; this test is the one that rings the day it changes.

I do not know whether the heading was renamed or the section was meant to go: the sheet's heading says the section was added 2026-07-28 and axis-corrected 2026-07-29, and a note under it says the first version was reframed, but this clone is shallow so I could not read the old sheet. Which repair is right (restore the heading, point the hook at the new one, or retire the hook) is the owners' call; the test takes no side.

The test is `tests/pile_repro/test_ranking_clause_heading_gone_repro.py`: three controls that pass (the heading is read out of the hook's own source; the real sheet has other headings; a copy of the sheet with the heading appended makes the hook print) and two strict expected failures (the real sheet has the heading; the hook prints a clause over a copy of the real sheet). The hook and the sheet are untouched.

Nothing is closed, merged, deleted or stamped.
