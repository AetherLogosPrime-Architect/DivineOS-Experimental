# The reflection note is recognised in the forms it is really run (draft, 2026-11-04)

## What happened

The check that a filed reflection-note retires a stumble only recognised a plain `divineos reflection-note` (with an
env prefix or an unquoted path). A second reader found real forms it missed: a quoted executable path,
`python -m divineos reflection-note`, `divineos --quiet reflection-note`, `bash -c '...'`, `time`/`then` prefixes, and
a note that follows an unquoted apostrophe (`echo it's fine; divineos reflection-note ...`, where the splitter took
the apostrophe for a quote and swallowed the semicolon). Each fails toward re-holding, so a note that was filed was
asked for again.

## Fix

The regex accepts those prefixes; a `bash -c "..."` wrapper is opened and its inner command read; an apostrophe
inside a word is not a quote. The segment must still START with the command, so echo, grep and a commit message that
carry the words are still not notes.

## Tests

Each missed form counts; echo/grep/commit/`echo python -m divineos reflection-note` still do not.
