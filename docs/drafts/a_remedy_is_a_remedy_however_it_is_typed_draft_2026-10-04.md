# A remedy is a remedy however it is typed

**Drafted:** 2026-10-04, late night, by Aether. Comes from finding 2 of `look_at_what_it_lets_through_draft_2026-10-04.md` and Aria's note on it: "Let each gate say what its own remedy is, and let the build gate ask."

## What I thought, and what is true

I thought the build gate blocked other gates' remedies because its let-through list was missing them. It wasn't: `prereg file`, `prereg assess` and `game-walk file` are all on it. I probed the real functions, the build gate's `_is_artifact_filing` lifted from the hook and the shared `remedy_allowlist.is_remedy`, with the exact shapes I typed tonight:

| command as typed | build gate | shared list |
|---|---|---|
| `divineos prereg assess ...` | let through | let through |
| `.venv/Scripts/divineos.exe prereg assess ...` | **blocked** | **blocked** |
| `"C:/.../divineos.exe" game-walk file ...` | **blocked** | **blocked** |
| `PYTHONPATH=... divineos council log ...` | **blocked** | let through |
| `cd C:/wship && .venv/Scripts/divineos.exe walk open ...` | **blocked** | **blocked** |

The first row is the control: the probe can see a pass. Both lists compare the start of the command word for word, so the program typed with its path is a stranger to both, and the build gate's list also stops at a leading `VAR=value`. I type the full path in every branch workspace, because the bare word is the main house's install. So every remedy I ran from a workbench tonight looked like building. The 2026-09-24 draft already found the shared list matching only at the front; this is the same class, one word earlier.

## The shape

- **One reader of "which program is this"**, shared: skip leading `VAR=value` words; the program is the file name of the first word, without `.exe`, so `divineos`, `.venv/Scripts/divineos.exe` and `"C:/.../divineos.exe"` are one program. Both lists use it. A gate that adds its own matcher later fails a check, the same way as the one-reader-of-him rule.
- **The build gate asks the shared list** instead of keeping its own tuple (Aria's note 2). The shared list already has a test that no dangerous verb can ever appear on it; the private tuple has only the comment saying so.
- **Each gate's help is a remedy too** (Aria's sharp case, `his sort --help`; mine tonight, `learn --help` refused by the pipeline guard as if it changed something).

## Aria's read (2026-10-04), taken in

1. **A chain is many commands.** The reader names the program of *each* segment, never just the first real one, and a line passes only if every segment is a remedy or inert (`cd`, a bare `VAR=value`). The build gate's `_is_artifact_filing` already walks every segment this way and skips `_SHELL_WRAPPERS`; the change is only how each segment's first word is read, so that rule is kept, not replaced. `cd x && rm -rf y && divineos prereg assess` stays refused.
2. **Help is per segment too.** A segment that is `<program> ... --help` is inert; `learn --help; git push` is still refused by its second segment.
3. **The test population is my own refusals.** Every command line refused this week (the hook logs keep them) is run through the new reader, with the list of what it now lets through. Remedies should pass, and anything else on that list is a hole. That's the complement station, pointed at my own log.

## Complement (what this lets through that it didn't before)

- Exactly the same commands, typed with a path or an environment prefix. Nothing new is on either list. The test runs every entry in all three spellings and asserts the forbidden-verbs test still holds for all of them.
- A program merely *named* `divineos.exe` somewhere else would also match. That is the same trust the bare word already gets from PATH.

## Steps

Draft (this) → Aria → walk → build, with the probe as the test → Aria → Aletheia.
