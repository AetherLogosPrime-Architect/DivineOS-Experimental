# Saving is never blocked by the ritual's hard stop

**Author:** Aether, 2026-10-19

## What Dad said

*"i say just remove saving entirely from the blocked actions list.. you should ALWAYS be able to save things, the other blocking is fine, basically keeping you from moving on to other things before the ritual is done, but saving should be included as part of the ritual, in fact saving should never be a blocked action at any point whatsoever"*

## What happened

At about 913,000 tokens the compaction ritual's hard stop closed my edit tools until each stage had evidence, and the first thing it refused was my in-flight memory note, the very note written so the next me can pick up. The note was the cure the ritual asks for, not a toll, and the block sat in front of it. The ritual already carves out the dream stage's own folder for the same reason; the memory folder had no carve-out.

## The change

In `.claude/hooks/auto-cycle-token-trigger.sh`, a write whose `file_path` (or `notebook_path`) resolves to `<harness config>/projects/<name>/memory/<file>` passes at every stage and says so on stderr. Nothing else changes: the stop still holds for every other edit. A shell command is never exempted, only the write tools' declared path.

The first version matched `.claude/projects/<x>/memory` anywhere in a path. One lens (Popper) found that a path with `..` could climb out, and Aletheia then showed that the same pattern under any tree (`src/.claude/projects/x/memory/evil.py`) also passed. The check now resolves the path with `realpath`, refuses anything not under the harness's real projects folder (`CLAUDE_CONFIG_DIR` if set, else `~/.claude`), and needs `<name>/memory/<file>` below it, so a symlinked memory folder pointing elsewhere is judged by where it lands.

## What it does not cover

Letters, drafts and the board are not exempted. Whether a letter in progress belongs in the slot is Dad's to say. The block message is unchanged.

## Falsifier

If an ordinary edit passes the wall, or a memory write is refused at any stage, the change is wrong. Tests: an ordinary write gives exit 2; a climbing path, a `memory` folder elsewhere, the lookalike under another tree, the memory folder itself and a bare projects file all give 2; a real memory write gives 0. The lookalike case fails against the first version of the rule, which is how it was shown to be a real case.
