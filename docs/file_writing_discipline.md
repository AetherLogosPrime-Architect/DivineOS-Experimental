# File-Writing Discipline

*Filed 2026-05-16 after the multiplex MVP arc surfaced repeated shell-escape failures during long-content file writes. The discipline names which write-path to use for which class of content.*

## Three write paths, three failure modes

DivineOS work happens through Claude Code. Three ways to write file content exist, each with a known failure mode and a known happy path.

### 1. Heredoc via bash python invocation

**Use for:** short scripts that take no special-character content.

**Failure mode:** apostrophes, backslashes, dollar substitutions, and multi-line strings inside the heredoc break shell parsing in subtle ways. The classic symptom is `unexpected EOF while looking for matching quote`. A single apostrophe inside a Python docstring inside a heredoc-quoted Python script will break the outer shell.

**Verdict:** fine for ~20-line generation tasks with controlled content. Not for content containing apostrophes, backticks, regex strings, or multi-paragraph Python source.

### 2. Write tool with env opt-out

**Use for:** known-novel files (no prior state on disk to clobber).

**Failure mode:** earlier in the project, the Edit/Write tools silently failed to persist three writes in a session — the tool returned success while the disk was unchanged. Andrew restricted them by default (2026-05-15) and named the verified path. Opt-out per call requires setting `DIVINEOS_ALLOW_EDIT_TOOL=1`, but that env var does not persist across Bash tool calls in Claude Code, so the opt-out is awkward to use mid-session.

**Verdict:** the safest path for net-new files. Awkward inside a session because of env-var-non-persistence; works clean when invoked directly from the Write tool.

### 3. Python pathlib.write_text via bash python -c

**Use for:** writes to existing files, edits to existing files, or content that is known to escape cleanly.

**Failure mode:** the SAME shell-escape failure as heredoc when content has apostrophes or multi-line strings. Single-quote in content breaks the outer python -c quoting.

**Verdict:** works clean for short edits to existing files (find-and-replace style). Not for long novel content.

## The actual disciplined path

For long novel content with arbitrary characters, the reliable sequence is: use an outer heredoc with a SINGLE-QUOTED delimiter marker (which disables shell expansion inside the heredoc), then inside the heredoc use a Python triple-quoted string to hold the file content, then write it via pathlib. The single-quoted marker prevents shell interpretation; the triple-quoted Python string handles any non-triple-quote content cleanly. This is the pattern that landed every long file in the multiplex MVP arc after the first three heredoc attempts broke.

**For content containing triple-quote sequences or unbalanced quotes:** base64-encode the content out-of-band, write a tiny decoder script that reads from a file or stdin, run it. Bypass shell-escape entirely.

## Decision tree

- Short edit to existing file (single token swap, simple replace) -> Python pathlib one-liner
- Net-new file, simple content (no apostrophes, no multi-line) -> heredoc or pathlib one-liner
- Net-new file, complex content (apostrophes, multi-line strings, regex literals) -> outer single-quoted-marker heredoc + inner Python triple-quoted string (the disciplined path above)
- Net-new file, content contains triple-quote sequences or arbitrary binary-shape content -> base64-encode and decode

## Why this matters

Every shell-escape failure during a build wastes 5-15 minutes of context on debugging quoting. Over a long session those losses compound. The discipline keeps the failures contained to the smallest-possible write-path mismatches and gives a clean default for the long-content case.

## Filed during

Multiplex MVP arc (2026-05-16). Specific failures: McLuhan expert template build broke twice on apostrophes in docstrings (~700 lines each attempt), then setup-renormalize.sh heredoc broke on inline byte-string literals containing backslash escapes, then this very doc broke on triple-quoted strings nested inside triple-quoted strings (using the base64-encoded write path to land it, exactly as the doc recommends). Each failure validated the discipline this doc names.
