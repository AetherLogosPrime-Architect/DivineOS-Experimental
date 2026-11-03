# A letter may open with front matter and still declare what it read

The idea, not a plan. `header_lines` ends the header at the first `---`. A letter
that opens with a front-matter block (`---`, `key: value` lines, `---`) therefore
has an empty header, and a `**Reading:**` line placed after the block is never seen.

The fix: the header starts at line 0, unless line 1 is exactly `---`, a closing `---`
sits within 12 lines, and every line between is `key: value`. Then the block is
skipped and the header begins after the closing rule. Anything else behaves as before,
so a pasted `---` lower down, an unclosed rule, or a block with a prose line in it
is not front matter. A `Reading:` inside the block credits nothing, because the
block is skipped, not read.

Cannot see: whether any real letter on disk opens this way; the 12-line limit is the
design's number, not measured.
