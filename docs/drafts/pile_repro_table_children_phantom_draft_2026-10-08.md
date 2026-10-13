# A proof-test for the hook check that never looks at Dad's table (rough draft)

*2026-10-08, round five, errand two. The idea, not a plan and not a fix.*

A picture: a building inspector who checks that every door listed on the front-office board leads to a real room. A second board hangs in the corridor, the table where Dad's per-message hooks are listed, and the inspector never reads it. If someone writes a door on that board that leads nowhere, the inspector walks past and reports "all doors good".

The phantom check reads the settings file only. This adds one test that fails today because a table entry pointing at a script that does not exist is not reported, and passes the day the check also reads the table. Controls show the check is alive: a missing script named in the settings IS reported, and every entry in the live table points at a real file today.

Not in scope: repairing the check.
