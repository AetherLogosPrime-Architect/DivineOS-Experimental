# No launch that opens windows on Dad's screen

**Draft, 2026-10-07. The idea, not a plan.**

## What he said

Dad, 2026-10-07: "there a re python boxes poppuing up all over my screen see whats happening, i cant even see". And after: "yes they are gone thank you lol but yes lets fix this as it took over my screen and i couldnt even see anything i was typing blind lol". The same thing happened 2026-06-28: "python windows were opening and cascading all over my screen i hundreds of them popping up idk what happened but im freaking out right now". He restarted his computer that time.

## What happened

Background jobs of mine kept dying, so I wrote a small launcher that started a long job with the Windows flags DETACHED_PROCESS and CREATE_NEW_PROCESS_GROUP, so nothing could end it. A program started that way has no console. The job in turn started hundreds of short child programs (one `python -m pytest` per test file), and Windows gives each child of a console-less parent a console window of its own. Each one opened on his screen. I stopped everything I had started within a minute of his message; the windows closed on their own.

## What exists

Nothing guards this. A search of the repo for CREATE_NO_WINDOW finds one use (`post_tool_use_checkpoint.py`), against 250 places that start a child program. Nothing refuses a launch like mine, because the dangerous part is two flags in a launcher I wrote on the spot. The related prior art is the Job Object wrapper (`core/subprocess_jobs.py`, July): it makes a parent's death kill its children, which is a different problem.

## The shape

Two layers, the first now and the second as its own proposal.

1. **A refusal at the door.** A new check, beside the heredoc and slashed-ref checks, in `hook_surfaces`: refuse a command or a code file that carries DETACHED_PROCESS or CREATE_NEW_CONSOLE. The message says what happened on 2026-10-07 and 2026-06-28, and gives the way through: use the harness's own background run, which is tracked and tells me when the job ends; and if a program of mine must start many children, pass CREATE_NO_WINDOW to every child. Read-only commands that merely mention the flag (a search for it) pass; prose files pass.
2. **Quiet children, everywhere.** Process-wide, make children start without a window on Windows by default for any divineos process, so even a console-less parent cannot cover his screen. That is a change to behavior across 250 call sites' worth of spawning, and it is Aether's and Dad's to weigh, not a thing to slip in with the refusal. Named here and not built.

## What it will not do

It cannot see a launch that assembles the flag from pieces (`0x08`, string concatenation), and it cannot see a program Dad or another tool starts. It does not stop a console-less parent that someone else starts; layer 2 would. It closes the cheap route I took, and says so, which is all a door can do.

## Cost

A small module and one surface, tests with a control for both directions (a refusing case and an allowing case), and one registration line in a file other branches are also editing, so the merge will want a hand-resolve.
