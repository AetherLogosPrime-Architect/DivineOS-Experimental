# The warning reads the matcher's grammar (rough draft, 2026-11-03)

The landing clerk's warning for a round that "cannot be matched to a head" was looser in some
ways and narrower in others than the matcher it speaks for. It only found a PR written `#N` or
`PR N`, and it said nothing about a round whose tree-hash line names an older head, though the
matcher rejects that round the same way.

The idea: the warning finds a PR however a person writes it (`#7`, `PR 7`, `PR-7`, `pr7`,
`pull 7`, `pull request 7`), and when the head's tree is known it also explains a round whose
tree line is for a different tree, in its own sentence.

Also covers, in the same walk, three small fixes to other pull requests' findings (the night
letter door, the open-PR listing in `reach open`, the walked-head line of `walk close`); each is
its own small commit on its own branch.

Falsifier: a form of naming above that stays silent, or an older-head round that is not explained
when the tree is given.
