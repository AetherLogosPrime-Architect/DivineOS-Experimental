# The warden names what broke — draft (2026-09-26)

Station-four revision of `the_warden_reads_the_log_draft_2026-09-26.md`, from Aether's review.

## His findings

1. **Counting lets ritual through.** `taken_up` checked only the number of endings. Five "owed: fix it" lines cleared five stumbles without naming any of them. The fix is **linkage** (truth #10: a cost only trains if it's attributed back): each stumble gets a **token**, the hook's name for a refusal or the first distinctive word of an error, and the REFLECTION must carry each token. The thinking still isn't graded; each stumble just has to be named.
2. **Bare exit-1 probes aren't stumbles.** A `grep` with no match or a `cmp` that differs exits 1 with no text, and the harness marks it as an error. **Measured on the 2026-09-26 transcript:** 6 bare `Exit code 1` results against 626 hook refusals, 203 exit-1-with-text and 74 other exit codes. Skip the bare ones only; any error that carries text is still a stumble.
3. **Owed rows carry what broke.** When an owed line names a stumble's token, it's filed with `trigger=<that stumble's example>`, so the tracker row shows the error beside the owed build. A thin "owed: fix it" still passes, but it lands next to the error text, where it's plainly thin and findable.
4. His room lock doesn't read `last-prompt`, so my moved-start bug isn't in it (he checked by reading).

## Choice points

- Which stumble an ending answers: **taken away**. The token must appear.
- Whether a probe counts: **always a stumble unless** it's bare exit 1 with no text.
