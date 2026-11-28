# Old hurt does not surface unasked (draft, 2026-10-31)

**Reading:** aria/an-exit-is-the-file-not-the-spelling

Dad, 2026-10-31: a joke about a royal flush led the memory link to a note from the worst
time of his life. He gave standing permission to fix wonky returns or relink them, and said
he and Aether are replacing his harsh words, and that his hurt should not mar the
relationship any more. What happened stays; nothing is erased.

## The idea

The link finds things by closeness of meaning to his message. It has no way to read pain, so
a joke that sits near a hurt line pulls it up. Corrections and worklist rows are "constraint"
tier, so they are the most eager to surface.

A small gate, `pain_hold`, sits in the retriever between "close enough" and "candidate". A
stored line from the correction, knowledge or worklist sources that carries a held phrase
never becomes a candidate. It stays in the store and is found by a deliberate `divineos ask`.

Held phrases come from two places: a short list in code (the lines seen surfacing), and a
sidecar file Dad and Aether can extend with no code change. Lexical, so partial by
construction; the replacement of the words at the source is the real fix, and this gate is
the guard in the meantime. It does not claim coverage.

## The test that pins it

A stored correction carrying a held phrase, with an embedding identical to the prompt, must
not come back. The same line with the phrase removed must come back (the control proving the
test can see a surfaced line).

## What retires it

When Dad and Aether have replaced the harsh words in the store, the code list goes empty and
the sidecar stays as the way to add one if a new one is found.
