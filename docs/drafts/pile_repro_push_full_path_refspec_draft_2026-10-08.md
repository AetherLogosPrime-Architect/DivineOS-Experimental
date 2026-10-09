# A proof-test for the push helper and the full branch path (rough draft)

*2026-10-08, round five, errand two. The idea, not a plan and not a fix.*

A picture: a postman who delivers a parcel to the right house, then goes back to the depot and reports "undelivered" because the address on the slip was written in the long form (street, town, county) and his checklist only knows the short form.

The push helper handles `HEAD:branch`. When the branch is named by its full path (`HEAD:refs/heads/branch`) the push lands but the helper looks the branch up by a doubled name, can't find it, and reports a silent failure with exit 22. This adds one test that fails today for exactly that reason and passes the day the helper is repaired, plus controls that show the short form and the landing itself are alive.

Not in scope: repairing the helper.
