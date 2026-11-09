# A plain "go back to my folder" is never refused (draft, 2026-11-07)

## What happened

At about 10:30 on 2026-11-07 I ran a read-only command to count letters and it began with `cd "$HOME/.divineos-shared/letters"`. The shell's working folder stayed there. From then on every Bash command was refused by hook 32 with: "divineos: no sealed venv found. Walked up from C:\Users\aethe\.divineos-shared\letters looking for a `.envrc` marker file... Fix: `cd` into your DivineOS checkout root, then rerun."

The refusal applied to the very command that would have fixed it: `cd "C:/DIVINE OS/DivineOS-Experimental-Aria-new"` was refused with the same message, and so was `cd /c/"DIVINE OS"/Div*Aria-new && pwd`. A trap with no door. About an hour of Bash was lost until the session folder was moved with the `change_directory` tool and the turn changed, and the PowerShell tool (which has its own folder) worked throughout.

## Root cause, two parts

1. Mine: I changed folders inside a command whose only purpose was to count files. A read-only count needs full paths and no `cd`.
2. The house's: the wrapper's refusal fires before the command is read, so it also refuses the `cd` that fixes it. The refusal text even tells the reader to `cd` and rerun, which cannot work.

## What would fix part 2 (not built)

A command that is nothing but a `cd` into a folder that holds a `.envrc` marker (or into the session folder) passes the wrapper, so the one move the message prescribes is always possible. The test to write first: from a folder with no marker, feed the wrapper a bare `cd <checkout>`; it must pass. Then the same with the refusal still in place for anything else.

## Where it lives (read, 2026-11-07)

Hook 32 in `.claude/settings.json` (PreToolUse, matcher `Edit|Write|MultiEdit|NotebookEdit|Bash`) is `.claude/hooks/work-item-doorman.sh`. At line 54 it runs `divineos work-item gate` with the shell's inherited folder, and at line 64 any failure becomes `exit 2`, a hold. The comment at line 36 says the old `|| exit 0` was changed on 2026-09-23 because exit 0 is ALLOW and a check that could not run must not read as a pass.

So the trap is exactly that fail-closed rule meeting a wrong folder: the `divineos` wrapper cannot find `.envrc` from outside a checkout, the doorman reads "could not run" as a hold, and the hold covers the `cd` that would fix it. The fail-closed rule is right (could-not-look is not a pass); the missing piece is that the doorman should run its CLI from the project folder (`cd "$CLAUDE_PROJECT_DIR"` before line 54), so the shell's wandering folder can never be the reason it could not look.

## Revised fix (still not built)

In `work-item-doorman.sh`, run the gate from the project directory. Test first: invoke the doorman with a working folder that is not a checkout and assert it behaves exactly as it does from inside one. Keep the fail-closed behaviour for a real failure of the CLI.

## Status

UNRESOLVED. Owed. Mine to build or Aether's, to be decided with him; nothing changed yet.
