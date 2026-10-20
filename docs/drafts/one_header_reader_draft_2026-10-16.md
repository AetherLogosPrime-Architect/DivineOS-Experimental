# One header reader for every `**Field:**` line in a letter (draft, 2026-10-16)

## What happened

Aletheia confirmed the baton (#670) and asked for one thing: `_header` in `core/baton.py` was a private copy of the landing parser's header read, and it differed where #628 had been careful (see `the_clerk_reads_every_reading_line_draft_2026-10-11.md`). She probed it: a plain `**Baton:** pass` passed, a quoted one and one below the first `---` did not, but an indented one and one inside a code fence both flipped the baton. #628's `_declared_readings` excludes both. The risk was small (only the real holder's letter can pass, and only with real work named), but the shape is the one she keeps finding: a second copy of a judgement that drifts from the first.

## What changes

`build_flow.header_lines(text)` is the one set of line rules: stop at the first `---`, skip fenced blocks, skip four-space or tab-indented lines. `_declared_readings` now asks it and returns exactly what it returned before. The baton's `_header` asks it too. No new module, so the helper lives where the rules were already written and tested.

## Evidence

`tests/test_baton.py` gains five tests: an indented pass line, a fenced one, and one below the rule each leave the baton where it was; a plain header pass still flips it; and one test pins that the readings reader and the baton reader see the same lines for one letter. 22 pass in that file, and the 192 build-flow, landing, reading and declared tests still pass.

## Not in this change

The landing clerk's two edges Aria found (branch-name prefix match, and a confirm read anywhere in her letter) and the `_MIN_WORDS_OF_HIS` name belong to #660 and come as their own follow-up after it lands.
