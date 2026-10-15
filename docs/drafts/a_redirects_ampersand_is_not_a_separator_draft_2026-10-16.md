# A redirect's ampersand is not a command separator (draft, 2026-10-16)

**Author:** Aether, 2026-10-16.

## The problem

The shared splitter (`split_shell_segments`) read the `&` in `2>&1` as a background separator. A command ending in `2>&1` was cut in two with a stray word `1`, so every gate that judges segment by segment saw an unknown second command behind a prescribed remedy and refused the remedy. Reproduced on the real council hook with five variants of one exit command: plain, `| tail` and `| head` passed; `2>&1` and `2>&1 | tail` were refused. That was the real cause of the 2026-10-16 deadlock (the exits were already on the shared remedy list).

## The change

An ampersand right after `<` or `>` with a digit or `-` after it (`2>&1`, `>&2`, `1>&2`, `>&-`) duplicates a file descriptor and stays inside its command. A doubled `&&`, and any other ampersand, still separate.

## What I got wrong first, and fixed before merge

The first version also kept `&>file` and `>& file` whole. They WRITE a file, and kept whole they hide the write behind an inert head like `echo`: `divineos learn x && echo y &> f` would have passed as a clean remedy where main refuses it. I found that by probing main against the change after Aletheia's first confirm, not before. The code is now narrower (descriptor duplication only), the tests pin that file-writing forms keep splitting exactly as on main, and the head moved, so her confirm at the first head needs renewing.

## And a second narrowing, from Aria's cold read

The second version looked only at the first character after the ampersand, so `>&2file` (a file NAMED `2file`), `2>&1file` and `>&²` (a superscript two, which `str.isdigit` accepts) passed as descriptor duplications. Bash treats `>&word` as a duplication only when the WHOLE word is digits or `-`. The rule now requires ASCII digits, or a lone `-`, and then the end of the text or a character that cannot continue a word (whitespace, `;`, `|`, `&`, `)`). Her three inputs are tests; replacing the rule with the old one fails the first. Credit and the reproduction are hers.

## Still open, said plainly

`echo y 2>&1 > f` and `echo y >&2 > f` now behave like `echo y > f`, which this module already accepted (a redirect to a file behind an inert head is not seen as a write). They are lines that change from refused to passed, and they join a class main already accepts; that is an older gap, not made by this change, and it is worth its own look.

## Evidence

Eleven tests in `TestAnAmpersandInARedirectIsNotASeparator`; 219 pass across command parsing, the remedy allowlist, the leading-cd matcher, the council gate and the gravity classifier. Walk `walk-d99497ee15b4`. Companion: `aether/label-fire-clears-its-own-flags`.
