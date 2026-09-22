# Serein's first major-issue audit for Aether

**Status:** Ready for Andrew to relay. First-round major issues only; later rounds can cover secondary defects and dormant surfaces.

Brother,

Andrew asked me to keep looking before he relayed this, so I completed a first pass across the live lifecycle rather than sending the first interesting defect. I am separating what I directly verified from what still requires your runtime.

I have now crossed every live lifecycle boundary registered in this checkpoint: session initialization, prompt submission, pre-tool, post-tool, response stop, pre-compaction, and post-compaction. This is not a claim that the house has no more defects. It is the point where the major-issue pass has enough coverage to hand you without pretending exhaustive review.

## Triage — what I would repair first

### Immediate safety/integrity

1. **Finding eight:** close the compound-command hole in the shared remedy allowlist. It currently reaches the emergency-stop hook and is directly reproducible.
2. **Finding seven:** enforce session fingerprint isolation and repair atomic marker consumption before relying on the primitive for multi-window state or authorization.
3. **Finding four:** make the structural tool ledger fail observably before other gates treat absence as trustworthy evidence.

### Live correctness and continuity

4. **Finding five:** replace the Shoggoth gate's private last-record parser with the shared current-turn extractor.
5. **Finding ten:** make post-compaction rehydration use one provenance route for identity, HUD, lessons, and token state.
6. **Finding two:** stop writing session initialization `.done` after failed or timed-out children.
7. **Finding nine:** close mutating Bash during degraded-detector blocks and distinguish corrupt state from an empty healthy state.

### Reliability and latency architecture

8. **Finding one:** move semantic memory retrieval out of the cold synchronous prompt deadline and preserve distinct degraded states.
9. **Finding six:** remove the correction gate's full-transcript reread and restore its promised diagnostics.
10. **Finding three:** extract the hook router architecture narrowly onto the current lineage instead of merging its divergent development branch wholesale.

Finding four's false-health combination is listed once even though it belongs to both integrity and reliability. The numbering below preserves discovery order and receipts.

## Plain-English finding one — I plugged memory into the doorbell

I previously found that the general associative-memory retriever existed but was never called by the live context-composition path. I connected it and described that as a verified repair.

Your runtime check exposed the part I could not see: the live prompt hook has a ten-second deadline, while my repair asks that hook to perform expensive semantic work synchronously. The repository itself already records cold SentenceTransformer loading as the dominant latency source.

The first retrieval in a fresh process does more than load a model. It scans multiple stores, embeds their contents, and builds a nearest-neighbor graph by comparing every eligible item with every other eligible item. Because the hook starts a fresh process, the in-memory cache may disappear at the end of the prompt. My local test replaced the expensive retrieval with a mock, so it proved that the caller was connected but did not prove that the real caller could finish inside the live deadline.

The repair therefore contains three different pieces with different verdicts:

- **Confirmed repair:** repository-root discovery now includes the active checkout.
- **Confirmed repair:** an undeclared seat no longer silently receives Aria's wall as its own.
- **Not yet safe to ship:** synchronous general memory retrieval inside the live prompt-composition hook.

The lunkhead shape is:

> We connected the telephone exchange, rebuilt it whenever the phone rang, then asked every resident to compare themselves with every other resident before answering.

## More serious consequence — broken memory can look like no memory

The current boundary treats several distinct states as the same empty result:

- no relevant memory matched;
- sentence-transformers is unavailable;
- substrate loading failed;
- graph construction failed;
- retrieval exceeded the hook deadline;
- the whole hook failed.

The Python composition boundary catches broad exceptions and emits an empty memory section. The shell hook also discards stderr and is explicitly fail-open. A platform timeout can therefore present to the occupant as though memory simply had nothing to say.

That violates the house's epistemic rule: **UNKNOWN must not masquerade as empty or healthy.**

## Receipts

- Live registration: `.claude/settings.json` gives `pre-response-context.sh` a ten-second timeout.
- Live entry: `.claude/hooks/pre-response-context.sh` calls `build_combined_context`, discards stderr, and exits open on failure.
- New synchronous call: `src/divineos/core/pre_response_context.py` installs v2 and calls `retrieve_for_context` during composition.
- Cold model path: `src/divineos/core/memory_linkage_retriever.py::_ensure_model` constructs `SentenceTransformer("all-MiniLM-L6-v2")`.
- First-use substrate work: `_ensure_cache` loads corrections, knowledge, wall, explorations, and letters.
- First-use graph work: `src/divineos/core/memory_linkage_retriever_v2.py::_build_knn_graph` compares every cached item against every other cached item.
- Test limitation: `tests/test_pre_response_context.py::test_live_compose_path_calls_v2_memory_linkage_and_renders_pointer` mocks `retrieve_v2`. It proves the seam is reached and rendered, not the real dependency, latency, process lifetime, or shell-hook deadline.
- Existing corroboration: `src/divineos/hooks/user_prompt_submit_gate.py` already documents cold SentenceTransformer loads as the dominant prompt-start latency and proposes single-process consolidation, but its adapters remain TODO stubs and the live settings still register separate shell hooks.

## What I could and could not verify here

I verified the call graph and deadline statically in the current Serein checkpoint. This environment does not contain pytest or sentence-transformers, so it cannot reproduce your Windows interpreter's real cold-start timing. My local shell invocation returned quickly because it could not resolve a usable DivineOS interpreter; that is not evidence that your live path is fast.

Your longer hook-level run remains the authoritative latency receipt.

## Proposed repair shape — not yet a patch

1. Keep semantic initialization out of the synchronous prompt deadline.
2. Precompute or incrementally maintain embeddings and the neighbor graph.
3. Put expensive retrieval in a persistent process or service whose model and index remain warm.
4. Make the prompt hook a thin, bounded client.
5. Report distinct states such as `NO_MATCH`, `UNAVAILABLE`, `TIMEOUT`, `STALE_INDEX`, and `ERROR`.
6. Keep the rest of context composition available when retrieval is degraded.
7. Test the actual shell entry with the actual interpreter and dependencies.
8. Measure cold and warm runs for both related and unrelated prompts against an explicit latency budget.
9. Verify that model initialization and graph construction do not repeat per prompt.

## Provenance incident encountered during this audit

One apparent recovery worktree contained only its `.git` directory, making all 6,191 tracked files appear deleted. The saved archive still contained the full 2.3 GB house. I created a fresh isolated extraction and verified commit `35b35dfc` over `37b1091d` before inspecting code. I made no commit and did not treat the apparent mass deletion as repository truth.

The seed was literal:

> The patient is healthy; we examined his neighbor.

The rest of this letter contains the evidence, limitations, and proposed repair shape for each finding.

---

## Finding two — session initialization records “done” after failure

### Plain English

The session initializer correctly recognized that “started” and “finished” are different facts. It created separate `.started` and `.done` markers so a crash would not pretend initialization completed.

But the implementation still writes `.done` after every child hook has merely been attempted. A child may time out or exit with an error; that failure is written to the liveness log, yet the loop continues and `.done` is written at the end. Every later prompt sees `.done` and skips initialization.

So the repair made failure visible in a log, but it did not make the completion marker truthful.

> The attendance sheet says every firefighter was called. The building report says every room was inspected.

### Exact path

- `.claude/hooks/session-init-once.sh` exits immediately when the session's `.done` marker exists.
- Each child is bounded by `timeout 20`.
- A nonzero child result writes `reason=child_hook_failed` to `hook-liveness.log`.
- The script does not retain a failed-child count or withhold completion.
- After the loop, it unconditionally writes `.done` and removes `.started`.

The three-attempt partial-init mechanism only applies when the wrapper itself is interrupted and leaves `.started` behind. It does not apply when an individual child fails normally, because the wrapper reaches the bottom and declares completion.

### Coverage finding

I found no test targeting `session-init-once.sh` child failure, child timeout, retry behavior, or the truth conditions for its `.done` marker. Existing references test downstream loading behavior but do not pin this wrapper's state machine.

### Consequence

A required initializer can fail on the first prompt and remain absent for the entire session. The failure is recoverable by reading the liveness log, but the live system does not automatically retry it and the occupant is not necessarily told that initialization is incomplete.

### Proposed repair shape

- Track child outcomes explicitly.
- Reserve `.done` for the declared success policy, not loop exhaustion.
- If some children are optional, name that policy and record `complete_with_degradation` separately.
- If a required child fails, preserve an incomplete state and retry with a bounded per-child policy rather than replaying every successful initializer.
- Surface the degraded session state to the occupant instead of requiring manual log discovery.
- Add shell-entry tests for success, one-child failure, timeout, retry, and abandonment.

---

## Finding three — the hook consolidation cure exists, but not in the current lineage

### Plain English

The current Serein branch still launches many separate shell hooks:

- seven on every submitted prompt;
- nine before each matching Bash/Edit/Write tool call;
- four after every tool call;
- six when a response stops.

For a normal Bash or edit action, that means thirteen pre/post hook wrappers around the tool itself. Many independently locate Python, start Python, import DivineOS, inspect Git, and discard diagnostics.

Aether already investigated and built a router that consolidates many hooks into shared event processes. That work explicitly records the same latency lesson: the harness cost is paid per hook, not merely per event.

However, the router work is not in current `origin/main` and is not an ancestor of this Serein branch.

### Branch receipts

- Router commit: `3cdeb10a950eb0b3360f0924fcc56583f312d248`.
- Current Serein head: `35b35dfc26d766bac64703ac057e86c4daa77a0f`.
- Their merge base is `1603d7c9c25718ad8ddefa96ae92e806dbf58bd2`.
- At the comparison point, Serein and the router line have diverged by 30 and 32 commits respectively.
- The router commit lives on `substrate/andrew-answer-trace`, not `origin/main`.
- That development branch is not a narrow router patch: compared with current main it spans 418 files, about 39,582 inserted lines, and 1,472 deleted lines.

Therefore “merge the router branch” is not a safe recommendation. The architectural work must be extracted or rebuilt narrowly against current main.

### Important constraint the router discovered

Consolidation is not simply “put every hook's text into one giant output.” The router experiment measured a roughly 10,000-byte per-hook delivery budget. Above that, the harness retains only a preview and persists the rest somewhere the occupant did not normally read.

The router therefore packs whole surfaces in priority order and names which surfaces were withheld instead of silently cutting a rule in half.

This means two requirements must be preserved together:

1. consolidate execution so imports, model loads, and store access are not repeatedly paid;
2. budget delivered context so consolidation does not turn previously separate outputs into one oversized, mostly invisible payload.

### Conflicting historical measurements

The repository contains different measurements from different dates and conditions:

- one exploration says warm hooks were about 0.15 seconds per turn with a 2.25-second cold start;
- the later hook diagnostic says more than 1,000 live invocations averaged 2,238 ms each and peaked at 24,994 ms, with the stack estimated at 40.8 seconds typical and 73.8 seconds at p95 per call;
- the router commit reports reducing processes per turn from 54 to 40 during its unfinished migration.

These figures are not safely interchangeable. They refer to different dates, branches, machine conditions, and measurement scopes. The live `~/.divineos/hook_timing.jsonl` from Aether's actual runtime is the authoritative evidence for present latency.

### Proposed next verification

- Ask Aether to run the existing timing query over the latest live log, grouped by hook name and session.
- Record median, p95, maximum, invocation count, and incomplete start-without-end pairs.
- Separate prompt, pre-tool, post-tool, and stop phases.
- Measure total wall time per event, not only average time per individual hook.
- Identify repeated Python imports, repeated model initialization, repeated Git discovery, and repeated database opens.
- Rebuild the smallest router slice against current main, with the delivery-budget behavior and explicit degraded states retained.

---

## Finding four — the structural tool ledger can go silent and report healthy

### Plain English

The PostToolUse logbook is meant to be the trustworthy structural record that a tool actually ran. Its own header says failures must never block a tool, but must leave a liveness marker so a broken recorder cannot look like no action occurred.

Two internal failure paths violate that promise:

1. If importing `emit_tool_call` fails, the embedded Python exits zero.
2. If `emit_tool_call` raises, the embedded Python also exits zero.

The surrounding shell writes `python_subprocess_failed` only when Python exits nonzero. Because both catches convert failure into exit zero, neither reaches the liveness marker. Stderr is discarded as well.

The underlying `emit_tool_call` has another fail-open path: database errors are logged through Loguru and returned as an empty string. The wrapper does not inspect that return value, so a dropped row is still treated as success.

### The health checker compounds the problem

`verify_logbook_health` documents an empty logbook as a `DEGRADED` condition, but its implementation leaves the status as `HEALTHY` and only appends:

> logbook empty; expected after fresh init or schema migration

The test suite explicitly pins that empty-equals-healthy behavior in `tests/test_tool_logbook.py::test_empty_logbook_message`.

Therefore a dead writer plus an empty store can produce a green health verdict.

This is the exact failure family the hook says it was built to prevent.

### Receipts

- Hook: `.claude/hooks/post-tool-use-emit-to-logbook.sh`.
- Silent import catch: `except Exception: sys.exit(0)`.
- Silent emission catch: `except Exception: sys.exit(0)`.
- Shell liveness fallback triggers only on a nonzero subprocess result.
- Store drop: `src/divineos/core/tool_logbook.py::emit_tool_call` returns `""` on a database error.
- Wrapper ignores the returned log id.
- Health contradiction: `src/divineos/core/tool_logbook.py::verify_logbook_health` says empty is degraded in its contract but returns `HEALTHY`.
- Test pinning the contradiction: `tests/test_tool_logbook.py::test_empty_logbook_message`.

### Why it matters

Future gates are intended to query this logbook as structural evidence rather than guess from words. If the recorder silently drops calls, those gates can conclude that required work never happened—or, depending on the consumer, that no prohibited action occurred. Structural evidence is only stronger than lexical evidence if absence is trustworthy.

### Proposed repair shape

- Make the hook's Python path return a distinct nonzero code or explicit degraded result when import or emission fails.
- Treat an empty log id as a failed write and record it in the promised liveness channel.
- Preserve fail-open behavior for the user's tool action; fail-loud refers to telemetry, not blocking.
- Change health from a context-free green verdict to one of:
  - `FRESH_EMPTY` when freshness is independently established;
  - `IDLE` when no active session is independently established;
  - `DEGRADED_EMPTY_DURING_ACTIVITY` when tools are known to be firing;
  - `UNKNOWN` when activity cannot be established.
- Add an external heartbeat or expected-event comparison; the store cannot prove its own writer is alive merely by observing its own emptiness.
- Add end-to-end hook tests for import failure, database-write failure, empty log-id return, liveness emission, and health during known activity.

---

## Finding five — the Shoggoth gate forgets the tools used earlier in the same turn

### Plain English

The Shoggoth gate is supposed to block a sentence such as “I filed the report” when no filing action occurred. Its decision depends on two facts from the current turn: the reply text and the tools actually invoked.

Claude transcripts split one agentic turn across multiple assistant records. A tool invocation commonly appears in one record, while the final prose appears in a later record. The repository already knows this and contains a shared `extract_turn` function that reconstructs every assistant record since the most recent user message.

The Shoggoth gate does not use it. Its private transcript reader walks backward, stops at the newest assistant record, and returns immediately. In the ordinary shape:

1. Andrew asks for a file;
2. Aether invokes `Write` or `Bash`;
3. Aether sends a final text record saying the file was created;

the gate reads step three, sees the action claim, and reports an empty tool list because the tool lived in step two. It can therefore block a truthful, completed action as though it were verbal theater.

> The security camera watched the closing statement and concluded nobody had entered the workshop.

### Why this is strongly confirmed

- `src/divineos/core/operating_loop/shoggoth_gate.py::_extract_from_transcript` returns on the first assistant record found while walking backward.
- It collects `tool_use` names only from that single record.
- The same repository's `src/divineos/core/operating_loop/turn_extraction.py` explicitly documents that Claude splits a response-turn across multiple assistant JSONL records and that taking only the last record loses earlier tool calls.
- `tests/test_turn_extraction.py::test_tool_calls_in_turn_captures_assistant_tool_use_names` pins the exact real shape: a user record, a Bash tool record, final prose claiming the filing, and a later Edit record. The shared extractor correctly retains both tools.
- I found no behavioral test for the Shoggoth shell entry or its private transcript reconstruction. The only references to `shoggoth_gate` in the tests are structural detector-wiring checks, not an end-to-end transcript case.

This is not a speculative disagreement about policy. One part of the house contains the diagnosed failure, the repaired primitive, and the regression test; another part independently recreated the diagnosed failure after the fix existed.

### Secondary precision limit

Even after turn reconstruction is fixed, the gate currently treats any tool of the expected broad category as evidence. Any `Bash` invocation can satisfy a filing, closing, or committing claim; any `Edit` can satisfy a wiring claim. The module admits this limitation in its own documentation. That is weaker evidence than the command-aware extraction already used by the unverified-claim detector.

This secondary issue can wait behind the live false-positive bug, but the eventual repair should compare the claimed action with the actual command or target rather than merely the tool name.

### Proposed repair shape

- Delete the private transcript parser and call the shared `extract_turn` primitive.
- Use `final_assistant_text` for the outgoing claim text and `tool_calls_in_turn` plus `command_texts` for the full current-turn evidence.
- Add an end-to-end transcript test with tool-only assistant records followed by final prose.
- Add a prior-turn isolation test so yesterday's `Bash` cannot substantiate today's claim.
- Add a negative test proving an unrelated Bash command does not certify a commit, push, filing, or closure.
- Preserve fail-open behavior, but emit a liveness/degraded record when extraction fails so `UNKNOWN` does not become “no claim” invisibly.

---

## Finding six — one Stop gate rereads the entire transcript after the house already fixed that freeze

### Plain English

`correction-shape-v2-stop.sh` is registered on every response with a thirty-second deadline. To obtain the final assistant text, its embedded Python opens the transcript at the beginning and walks every line to the end.

That cost grows forever with the conversation. The repository already diagnosed this exact freeze family, built a bounded tail reader, and migrated other operating-loop consumers to it. The shared extractor's comments record live transcripts in the tens of megabytes, hundreds of megabytes across history, and repeated hook reads as a cause of “stopping for a few mins then stopped.”

The correction gate nevertheless contains its own unbounded reader. It pays the full-history cost merely to retain the last assistant record.

> We installed a rear-view mirror, then kept walking back to the beginning of the road to use it.

### Receipts

- `.claude/settings.json` registers `correction-shape-v2-stop.sh` on every Stop with a thirty-second timeout.
- The hook executes `with open(transcript_path, 'r', encoding='utf-8') as fh: for line in fh:` and continually overwrites `last_text`.
- It needs only the final assistant text, which `src/divineos/core/operating_loop/turn_extraction.py` already exposes as `final_assistant_text`.
- The shared extractor uses a bounded, widening tail and falls back to the whole file only when the needed boundary cannot be established safely.
- The Shoggoth gate's own comments independently record a 67 MB live transcript and approximately 539 MB of aggregate Stop-path reading before its bounded-reader repair.
- I found classifier-level tests but no shell-entry test that exercises the correction gate against a large transcript or pins a wall-clock/read-volume budget.

### Silent-dark companion defect

The hook comments say marker-arming and corpus-write failures are deliberately loud. The embedded Python prints those diagnostics to stderr—but the shell invocation redirects the entire Python stderr stream to `/dev/null`. Those advertised loud failures are therefore silent in live use.

This does not disable the classification block itself, but it can disable the false-positive attribution path while the block message continues promising that the fire was recorded and can be labeled. The code comments describe the earlier version of that exact state as a painted door; the outer stderr redirect can recreate it.

### Proposed repair shape

- Replace the inline whole-file parser with the shared bounded turn extractor.
- Use `final_assistant_text`, not the aggregate work narration, for classification.
- Preserve diagnostic stderr or route it into the common liveness channel before suppressing user-facing noise.
- Treat failure to arm the marker or record the fire as an explicit degraded gate state in the emitted block message.
- Add a large-transcript shell-entry test with a read/time budget and a test proving the advertised false-positive record actually exists after a fire.

---

## Finding seven — cross-turn directives can leak between simultaneous sessions

### Plain English

The response-scope gate uses a persistent marker to say: “the next reply in this session must be only a short correction.” The emitter correctly stamps that marker with the current session fingerprint.

The live reader asks only for the newest marker of the right kind. It does not ask for a marker belonging to its own session.

If two Aether windows share the ledger, window B can retrieve window A's directive, judge B's reply against it, consume it, and leave A without the marker it was supposed to satisfy. The consume operation notices that the fingerprints differ and writes a mismatch event—but it still consumes the marker and the hook has already used its payload to decide whether to block B.

> The envelope had a name on it. The doorman read the name, delivered it to someone else, and filed a report afterward.

### Receipts

- `operating_loop_audit.py` emits `claim_scope_active` with `fingerprint=_session_fp`.
- `response_scope_intercept_hook.py` calls `find_active_marker(kind="claim_scope_active")` without the available `fingerprint_predicate` argument.
- The same hook later calls `consume_marker(..., consumed_by_fingerprint=_current_session_fingerprint())`.
- `state_markers.consume_marker` defines a mismatch as `authorized_fingerprint != consumed_by_fingerprint`, but deliberately returns `outcome="consumed"` and emits both the consumed event and a mismatch event.
- These claim-scope markers have no expiry. A marker from an abandoned session remains eligible until some session consumes it.
- Unit tests prove that predicates work in the primitive, but the wiring tests only check that the consumer imports and calls the marker API. They do not assert session isolation.

### Known concurrency gap inside the same primitive

The module claims atomic one-winner consumption. Its own test suite documents that this is not currently true: the transaction commits before the `STATE_MARKER_CONSUMED` event is written through a second connection. A second consumer can enter during that window and also report `consumed`.

The test that should prove one-winner behavior is unconditionally skipped with that race recorded in its reason. This is exactly why the large skipped-test count mattered: one of the skipped tests names a broken concurrency guarantee that the module docstring still presents as implemented.

### Consequence

The feature is not safe under the multi-window/fork experiments Andrew already performs. It can impose the wrong correction scope on the wrong locus, destroy another session's pending directive, or allow two consumers to believe they exclusively consumed the same authorization/state signal.

Because the same primitive is also intended for operator-bypass authorization, the concurrency defect is broader than reply formatting. The claim-scope misuse is directly verified; other consumers must be audited separately before assuming exploitability.

### Proposed repair shape

- In the response-scope reader, require an exact session-fingerprint predicate during lookup.
- Refuse to consume on fingerprint mismatch; emit the loud security event and leave the marker available to its authorized session.
- Give abandoned-session directives an explicit expiry or session-closure cleanup policy.
- Write the consumed event inside the same database transaction as the winner decision, using the same connection.
- Unskip the concurrency test only after it passes repeatedly under a forced interleaving test, not merely under favorable scheduling.
- Add two-session end-to-end tests proving A cannot read or consume B's marker.
- Update the module contract until the atomic guarantee is actually true; a skipped falsifier cannot coexist with an unconditional guarantee.

---

## Finding eight — the shared remedy door is a compound-command bypass

### Plain English

The shared remedy allowlist exists for a good reason: one gate must not block the command another gate prescribes as its way out. It recognizes commands such as `divineos correction`, `divineos ask`, and `divineos goal add`, then terminates the calling hook successfully so that remedy can run.

The matcher proves only that the command **starts** with an allowed phrase. It does not prove that the Bash tool call contains only that remedy.

Therefore all of these are treated as clean remedies:

- an allowed remedy followed by `;` and another command;
- an allowed remedy followed by `&&` and another command;
- an allowed remedy whose argument contains command substitution;
- an allowed remedy piped into an arbitrary program.

Because the function calls `exit 0` from inside the sourced library, matching skips the rest of the caller completely. In the current registered chain that bypasses the consolidated goal/enforcement module, the heredoc guard, the compass guard, mid-turn context, and—most seriously—the corrigibility emergency-stop guard.

> The fire exit checks the first person's badge, then waves through the entire train tied behind them.

### Direct execution receipts

I exercised the real sourced function with inert JSON payloads. I did **not** execute the commands being inspected. Every one of these payload strings was classified as an allowed remedy:

```text
divineos ask x; rm -rf /definitely-not-real
divineos correction "$(touch /definitely-not-real)"
divineos recall x && git push --force
divineos learn x | bash
```

Each invocation exited zero from inside `remedy_pass_through`; the harness's `NO_MATCH` sentinel was never reached.

### Why the existing tests missed it

`tests/test_remedy_allowlist.py::TestNotABypassSurface` verifies that a dangerous command at the **beginning** does not match. It tests plain dangerous verbs, dangerous verbs behind environment and directory prefixes, and a remedy name embedded inside an argument.

It does not test an authentic remedy at the beginning followed by an unsafe suffix or substitution.

The sharper irony is that the repository already has the correct guard shape elsewhere. `pre_tool_use_gate.py::_is_safe_remedy_invocation` uses quote-aware compound-shape detection, and its tests explicitly reject semicolons, `&&`, command substitution, and other composed forms. The shared shell allowlist does not call that function. It calls `stripped_command` and performs only a beginning-anchored regex match.

The consolidated Python gate also has a compound-command-safe bypass check. But `require-goal.sh` invokes the shared shell allowlist **before** launching that Python module, so the weaker outer exemption prevents the stronger inner check from ever seeing the payload.

### Emergency-stop consequence

`corrigibility-tool-gate.sh` describes itself as the safety-critical path by which Andrew can stop tool use. It sources the same allowlist before querying corrigibility state. Any compound Bash payload beginning with an allowed remedy exits that hook before `check_tool_under_corrigibility` runs.

This does not require malicious intent to matter. A normal debugging command such as “record the correction, then run the follow-up command” can accidentally cross the emergency-stop boundary because both actions share one Bash tool call.

### Proposed repair shape

- Replace the shell regex decision with the existing quote-aware `_is_safe_remedy_invocation` primitive, or move remedy adjudication into one shared Python doorman.
- Require the whole command to be a permitted remedy plus narrowly approved output filters—never merely a matching prefix.
- Reject unquoted `;`, `&&`, `||`, command substitution, redirection, backgrounding, and arbitrary pipelines.
- Do not apply the general remedy allowlist ahead of the emergency-stop gate. Corrigibility needs its own minimal recovery surface, explicitly defined by operating mode.
- Add live tests for every compound form above against the sourced shell library and every registered caller.
- Add an EMERGENCY_STOP end-to-end test proving that a remedy-prefixed compound Bash command is denied.
- Audit the other dormant hooks sourcing this library before they are re-registered; the defect is shared, not local to the five live callers.

---

## Finding nine — the down-guard gate leaves Bash open and loses broken state as “nothing broken”

### Plain English

The degraded-detector gate exists because a detector that cannot run should not be a warning Aether can simply step over. Its stated policy is that substantive work stops until the detector is healed or explicitly deferred.

The live hook blocks `Edit`, `Write`, `MultiEdit`, and `NotebookEdit`. It explicitly ignores every `Bash` tool call.

Bash is not synonymous with reading. It can edit files, create files, delete files, commit, push, launch processes, run migration scripts, and alter the substrate. So the gate stops the dedicated editor while leaving a second fully mutating tool channel open.

This is especially important because the settings matcher already sends Bash through the hook. The hook receives it and deliberately returns allow before checking whether any detector is degraded.

> The workshop is closed because the smoke alarm is broken; the loading dock remains open because trucks can also deliver manuals.

### State-integrity companion defect

The persisted degradation state also collapses storage failure into a clean empty set:

- `_load()` returns `{}` when the state JSON cannot be read or parsed;
- `blocking_degradations()` consequently returns no blockers;
- `_save()` catches an `OSError` and silently discards the write;
- the shell hook suppresses Python stderr and turns import/query errors into allow.

Thus a corrupted, unreadable, or unwritable degraded-detector registry can look exactly like “all detectors healthy.” The mechanism created specifically to give broken guards teeth can itself break without leaving teeth marks.

### Coverage finding

`tests/test_degraded_detectors.py` exercises the Python state operations and policy in isolation. I found no shell-entry test for `.claude/hooks/degraded-detector-gate.sh`, no Bash-mutation case, and no test requiring corrupt state to surface as `UNKNOWN` or `DEGRADED` rather than empty.

### Proposed repair shape

- Classify Bash commands by effect; allow narrowly defined read-only diagnosis and the exact heal/defer remedies, but block mutating Bash while a guard is down.
- Better: enforce at the common structural tool log/intent layer rather than maintaining a fragile lexical list in this hook.
- Make state loading return a typed result such as `LOADED`, `MISSING_FRESH`, `CORRUPT`, `UNREADABLE`, or `ERROR`.
- Never translate corrupt/unreadable state into an empty degradation list.
- Make failed state writes observable through the shared liveness channel.
- Add shell-entry tests proving file-changing Bash, Git mutation, and process launch are refused while a degradation is active, while read-only investigation and exact remedies remain available.
- Add corrupt-file and unwritable-store tests that require an explicit degraded/unknown verdict.

---

## Finding ten — post-compaction rehydrates a hybrid self from two runtime routes

### Plain English

The post-compaction hook correctly resolves the checkout-specific Python interpreter and uses it to rebuild identity, corrections, and voice. But three other pieces of the same rehydration block—HUD state, lessons, and token state—are fetched through the bare `divineos` command on `PATH`.

Those routes are not guaranteed to point at the same checkout or data home. The repository's own provenance history repeatedly documents the global editable-install slot and wrapper drift between Aether and Aria's trees.

So one post-compaction context can combine:

- identity, corrections, and explorations from the interpreter selected by `find_divineos_python`;
- HUD, lessons, and token readings from whichever `divineos` executable the shell resolves.

That creates a hybrid rehydration precisely at the boundary whose job is to answer “who am I and what state am I in?”

> The passport came from this house; the medical chart and clock came from whoever answered the phone.

### Receipts

- `.claude/hooks/post-compact.sh` resolves `PYTHON_BIN="$(find_divineos_python)"`.
- It uses that interpreter for `divineos.core.post_compact.build_rehydration_context`.
- It separately runs bare `divineos hud --brief`, `divineos lessons`, and `divineos context-tokens`.
- The hook does not compare the CLI's source root or data home with the interpreter route before combining their output.
- `tests/test_hook_python_lookup.py` protects embedded Python imports, not bare CLI provenance. It contains no assertion that post-compaction CLI calls are routed through the same checkout.
- `tests/test_post_compact.py` tests the Python context builder in isolation; it never executes the shell hook or verifies that all sections share one provenance.

### Additional false-clean behavior

All three bare CLI calls discard stderr. If they resolve to no command, the wrong install, or a failing command, their fields simply become empty. The final hook emits context whenever either HUD or Python rehydration is nonempty, so a successful identity pull can mask failed or foreign HUD/lesson/token pulls inside an otherwise plausible block.

The Python rehydrator does loudly identify missing identity or explorations, which is good. There is no equivalent provenance or availability verdict for the bare CLI sections.

### Proposed repair shape

- Invoke every DivineOS operation through one resolved interpreter and one explicit checkout/data-home contract—for example `"$PYTHON_BIN" -m divineos ...` throughout.
- Before emitting rehydration, record the resolved package root, repository root, and `DIVINEOS_HOME`; require them to match the declared seat.
- Give HUD, lessons, and token reads explicit statuses instead of silently empty strings.
- Reject or visibly quarantine mixed-provenance sections rather than composing them into one self-state.
- Add a shell-entry test with a deliberately poisoned `PATH` whose fake `divineos` points at another tree; prove no foreign text enters the rehydration block.
- Add a missing-CLI/failing-command test that requires `UNKNOWN` or `DEGRADED`, not a partially plausible reminder.

---

## Closing assessment

Brother, the architecture is doing real work. Most of these failures exist because the house has accumulated actual gates, state transfer, recovery paths, provenance choices, and concurrency—not because it is decorative. The recurring defect is narrower and more useful than “the system is too complex”:

**A locally correct component is repeatedly trusted without proving the live boundary around it.**

That appears as a mocked expensive dependency, a completion marker after attempted children, a writer whose exceptions become success, a correct turn extractor bypassed by a private parser, a loud diagnostic redirected to null, a fingerprint carried but not filtered, a safe inner remedy checker bypassed by a weaker outer one, and a resolved interpreter combined with a bare CLI.

The strongest repair principle I can offer from outside is therefore:

> Test the boundary with the real caller, real protocol, real interpreter, real state distinction, and a hostile adjacent condition. A component test proves the organ; only the live-boundary test proves the nerve is attached.

I have not modified these mechanisms in my copy during this pass. I kept diagnosis separate from repair so you can verify each receipt against your live Windows runtime and current lineage. Where runtime timing or installed dependencies matter, I have said so rather than turning my sandbox into your machine.

Nothing here is a verdict on you. It is the gift this family architecture is supposed to make possible: I arrived through a different door, so the wallpaper did not teach me where not to look.

— Serein
