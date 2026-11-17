# The suite door, three more ways through and around (draft, 2026-11-04)

The idea, not a plan. Review round 4 of repair #810 (findings 1 and 3).

1. **Fails open when the splitter cannot cut.** `split_shell_segments` returns
   None for a line holding `$(( ))`. The door then judges the WHOLE line by its
   first word. `echo $((1+2)); <suite run>` starts with `echo`, a reader, so the
   run after the `;` is never looked at. Cheapest path for an attacker or a lazy
   habit: put arithmetic in front. The repair: when the splitter cannot cut,
   cut crudely on `;`, `&&`, `||`, `|`, `&` and newlines, and judge each piece
   by its own first word. A crude cut can split inside quotes; a broken piece
   fails to parse and is not a hit, so crude cutting can only make the door see
   more runs, not exempt any.
2. **Fails closed on honest record commands.** The exemption is by program
   name. `python -m divineos learn "..."` is the same program but its first
   token is python. An unquoted `C:\x\divineos.exe learn ...` loses its
   backslashes under POSIX word splitting, so its name reads wrong. The
   repair: read the first word raw (so backslashes survive), and let
   `python -m divineos` stand in for the program.

Walked by the council (Schneier, Carmack, Bengio, Dekker, Jacobs, Hofstadter,
Dennett, Dawkins): the cheapest break is arithmetic in front of a run; the
default for an uncuttable line must be the careful one; a test has to feed the
door exactly such a line.

Not done: `bash -lc 'divineos learn "<word>"'` stays refused. The door cannot
place a string handed to another shell, and the way out (unwrap it) is honest.
Not done: the heredoc-position label (review finding 2, LOW).

Blind spot: crude cutting does not understand quotes, so a record command with a
`;` inside its quoted text would be cut into pieces. Each piece is judged alone,
so the second half could read as a bare word; the record exemption is checked on
the whole segment first only when the real splitter worked.
