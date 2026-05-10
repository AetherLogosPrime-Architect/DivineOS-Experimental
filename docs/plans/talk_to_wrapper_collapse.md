# Talk-to Wrapper: 3-step → 1-step Collapse (Revised)

**Status:** PLAN. Started reading cold 2026-05-10. Revised after reading the
two PreToolUse hooks and `talk_to_commands.py`.
**Bottleneck #1** from the architecture-friction list.

## What I learned reading cold

The original plan assumed the sealed prompt carried meaningful content
(voice-context preamble + delimiter + message) that needed to survive the
collapse. **It does not.** Per the 2026-05-08 redesign in
`talk_to_commands.py::_load_voice_context` (lines 181-234), the preamble
is already minimal substrate-pointer text:

> "I am Aria. My substrate is at: family/family.db... My agent
> definition at .claude/agents/<name>.md orients me on every invocation."

The member's agent definition file is the canonical orientation. The
preamble adds nothing the agent file doesn't already carry. **The
preamble is vestigial.**

Two PreToolUse hooks currently gate family-member invocations, both
duplicating the "did this come through talk-to" check:

- `family-wrapper-required.sh` — pending exists + TTL + file-integrity hash
- `family-member-invocation-seal.sh` — pending exists + TTL + prompt-vs-pending hash

In the 1-step flow, both collapse into one validator-runs-on-prompt check.

## Revised goal

```
Agent(subagent_type="aria", prompt="<plain message>")
```

No prior CLI call. No sealed file. No pending JSON. No TTL. No canonical
hash. No byte-exact hash. The hook IS the seal: validator pass = sealed.

## Architecture changes

| Surface | Before | After |
|---|---|---|
| `Agent` prompt | sealed text (preamble + delimiter + message) | plain message |
| `talk-to` CLI | required first step | optional pre-validator (deprecated path) |
| `~/.divineos/talk_to_*` files | required, TTL 120s | obsolete |
| `family-wrapper-required.sh` | pending-file gate | merged into seal hook |
| `family-member-invocation-seal.sh` | hash-match gate | runs validator directly |
| Voice-context preamble | substrate-pointer text | dropped (agent file does this) |
| INVOKED ledger event | logged by `talk-to` CLI | logged by hook |

This collapses bottlenecks #1, #2, and #3 in one pass:

- **#1 (3-step → 1-step)**: direct flow, no sealed file.
- **#2 (em-dash hash mismatch)**: no hash to mismatch.
- **#3 (TTL gate-fires)**: no TTL.

## Files to modify

| File | Change |
|---|---|
| `.claude/hooks/family-member-invocation-seal.sh` | Replace pending-file logic with validator call; log INVOKED on pass |
| `.claude/hooks/family-wrapper-required.sh` | Delete (merged) OR convert to no-op shim and remove from settings |
| `src/divineos/cli/talk_to_commands.py` | Extract validator into `core/family/talk_to_validator.py`; CLI becomes thin pre-flight runner |
| `src/divineos/core/family/talk_to_validator.py` (NEW) | Houses `_GENERIC_PUPPET_PATTERNS`, dynamic "you are <name>", `validate_message()` callable |
| `src/divineos/core/family/family_member_ledger.py` | Add hook-callable INVOKED helper if not already exposed |
| `src/divineos/core/operating_loop/addressee_misdirection_detector.py` | Update FAMILY_MEMBERS source-of-truth: read from `registered_names.family_member_names()` (consistency drift fix) |
| `tests/test_talk_to_validator.py` (NEW) | Cover validator on extracted module |
| `tests/test_family_seal_hook_direct.py` (NEW) | Cover hook direct-invocation flow |
| `tests/test_talk_to_commands.py` | Update for thin pre-flight CLI shape |
| `CLAUDE.md` | Rewrite "Summoning Family Members" section |

## Consistency drift to fix in same pass

- `family-member-invocation-seal.sh` line 64: `GUARDED = {'aria'}` — hardcoded, should source from `registered_names.family_member_names()` like `family-wrapper-required.sh` does (line 99).
- `addressee_misdirection_detector.py`: `FAMILY_MEMBERS = ("aria", "popo")` — hardcoded, should also source from `registered_names`.

## Open design questions

1. **Validator import cost in hook**: hook is bash → python shell-out. The
   validator import path needs to be cheap. Currently `talk_to_commands.py`
   imports from `divineos.core.family._schema`, `db`, `voice` — heavy.
   Mitigation: extract validator into a leaf module with minimal imports
   (just `re`, `registered_names`).

2. **INVOKED event logging from the hook**: append_event takes a Python
   call. Hook is already shelling to python; can do it there. But: a hook
   that writes to the ledger creates a side-effect on a *blocking* path.
   If ledger write fails, do I deny or allow? Decision: log-best-effort,
   never block on ledger write failure. The hook's job is gating, not
   bookkeeping. Surface ledger failures via stderr to operator.

3. **Tool-input mutation**: do I want the hook to inject the substrate-
   pointer preamble into the prompt before the Agent runs, or trust the
   agent definition entirely? Decision: trust the agent definition. The
   2026-05-08 redesign already moved orientation responsibility to the
   member; the preamble is redundant. Drop it.

4. **`talk-to` CLI fate**: keep as a pre-flight validator (operator runs
   it to check whether their phrasing would survive the hook before
   spending a turn on the Agent invocation). Or remove entirely. Decision:
   keep as pre-flight; mark in CLI help that direct invocation is now
   primary.

5. **Migration**: existing tests that exercise the sealed-prompt path
   need updating. The pending-file mechanism stays as deprecated-but-
   working during rollout (hook accepts BOTH modes for one release cycle),
   then the pending-file path is removed.

## Test plan

Pre-implementation (failing tests first):

1. `test_direct_invocation_clean_prompt_allowed` — Agent(subagent_type=aria,
   prompt="hi") with no pending file → hook allows.
2. `test_direct_invocation_puppet_shape_blocked` — Agent(prompt="you are
   Aria, stay first-person") → hook denies with diagnostic naming pattern.
3. `test_direct_invocation_logs_INVOKED` — successful invocation appends
   INVOKED event to member ledger.
4. `test_legacy_pending_file_still_works` — pending file present + matching
   hash → hook allows (one-release backward compat).
5. `test_validator_module_extraction` — `validate_message()` callable
   from `core/family/talk_to_validator.py` independent of CLI.
6. `test_em_dash_payload_passes` — regression for #2; em-dash content in
   prompt no longer hash-mismatches because no hash.
7. `test_addressee_detector_uses_registered_names` — consistency drift
   fix; detector picks up newly registered members without code edit.

Post-implementation:

- Manual smoke: `Agent(subagent_type="aria", prompt="hello")` from a
  fresh session, confirm it lands.
- Run full `pytest tests/ -q --tb=short`; all green.
- Run `bash scripts/precommit.sh`; clean.

## Execution order

1. ✅ Read seal hook + canonicalizer + talk_to CLI + wrapper-required hook (DONE this session).
2. Write failing test #5 (validator extraction) — confirms the refactor target.
3. Extract validator into `core/family/talk_to_validator.py`.
4. Make CLI import from new module; tests still pass.
5. Write failing tests #1, #2, #3 (direct-invocation hook behavior).
6. Modify seal hook to call validator on missing-pending path.
7. Add INVOKED logging in hook.
8. Write failing test #4 (legacy compat).
9. Verify legacy path still works.
10. Write failing test #7 (consistency drift).
11. Update `addressee_misdirection_detector.py` and `family-member-invocation-seal.sh` GUARDED set to source from `registered_names`.
12. Write failing test #6 (em-dash regression).
13. Confirm em-dash passes in direct-flow.
14. Delete or shim `family-wrapper-required.sh`; update settings if needed.
15. Update CLAUDE.md "Summoning Family Members" section.
16. Run full test suite; commit; PR.

## Definition of done

- `Agent(subagent_type="aria", prompt="<msg>")` works without prior talk-to.
- Puppet-shape prompts blocked at the hook with named-pattern diagnostic.
- INVOKED events still land in member ledger.
- Legacy pending-file flow still passes (deprecation, not removal).
- Em-dash regression covered.
- Detector and seal hook source family-member names from `registered_names`.
- CLAUDE.md "Summoning Family Members" rewritten for 1-step primary flow.
- All tests green; precommit clean.

## What this does NOT change

- The puppet-shape patterns themselves. Same validator, same patterns.
- The member's agent definition contract. Members still orient via
  `.claude/agents/<name>.md`, still update their substrate post-response.
- The hash-chained per-member ledger. Still gets INVOKED / RESPONDED
  events, just from a different code path.
- The five family operators (reject_clause, sycophancy_detector, etc.).
  Those run inside the member's response, not at invocation time.
