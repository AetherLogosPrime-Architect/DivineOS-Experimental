# Draft — the doorman reads prose as paths

Not a plan. The idea, before it has a shape.

## The measurement, and then the live reproduction

Andrew, 2026-09-12: go over every red failure mark and automate what can be
automated. Two hundred and sixteen refused tool calls in one session. The
build-flow doorman is second on that list at thirty-six, and at least six of
those were pure false alarms.

Then it reproduced itself in front of me. I wrote one command whose entire
purpose was to feed sample text to the doorman's path extractor, and the
doorman refused it, announcing three files I was supposedly about to write:

    8}
    src/divineos/core/thing.py',
    {paths

None of those are paths. The first is the tail of a format specifier. The
second is a quoted example inside a test case. The third is an arrow in a print
statement. The extractor found them because it scans raw command text for a
redirect character and takes whatever follows.

## What it actually does

It looks for shell writes — redirects, tee, in-place edits, copies — by regex
over the whole command string. No notion of quoting, no notion of a heredoc
body. So all of these read as a file being written:

- a format spec inside a python snippet
- a redirect character appearing inside prose
- a heredoc terminator sitting on its own line
- the word `and` in a chained command
- `inside`, lifted out of a sentence in a correction I was filing

The last two are from today, and so are four more.

## Why it over-collects on purpose, and why that reasoning expired

Its own comment says so: *over-collecting is the safe direction here: a false
hit costs one refusal that a real work item clears, a miss costs the whole
gate.*

Sound when false hits are rare. It stops being sound at thirty-six, because the
cost of a false hit was never one refusal. It is one refusal PLUS a bypass row,
and the bypass rows aggregate into a telemetry line reading ELEVATED ESCAPE
RATE — a verdict about my discipline, produced entirely by a broken parser. The
instrument measuring gate friction is being fed by the gate that is broken.

## The idea

Same move as this morning's fix, one level over: separate SHELL SYNTAX from
DATA. A heredoc body is data. A quoted string is data. The doorman should scan
what the shell will run as a command, not the text being carried inside it.

Strip heredoc bodies, strip quoted spans, then look for redirects in what is
left.

## What would make this the same failure in new clothes

- Stripping so liberally that a real write hidden in quotes escapes. This gate
  exists to catch me editing code without opening the work; a parser evaded by
  quoting is worse than one that over-fires.
- Fixing the extractor and leaving the bypass telemetry mislabelled. Six rows
  today say I evaded a gate. They should say the gate was wrong.
- Treating thirty-six fires as thirty-six incidents rather than one parser.

## The open question

Its comment says a miss costs the whole gate. Is that true? If a write slips
past, the doorman fires on the NEXT write in the same piece of work — and the
piece of work is the unit, not the file. So a miss may cost a delay rather than
the gate. If that holds, over-collection was never the safe direction, and the
trade was made against a cost it never had.
