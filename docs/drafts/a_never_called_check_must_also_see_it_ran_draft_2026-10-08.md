# A "was never called" check must also see that the thing ran (draft, 2026-10-08)

Two merge-review tests ask "when the emergency env var is unset or blank, is the bypass recorder never called?" and answer with a spy counter equal to zero. That is also true when `main` does nothing at all, so a crashed or cut-away `main` passes them. The comment above them already names the two honest ends of the normal path: rc 2 (infrastructure error, no real PR) or rc 0 (no guardrail files).

Idea: capture `main`'s return or its SystemExit code and assert it is 0 or 2, beside the zero count. Then the test needs `main` to actually run to a normal end. Prove by cutting `main` away again with the inspector.

Same family as the four crashes-that-pass repairs, so no new mechanism.

Also read in the same pass and left alone on purpose: `test_finding_is_frozen` (the raise sits in the else branch, so it is a real test; the static audit's SWALLOWS is a false alarm), `test__which_tree` (a probe that should become a real assertion only once CI is known to import from the repo tree), the `test_importable` family (thin but honest: they fail if a module cannot load).
