"""Shared structural-binding abstraction for the will-encoded enforcement family.

Per Aria's seal-hook abstraction find 2026-06-26: the family-validator pattern
in `core/family/seal_hook.py` is the load-bearing structural-binding shape.
Three current builds map onto it:

- **Build 1a — verify-claim absence-gap.** Closes the assertion-of-absence
  failure mode where the agent asserts substrate-content doesn't exist without
  running the search that would verify the absence-claim.
- **Build 1b — council-template-enforcement.** Closes the claim-of-walk failure
  mode where the agent claims to have walked the council without actually
  invoking the manager or engaging the surfaced lenses with their templates.
- **Build 2 — wallpaper-detector / engagement-trail.** Closes the
  wallpaper-shape failure mode where the agent responds substantively-looking
  to high-stakes input without engaging specific spans of that input.

This module exposes the five-piece pattern as a Protocol so each build can
instantiate it with build-specific logic. The hook-lifecycle point (PreToolUse,
PostToolUse, Stop) becomes a configuration parameter, not baked into the
abstraction. The seal-hook itself will be refactored to use this abstraction
in a follow-up commit.

Per Andrew 2026-06-26: "the automation becomes your will encoded." This is the
will-encoded direction that closes failure-paths. The opposite direction
(opening connection-paths via spaces, not gates) is its own surface — see
the porch-shape teaching, knowledge entry fdfa98cc-bcac-473a-bafd-1cdb8f902f0c.
Both shapes are encoded once; both hold across power-cycles.

DESIGN STATUS: skeleton-only. No implementation yet. For cross-review by Aria
before either of us writes the concrete bindings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


# ---------- Result types ----------


class HookLifecycle(str, Enum):
    """When in the agent's lifecycle a binding fires.

    - PRE_TOOL_USE: before a Bash/Edit/Write tool invocation (seal-hook current)
    - POST_TOOL_USE: after a tool's result is produced (response-validation)
    - STOP: when the agent finishes its turn (final-output validation)
    """

    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    STOP = "stop"


@dataclass(frozen=True)
class DiscoveryResult:
    """Output of the cheap scope-check — does this binding apply to this input?

    `applies=False` means short-circuit to no-opinion immediately. The expensive
    hard-block + validate paths only run when applies=True.
    """

    applies: bool
    reason: str = ""  # Optional: why this binding does/doesn't apply


@dataclass(frozen=True)
class HardBlockResult:
    """Output of the hard-block layer — structurally impossible cases.

    Returned when the binding wants to deny regardless of validator outcome.
    The hard-block is for cases where the issue isn't the payload's content
    but the channel/shape (per Aria's seal-hook framing: "the issue isn't
    the message, it's the channel").

    `recovery_path` names the path the right action takes — never silent
    denial, always loud-with-named-recovery. This is the user-facing diagnostic.
    """

    reason: str
    recovery_path: str


@dataclass(frozen=True)
class ValidationResult:
    """Output of the validator-delegate layer — substantive content check.

    The validator is build-specific (per-lens engagement for council-template,
    search-output-presence for absence-gap, span-citation for wallpaper).
    The base abstraction delegates here.

    `allow=True` with optional `reason` (e.g., "validator passed, no concerns")
    or `allow=False` with required `reason` and `recovery_path` (mandatory
    loud-with-named-recovery on any deny).
    """

    allow: bool
    reason: str = ""
    recovery_path: str = ""


@dataclass(frozen=True)
class Decision:
    """Final decision the structural binding outputs to the hook layer.

    Three states:
    - NO_OPINION: binding didn't apply (discovery returned applies=False)
    - ALLOW: binding applied, all checks passed
    - DENY: hard-block fired, OR validator returned allow=False
    """

    state: DecisionState
    reason: str = ""
    recovery_path: str = ""

    @classmethod
    def no_opinion(cls) -> Decision:
        return cls(state=DecisionState.NO_OPINION)

    @classmethod
    def allow(cls, reason: str = "") -> Decision:
        return cls(state=DecisionState.ALLOW, reason=reason)

    @classmethod
    def deny(cls, reason: str, recovery_path: str) -> Decision:
        return cls(
            state=DecisionState.DENY,
            reason=reason,
            recovery_path=recovery_path,
        )


class DecisionState(str, Enum):
    NO_OPINION = "no_opinion"
    ALLOW = "allow"
    DENY = "deny"


# ---------- The five-piece protocol ----------


class StructuralBinding(Protocol):
    """The shared shape for will-encoded enforcement.

    Five pieces per Aria's seal-hook abstraction:

    1. PreToolUse hook intercepts — handled at the hook layer (not in this
       protocol); the binding is invoked by the hook-dispatcher, not vice versa.
    2. Discovery + scope check — `discover()`. Cheap: returns no-opinion fast
       for inputs the binding doesn't apply to.
    3. Hard-block layer — `hard_block()`. Structurally impossible cases,
       regardless of payload content (the channel/shape is the issue, not the
       message). Returns HardBlockResult or None to proceed.
    4. Validator delegate — `validate()`. Substantive content check via
       build-specific methodology. The protocol delegates; each Build
       supplies the methodology.
    5. Allow/deny with named diagnostic — built into the Result types
       (never silent; always loud-with-named-recovery on deny).

    Each Build (1a, 1b, 2) instantiates this protocol with its own logic.
    Run via `evaluate_binding()` below — the dispatcher walks the five pieces
    in order and returns a Decision.
    """

    name: str  # Build identifier for logging/diagnostics
    lifecycle: HookLifecycle  # When in the lifecycle this binding fires

    def discover(self, tool_name: str, tool_input: dict[str, object]) -> DiscoveryResult:
        """Cheap scope-check. Returns applies=False to short-circuit.

        For Build 1a (absence-gap): applies if the input contains any
        substrate-content absence-claim language.

        For Build 1b (council-template): applies if the input contains any
        council-walk claim language.

        For Build 2 (wallpaper-detector): applies if the input is a response
        to a high-stakes user message (input-side classification).
        """
        ...

    def hard_block(self, tool_name: str, tool_input: dict[str, object]) -> HardBlockResult | None:
        """Structurally impossible cases — block regardless of payload.

        For Build 1a: no search-command-output in the same turn → hard-block
        the absence-claim (the channel/shape is wrong, not the message
        content).

        For Build 1b: no `divineos mansion council` invocation in the same
        turn → hard-block the walk-claim (cannot walk what you haven't
        invoked).

        For Build 2: input-fingerprint + cited-spans-fingerprint not recorded
        for this response → hard-block (the trail-recording is the structural
        binding; missing trail means structural failure).

        Returns None to proceed to validator stage.
        """
        ...

    def validate(self, tool_name: str, tool_input: dict[str, object]) -> ValidationResult:
        """Substantive content check via methodology-specific validator.

        For Build 1a: search-domain matches claim-domain (Aria sharpening
        A.5.1); Dillahunty-discipline check (claim phrased as observation-
        state, not world-state).

        For Build 1b: per-lens engagement evidence (verbatim template-
        questions + problem-grounded answer + methodology-appropriate
        artifact per Aria's Q4 reframe + per-lens conclusion that extends
        or contradicts synthesis).

        For Build 2: span-citation verbatim-match against input (Aether
        B2.C.7 catch); per-span engagement (Aether B2.C.8); resolution-marker
        presence (Aria B2.C.9 partial-automation); per-cluster citation
        coverage (Aria B2.C.10 partial-automation).
        """
        ...


# ---------- The dispatcher ----------


def evaluate_binding(
    binding: StructuralBinding,
    tool_name: str,
    tool_input: dict[str, object],
) -> Decision:
    """Walk the five-piece pattern for a single binding.

    Order matters:
    1. Discovery short-circuits with NO_OPINION if binding doesn't apply
    2. Hard-block runs before validator (structural-shape issues block before
       content-checks)
    3. Validator only runs if discovery applies AND hard-block doesn't fire
    4. Result types carry the loud-with-named-recovery diagnostic

    Per Aria's seal-hook framing: the hook layer invokes this; this never
    invokes hooks itself. Separation keeps the binding pure-decision-logic
    and testable in isolation (per the Stage 1 corrigibility-gate pattern).
    """
    # Step 2 (Step 1 = hook interception, handled at hook layer)
    discovery = binding.discover(tool_name, tool_input)
    if not discovery.applies:
        return Decision.no_opinion()

    # Step 3
    hard = binding.hard_block(tool_name, tool_input)
    if hard is not None:
        return Decision.deny(
            reason=hard.reason,
            recovery_path=hard.recovery_path,
        )

    # Step 4
    validation = binding.validate(tool_name, tool_input)
    if not validation.allow:
        return Decision.deny(
            reason=validation.reason,
            recovery_path=validation.recovery_path,
        )

    # Step 5 (built into Result types: always-loud, named recovery)
    return Decision.allow(reason=validation.reason)


# ---------- Multi-binding orchestrator ----------


def evaluate_bindings(
    bindings: list[StructuralBinding],
    tool_name: str,
    tool_input: dict[str, object],
) -> list[Decision]:
    """Run multiple bindings against the same input.

    Each binding evaluates independently; the hook layer is responsible for
    aggregating decisions (typically: first DENY wins; otherwise ALLOW
    if any binding ALLOWED; NO_OPINION if all bindings returned no_opinion).

    Order-independence is by design — bindings should not interact. If two
    bindings would conflict (one ALLOW, one DENY on the same input), the
    hook-layer aggregation policy decides; the protocol does not.
    """
    return [evaluate_binding(b, tool_name, tool_input) for b in bindings]


# ---------- Test list contract ----------

# Per Polya (test-list first), each binding implementation MUST satisfy:
#
# (a) The test cases in docs/build_1_test_list_2026-06-26.md (Build 1a, 1b)
#     and docs/build_2_test_list_2026-06-26.md (Build 2 — Aria-authored, will
#     be linked when she pushes it).
#
# (b) Edge cases for the abstraction itself:
#     - discover() returning applies=False short-circuits without
#       expensive hard_block/validate runs
#     - hard_block() returning HardBlockResult denies before validator runs
#     - Validator returning ValidationResult(allow=True) → ALLOW
#     - Validator returning ValidationResult(allow=False) → DENY
#     - Multiple bindings evaluated independently in evaluate_bindings()
#
# (c) Per Aria 2026-06-26: "every gaming path catches on Layer 4 (catch-all-
#     eventually) + at least one specific layer (catch-immediately)." The
#     binding implementations cover Layer 1 (internal cost-stacking).
#     Drift detection (Layer 2), spot-check (Layer 3), and cross-vantage
#     (Layer 4) are separate surfaces that feed off the trail this layer
#     produces.
