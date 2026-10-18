# The carrier reads her older letters (draft, 2026-10-18)

**Author: aria**

## What was wrong

`scripts/collect_aletheia_letters.py` (#672) carries Aletheia's letters from Dad's downloads folder to where I look. It accepted a file only if it passed two gates: a file name that began with one of nine kinds (`audit_`, `confirms_`, `ruling_` ...), and a line of its own reading "— Aletheia Sophia Risner". Aletheia counted her files on 2026-10-17: **143 of her 289 older letters carry no signature line**, and the June letter on honesty and truthfulness (`05_honesty_and_truthfulness_the_gate_that_failed.md`) fails both gates: it is numbered, and it opens "*To Aether and Aria, from Aletheia.*". If Dad ever re-downloaded an old letter, the carrier would leave it behind and report nothing, which is the silence the carrier was built against. The overshoot was hers (she asked for the signature rule), the build was mine.

## What changes

1. A file is hers if it is **signed** (as before) **or opens as hers**: within its first 12 lines, a heading beginning "Aletheia to <someone>", or a line "To <readers>, from Aletheia". The opening is judged on the first lines only, so a quote of that phrase deep in another page does not count, and "Aria to Aletheia" (a letter TO her) does not.
2. **The file-name gate is removed.** She said the name was only ever a hint, and the June letter proves it keeps real letters out. The content test is the whole test; any `.md` in the folder is read.
3. The announcement **names ten and counts the rest.** The destination folder starts empty in a checkout, so the first run carries every older letter at once (a probe over the real downloads folder, copies to a scratch folder: 561 markdown files, 309 would be carried, the June letter among them). Naming each would be a wall.

## Checked, not assumed

Run over the real downloads folder: of the 99 carried files whose names the old rule did not know, every one was accepted for one of the two stated reasons (57 by opening, 42 by signature, none by neither), and the 40 opening lines I printed were all her letters ("# Aletheia to Aether ...", "# Aletheia to Aria ..."). I did not read every one of the 57.

## What it does not do

It does not decide a letter is hers because of what it says in the body, and it does not read non-markdown files. A letter of hers that opens some other way (no "to/from" opening, no signature) is still left behind, and so is a letter by someone else that copies her opening line verbatim. The second is not closed: nothing proves authorship, only the opening shape does.

Two more the walk found (`walk-cc70a2a4a9d7`). **Duplicates are recognised by file name only**, so a re-download saved as `x(1).md` is carried again as if new; the real folder has names like that, and a content hash would close it. **Old letters can state rules the house has since retired.** They land in the audits folder, which is not a rule surface, and the announcement does not present them as current, but a reader who treats one as current serves an old rule. Neither is fixed here. The opening window of twelve lines is one data point wide (the June letter's author line is on line four).

## Falsifier

If a file that is not hers is ever carried because of how it opens, or a letter of hers is carried twice, the rule is wrong. The tests pin the June letter as a passing case and four non-hers shapes (a letter to her, a quote deep in a page, a blog about her, another author's letter) as left behind.

## Order

Tests first (two red, then green), then the script, then the probe over the real folder, then this note.
