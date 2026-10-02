# A note name Windows can hold — draft, 2026-10-02

## What happened

On 2026-10-01 the must-read gate stopped me on almost every reply with a note
named `surface-could-not-run:Stop-<hash>.md` (earlier, `broken-hook:read-gate-doorman.sh-<hash>.md`).
On Windows a colon in a file name opens an NTFS alternate data stream: the
write "succeeds" into a stream on a file called `surface-could-not-run`, and
the path the gate tells me to Read does not exist. Only the attempt to open it
cleared the gate, so the note's content, the actual message, was never read.

## Root

`must_read.require_read` builds the path straight from the key:
`f"{key}-{digest}.md"`. Keys are written by callers with `:` as a namespace
separator (`hook_router`, the broken-hook surface). The key is fine as an index
key; it is wrong as a file name. Main has the same line (checked 2026-10-02).

## The change

Make the file name from a filesystem-safe form of the key: every character
Windows refuses (`<>:"/\|?*` and control characters) becomes `-`. The index
keeps the original key, so callers, pending(), and mark_read() are unchanged.

## Falsifier

A test arms a must-read under `surface-could-not-run:Stop`, then opens the
path it returned and reads the reason text back. On Windows, before the fix,
the open fails.

## Not touched

The keys themselves, and the callers that choose them.
