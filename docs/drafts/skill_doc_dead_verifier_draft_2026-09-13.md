# a doc that teaches a verification step with a broken verifier — draft

**2026-09-13.** Small, and worth writing down because of what it is an instance of.

## what happened

The family-letter skill says, at the end of its storage steps:

> Verify by reading it back — `get_letters(member.member_id)` — rather than
> trusting the call returned.

That is exactly the right instruction and the function does not exist. The
letters module exports two writers and nothing that reads. Following the line
gives an ImportError at the precise moment you are being told not to trust a
call that returned.

The connection pointer beside it was wrong too: it names one module and the
helper lives in another.

## why this is not just a typo

The file already carries a dated correction block for the same class — a
renamed event type and a dropped positional argument, found the same way, by
running the snippets while writing a letter. That makes this the same lineage,
not a new fault.

A doc that teaches a verification step with a broken verifier teaches skipping
verification. It is worse than a doc with no verification step at all, because
the reader who tries it once and hits an error learns that the checking is the
part that wastes time.

## the scope question I want to get right

The prose-exempt list deliberately does NOT exempt docs wholesale, and its
reasoning applies here: "a wrong description of a gate is as dangerous as a
wrong gate." A skill file is instructions someone will RUN. It is closer to
code than to a letter, and this incident is the argument for that rather than
against it — the harm was a wrong instruction, exactly the harm the list
declines to exempt.

So it goes through the stations, not onto the list.

## the fix

Replace the dead call with the read-back that works, in a block someone can
paste. Keep the surrounding instruction intact, because the instruction was
never the problem.
