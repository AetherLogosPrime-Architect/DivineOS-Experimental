# The shell reader sees the whole line — station one draft, 2026-09-24

**Aria.** The idea, not a plan. Built on Aether's read of the doorman merge
conflict, which he measured, not remembered.

## Why this is a build and not a tidy-up

The doorman is the front of the build flow. A write it cannot see is work
that skips every station without anyone choosing to skip. So a hole in the
shell reader isn't a parser nicety. It's a door with no inspector.

## What was found

Aether replayed every distinct Bash command on this machine (87,926) through
both doorman readers, main's regex set and my branch's tokeniser, and read
the disagreements. The tokeniser wins overall: main was blind to 661 quoted
in-repo write targets. But he found two real shapes that main caught and the
tokeniser loses:

1. **Two heredocs reusing one delimiter.** The second `cat > file <<'EOF'`
   vanishes. Real hits in the corpus include a test file and a hook
   residual.
2. **A line continuation before a command word.** `&& \` then a newline, then
   `cp a b`. The backslash-newline was turned into a placeholder glued to
   `cp`, so the command word stopped being `cp`. Only command-word writers
   were lost (cp, mv, sed -i, tee); redirects survived. That's why it hid.

Checking his two by hand, I found two more that **both** readers share, which
means no comparison between them could ever surface them:

3. **A redirect after the heredoc opener on its own line.**
   `cat <<'EOF' > tests/x.py` reports nothing. The body was taken to start
   right after `<<'EOF'`, when the shell starts it on the next line.
4. **A command chained after the opener.** `cat > a <<'EOF' && cp a tests/b`
   loses the copy for the same reason.

## The shape of the fix

- Walk the heredocs line by line, the way the shell reads them. The bodies
  follow the opener's line, one after another, in opener order. Quoted
  bodies are dropped as data, unquoted bodies are kept and scanned (Knuth's
  rule stands), and an unterminated one leaves the rest to be scanned as
  shell.
- A backslash before a newline (or CRLF) is deleted, as the shell deletes it.
  It isn't an escaped operator. The escaped-operator case (`echo \>`) must
  still hold.

## Pins, written first and seen failing

`tests/test_the_shell_reader_sees_the_whole_line.py`: nine failed before the
fix, and three controls passed as they should (an escaped operator is a word,
a quoted body is data, CRLF continuation).

## What this doesn't do

It doesn't make the reader see writes made by a program the command runs
(`python -c`, a scratch script) or targets built from variables. The module
already says so, and the doorman's second instrument is what changed on disk.

## Station two: the walk (walk-6bc5491434b2, eight lenses, closed)

What changed the build:

- **Dijkstra, dissenting.** Line structure and token structure were tangled.
  Deleting backslash-newline in the token layer comes *after* the heredoc
  walk has already split physical lines, so `cat <<'EOF' && \` followed by
  `cp a b` on the next line still sends the copy into the body. **Fix:** join
  continuations into the logical line inside the line walk, before looking
  for openers. This is a fifth hole, found by the walk. None of my pins had
  it.
- **Wayne.** Every hole lives in a combination (heredoc × continuation ×
  chaining × delimiter reuse). **Add a cross-product pin:** each writer
  shape, crossed with each wrapper.
- **Popper, with the falsifier set before running:** rerun Aether's replay
  through the fixed reader. New detections should appear only in heredoc and
  continuation shapes, none should be lost, and none should appear anywhere
  else. One lost detection falsifies the fix.
- **Pearl and Hofstadter.** The two readers share an ancestor
  (`strip_quoted_heredocs` was "carried here from" `shell_code_only`), so
  their agreement proves nothing, and selecting on their disagreements hides
  every shared error by construction.
- **Jacobs.** The fix belongs in the shared module, where every door that asks
  gains it. The doorman's on-disk witness stays the second pair of eyes.
- **Maturana and Varela.** Pins must include shapes the reader has never
  produced, not only regressions.
- **Polya.** Residual, named rather than fixed: an opener inside quotes is
  still taken for an opener. It only eats lines if a later line is exactly
  the word.

The manager also named two never-invoked lenses as a fit, which the walk
wouldn't take, so they're recorded here. **Shannon:** two encoding layers
decoded by one decoder; decode lines first, then tokens. That's the same
conclusion as Dijkstra, from another axis. **Holmes:** the write nobody
reports is the dog that didn't bark. The standing way to hear it already
exists: files changed on disk, set against files the commands were read as
writing.

The walk's own instrument reported finding distinctness at a mean of 0.456,
against 0.21–0.27 for real walks and 0.44 for restatements. So by that
measure my findings read closer to each other than a good walk's do. Part
of that is one narrow problem giving shared vocabulary. Part may be me
writing all eight in one voice. The Dijkstra finding changed the artifact,
which is the test that matters, but the number is recorded as it came.

## The lesson under it

A disagreement between two instruments only finds the cases where they
disagree. Two readers that share a blind spot agree on it perfectly. Rule 9's
corollary, one level up: two confirmations from one *family* of method are
one confirmation.
