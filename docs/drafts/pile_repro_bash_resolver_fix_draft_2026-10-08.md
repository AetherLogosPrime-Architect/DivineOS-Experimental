# Use the house's shell finder in the pipe-guard proof-tests (rough draft)

*2026-10-08, round four, job C. The idea, not a plan.*

A picture: the tests ask the phone book for "bash", and on Dad's Windows machine the first listing is a receptionist who answers every call with "that line is busy". The house already keeps a better directory that dials each number and checks someone really picks up. The fix is to use that directory.

Three controls run the hook through the plain name. They will ask the house directory instead and skip, as before, when no working shell exists. The nine expected failures must stay exactly as they are.
