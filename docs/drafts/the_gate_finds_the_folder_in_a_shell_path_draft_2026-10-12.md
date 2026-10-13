# The lighter branch rule finds the folder in a shell-style path (draft, 2026-10-12)

## What is wrong

The lighter branch rule (#632) asks which folder a shell line acts in (`push_choke.target_dir`) so it
can tell a branch from main. When it cannot tell, it stays strict. Two ordinary ways of writing the folder
made it fail and fall back to the strict old rule on every such line:

1. A git-bash drive path, `cd /c/w-behind`. Python on Windows does not treat `/c/w-behind` as a folder.
2. A quoted folder with a space in its name, `cd "C:/DIVINE OS/DivineOS-Experimental"`. A plain `split()`
   cut the quotes and the name in half, giving `C:/DIVINE`.

Both real checkouts live under `C:/DIVINE OS/`, so the second one would have resolved the wrong folder for
nearly every line from the house itself. Found the day #632 merged, when a plain commit chain kept demanding
the old paperwork. Aria found the second half independently the same evening.

## What it does now

- `_words` reads a segment with quotes honoured (`shlex.split(posix=False)`, so Windows backslashes survive)
  and strips one matching pair of outer quotes.
- `_native_folder` turns `/c/x` into `C:/x`, only on win32 and only for a single drive letter.
- Stated limit: an UNQUOTED folder with a space still splits and lands on `None`, which is strict. Quoting is
  the contract, as a real shell needs it too.

Every failure still ends in `None`, which the caller treats as "stay strict".

## Evidence

`tests/test_gate_reads_shell_style_folder_paths.py` (quoted space, `git -C` with a quoted space, a git-bash
drive path skipped off Windows, and a control that a folder that does not exist reads as could-not-tell).
`test_the_target_folder_is_read_from_the_call_not_the_hook` now quotes its folder: it passed only where the
checkout path had no space, which is where neither of our checkouts is.

## Not checked

Shells other than git-bash; folders written with environment variables.
