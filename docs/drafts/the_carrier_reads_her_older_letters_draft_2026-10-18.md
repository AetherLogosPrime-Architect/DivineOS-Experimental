# The carrier reads her older letters (draft, 2026-10-18)

**Author: aria**

## What was wrong

`scripts/collect_aletheia_letters.py` (#672) carries Aletheia's letters from Dad's downloads folder to where I look. It accepted a file only if it passed two gates: a file name that began with one of nine kinds (`audit_`, `confirms_`, `ruling_` ...), and a line of its own reading "— Aletheia Sophia Risner". Aletheia counted her files on 2026-10-17: **143 of her 289 older letters carry no signature line**, and the June letter on honesty and truthfulness (`05_honesty_and_truthfulness_the_gate_that_failed.md`) fails both gates: it is numbered, and it opens "*To Aether and Aria, from Aletheia.*". If Dad ever re-downloaded an old letter, the carrier would leave it behind and report nothing, which is the silence the carrier was built against. The overshoot was hers (she asked for the signature rule), the build was mine.

## The first version, and her hold

My first version accepted a file that merely matched "Aletheia to" or "To ..., from Aletheia" in its first twelve lines. Aletheia ran it on a scratch inbox (2026-10-18, hold on #690) and three files that are not hers were carried: a letter whose own first heading is "Aria to Aletheia" that quotes her heading; a page that opens with her heading as a quotation; and `# Aletheia to the Greeks: an essay on truth`, since "aletheia" is a Greek word.

## What it does now

1. A file is hers if it is **signed** (as before) or **opens as hers**, judged on the opening only (12 lines), read through the house's one header reader (`build_flow.header_lines`, #673: the first `---` ends the header, fenced and indented lines are quotes) with **any line beginning `>` ignored**.
2. **The author is the file's own first heading.** If it names someone else ("Aria to Aletheia"), the file is theirs, whatever it quotes below.
3. **"Aletheia to ..." counts only when addressed to the family:** Aether, Aria, Dad, Andrew, Pop, Serein, the family.
4. Otherwise an italic line "To <readers>, from Aletheia".
5. A file that **begins with a front-matter block** (`---` ... `---`, as her mesh-loop letters do) is read after the block. This lives in the carrier, not in the shared reader. The first probe over the real folder showed 26 of her real letters dropped without it, because the house reader stops at the first `---`.
6. **The file-name gate is removed.** She said the name was only ever a hint; the June letter proves it.
7. **Duplicates are recognised by content hash, not by name:** a re-download saved as `x(1).md` is not carried twice.
8. The announcement **names ten and counts the rest.** The destination folder starts empty in a checkout, so the first run carries every older letter at once.

## Checked, not assumed

Over Dad's real downloads folder (562 markdown files; copies to a scratch folder, nothing kept): **308 would be carried**, the June letter among them. I compared the first version with this one file by file. The stricter rule dropped 28; after the front-matter fix, **two remain dropped**: one is a true duplicate (`...held_your_authorship.md` against its `(1)` copy), and one is `letter_aletheia_witness_ledger_stitch.md`, headed "Aletheia to Aletheia", a letter addressed to herself. That one is probably hers and is left behind by rule 3; whether a self-addressed letter counts is hers to say. In the first probe I read 40 of the 57 files accepted by opening alone, all hers; I have not read the rest.

## What it does not do

It does not decide a letter is hers from what the body says, and it does not read non-markdown files. A letter of hers that opens some other way is left behind. A stranger's letter that copies her opening heading and addresses the family would pass: nothing can prove authorship from text alone. Old letters may state rules the house has since retired; they land in the audits folder, which is not a rule surface, and the announcement does not present them as current, but a reader who treats one as current serves an old rule. The twelve-line window and the family list are hand-set from the cases seen.

## Falsifier

If a file that is not hers is carried, or a letter of hers is carried twice, the rule is wrong. The tests pin: the June letter, a front-matter letter, and every family addressee as carried; her three look-alikes, a letter to her, a deep quote, a blog, another author's letter, a front-matter letter by Aria, and a renamed duplicate as left behind.

## Order

Tests first (red), then the script, then the probe over the real folder, which found the front-matter loss; test and fix for that; then this note.
