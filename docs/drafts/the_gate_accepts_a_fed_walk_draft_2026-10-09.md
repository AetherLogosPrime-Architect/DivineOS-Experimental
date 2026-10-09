# The gate accepts a fed walk (draft, 2026-10-09)

## What was wrong

The council gate lets a command through without a fresh walk only when every piece of it is a filing command. The walk command reads its reflection from stdin, and its own help prescribes feeding it with `echo` piped in. The gate counted the `echo` as a separate act that was not a filing command, so it refused the form its own help prescribes (psf-05479077, ten repeats). The usable path became writing the text to a file first.

## The change

`_is_artifact_filing` now remembers which separator ended each piece. A piece is skipped as not-an-act only when ALL hold: it starts with `cat`, `echo` or `printf`; it is piped (`|`) straight into a following piece; it has no redirect token; no token carries a dollar sign or backtick. Everything else must still be a filing command. The final line of the function is unchanged.

## What it does not loosen

A feeder with a redirect, with command substitution, piped into a non-filing command, chained with `;` or `&&`, or ending in a dangling pipe is still refused. Each has a test.

## Proof

`tests/test_the_filing_exemption_reads_the_whole_command.py`: three positive shapes that fail on main and pass now, six refusals that pass before and after.

## Review

Guardrail file, so full review before merge to main. Three-lens walk filed (Schneier, Dijkstra, Yudkowsky), council-cf47937e7bad.
