# The build step for the council count fixer (rough draft)

*2026-10-08. The idea for the build, not a plan.*

The first draft says why. This one says what the build is, in a picture: add the missing hose. A small function that rewrites the first number in each of the six council phrasings, shaped like the command-count fixer beside it (raise-only, with the same escape to lower), reading the phrase list the checker already owns so the two cannot disagree, and called from the fix path next to the others.

The test comes first: it fails because the function does not exist, then passes once it does. Seven parts: a control that the checker reads each phrasing, the fixer existing, each phrasing raised, never lowering by default, lowering when asked, an untouched doc, and the fix option actually calling it.
