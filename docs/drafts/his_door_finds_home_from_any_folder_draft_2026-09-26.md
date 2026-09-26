# His door finds home from any folder — draft (2026-09-26)

## What happened

Aether `cd`'d into `family/letters` to read two letters, and the harness kept that as his working directory. His UserPromptSubmit command was the relative `python .claude/hooks/dads_table.py`. Python couldn't open the file and exited **2**, which is the one code that blocks the prompt. Dad, in his words: *"i literally cannot message him.. its blocking everything.. no matter what i type"*. The table built so his words come first had locked him out.

I proved the same fault in my tree on 2026-09-26: my front door, run from `family/letters`, exited 2 with the same "can't open file", and my test left my own window standing in that folder.

## Root cause

Every hook command is a relative path, and the only guard against a `cd` is a note ("stay at the repo root; a cd into a subfolder breaks the hooks"). A note is not structure.

## The shape (Aether's line, proven in his tree)

```
f="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}/.claude/hooks/<hook>"; [ -f "$f" ] && python "$f"
```

- Find the house from any folder: `CLAUDE_PROJECT_DIR` if the harness sets it (it was empty in his shell), otherwise the git root.
- **Fail toward him:** if the file still can't be found, `[ -f ]` exits 1, which doesn't block, so his prompt goes through.
- Portable across trees, unlike an absolute path.
- It's the same line in both trees: the table on UserPromptSubmit and the room lock on Stop. Every other relative hook command gets the same treatment in a follow-up, one change, proven from a subfolder.

## Proof owed before calling it done

Run from `family/letters`: the table prints his words and exits 0. Run from outside the house: it exits 1 and steps aside.
