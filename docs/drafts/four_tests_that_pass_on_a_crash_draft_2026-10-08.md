# Four tests that pass on a crash (draft, 2026-10-08)

Same family as `a_crash_must_not_pass_for_a_refusal_draft_2026-10-07.md`, which repaired twenty-two. The cut-away check now reads four more as SWALLOWED: they reached the code, the code was made to crash, and they stayed green. Each is a different disguise for one flaw, "I check for the absence of a bad thing, so a crash looks fine".

- `test_related_empty` skips its only assertion when the setup step fails to return an id.
- `test_weight_1_no_consultation_required` asserts a refusal sentence is absent, which a crash satisfies.
- `test_weight_2_passes_with_valid_consultation` asserts two refusal sentences are absent, same.
- `test_resolve_refuses_when_there_is_no_debt` asserts exit code 1, which a crash also gives.

Idea: each test asserts the thing that SHOULD be there, taken from the real output of the real command, so a crash cannot satisfy it. Prove each by cutting the code away again and watching the test go red. Four repairs, no new mechanism, so no new infrastructure.
