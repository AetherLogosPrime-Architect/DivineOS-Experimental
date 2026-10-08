# A crash must not pass for a refusal

**Draft, 2026-10-07. The idea, not a plan.**

## What he said

Dad, 2026-10-07: "this is why were going to sabotage everything, especially the earliest tests, to make sure there are no fake tests", and what it is for: "to help find hidden broken systems that are claiming they work so we can fix them properly".

## What the sabotage found

The cut-away sweep (see `a_test_must_notice_when_its_code_is_cut_away_draft_2026-10-07.md`) replaces the code under test with a stub that crashes, only while a test body runs. 22 tests reached the crashed code and stayed green. Reading them, one shape covers almost all of them: a test of a command that asserts it FAILED, or asserts a message is ABSENT, and nothing more.

- `assert result.exit_code != 0` (a command "refuses"): a crash exits non-zero too, so a command that dies on startup passes the same test as one that refuses for the right reason. Seen in `test_void_cli` (show missing, force required, high bar refused), `test_actor_authenticity_phase1`, `test_backlog_commands`, `test_cli` (learn invalid type), `test_talk_to_commands` (puppet patterns rejected, exit 1).
- `assert "X" not in result.output` (a warning "does not fire"): a command that crashed before printing anything has no X either. Seen in `test_audit_source_ref_required` (five tests whose own comments say the round "may succeed or fail for unrelated reasons"), `test_decision_family_gate`, `test_cli::test_knowledge_after_init_loads_seed`, `test_noninteractive_safety`, `test_goal_check_surface` ("does not mutate" is satisfied by a dead command).
- `or "error" in output or "no" in output` disjunctions (`test_cli` analyze tests): any of three outcomes passes, one of which is "no", a word almost any output contains.
- Early `return`s that skip a test when something is absent (`test_orientation_prelude`, three tests in `test_audit_source_ref_required` when not in a git repo, or no origin ref): a green that never ran.

This is the "Unknown Test" and "weak assertion" family in the test-smell catalogs, and it is exactly the class the static audit (`check_test_substance.py`) calls CAPABLE of failing, because an `assert` is present. Capable of failing is not the same as able to tell a crash from the right answer.

## The shape

For each of the 22: run the command for real, read what it actually prints and exits with, and pin THAT: the exit code AND the specific refusal text for a refusal; for an "absent" test, positive evidence that the command ran (its success text or exit 0) before asserting the absence; for a self-skipping test, a real skip (`pytest.skip` with a reason, which is reported) or a real fixture so it does not return silently. Then re-run the cut-away on those files: each must turn from SWALLOWED to CONNECTED. That re-run is the proof the fix worked, not my reading.

## What it will not do

It fixes the 22 the sweep reached. The same shape surely exists in tests the sweep could not reach (code run out of process, 918 tests) and in tests that never touch the code at all (the DISCONNECTED set). The repeated shape is the finding; a standing check for it (a refusal test with a bare nonzero-exit assertion and no output assertion) is the structural follow-up, filed after these are fixed so the pattern is learned from real cases.

## Cost

Reading and running 22 commands, editing 12 test files, and one re-run of the cut-away. Small next to what it protects: the claim that these commands refuse what they should.
