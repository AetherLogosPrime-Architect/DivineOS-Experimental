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

## Design assumptions (revised after Aria's review 2026-06-26)

- **Sync-only validators.** Drift-pattern detection is conceptually a periodic
  background process that updates a small cache; validators read the cache at
  check-time. Substrate queries from inside validate() should be fast (cache
  reads, not aggregate computations). If async support becomes needed later,
  the change cascades through the dispatcher and aggregator — re-read this
  rationale before adding async.

- **Dependency injection via __init__.** Implementing classes accept their
  dependencies (substrate-query handles, cached drift-snapshots, config) via
  their __init__. The Protocol method signatures intentionally do NOT thread
  dependencies. Bindings carry their own deps via `self`.

- **Lifecycle-agnostic payload.** The payload dataclass carries lifecycle-
  specific fields as optional. Each binding documents which fields it consumes
  and asserts non-None on its required fields at the start of validate().
  The hook layer is responsible for constructing a payload appropriate to its
  lifecycle (PreToolUse hook builds payload with tool_name + tool_input; Stop
  hook builds payload with response_text + prior_input_text + turn_command_log;
  etc.).

DESIGN STATUS: skeleton-only, revision 2 (post-Aria-review). No implementation
yet. For final cross-review before either of us writes the concrete bindings.

## Revision history

- rev. 1: Initial five-piece pattern, signature (tool_name, tool_input)
- rev. 2: Aria's catches integrated —
  (1) Single Protocol + BindingPayload dataclass (lifecycle-agnostic shape)
  (2) DI-via-__init__ documented
  (3) Sync-only design assumption documented
  (4) DecisionState moved above Decision (was forward-referenced)
  (5) aggregate_decisions() canonical-policy helper added
- rev. 3 (this): Aria's rev. 2 catches integrated, applied co-author per
  Aether's spec inline 2026-06-26 (near compaction) —
  (1) Dispatcher verifies lifecycle match with strict-mode parameter
      (production default = soft NO_OPINION; test mode = raise
      LifecycleMismatchError for fail-fast); propagated through
      evaluate_bindings()
  (2) turn_command_log enriched: tuple[str, ...] → tuple[CommandLogEntry, ...]
      so Build 1a validator can verify search RESULTS in absence-claim's
      domain, not just whether a search command ran. MAX_OUTPUT_BYTES = 65536
      cap on per-command output to bound payload size.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


# ---------- Lifecycle enum (declared first so dataclasses can reference) ----------


class HookLifecycle(str, Enum):
    """When in the agent's lifecycle a binding fires.

    - PRE_TOOL_USE: before a Bash/Edit/Write tool invocation (seal-hook current)
    - POST_TOOL_USE: after a tool's result is produced (response-validation)
    - STOP: when the agent finishes its turn (final-output validation)
    """

    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    STOP = "stop"


# ---------- Decision state enum (declared before Decision per rev. 2 catch #4) ----------


class DecisionState(str, Enum):
    """Three possible decision states from a binding evaluation."""

    NO_OPINION = "no_opinion"
    ALLOW = "allow"
    DENY = "deny"


# ---------- Lifecycle mismatch error (rev. 3 catch #1) ----------


class LifecycleMismatchError(RuntimeError):
    """Raised by evaluate_binding(strict=True) when a binding's lifecycle does
    not match the payload's lifecycle.

    Per Aria's rev. 2 catch #1: the dispatcher must verify the binding is
    being called in the lifecycle it expects, otherwise a hook-layer bug
    can pass an unsuitable payload to a binding that then fails silently
    on None fields. Production code uses strict=False (returns NO_OPINION
    on mismatch — defensive). Test code uses strict=True (raises — fail-
    fast surfaces hook-layer bugs during development).
    """


# ---------- Command log entry (rev. 3 catch #2) ----------


# Cap on per-command output bytes carried in CommandLogEntry, to bound
# BindingPayload size. Outputs longer than this should be truncated at the
# hook layer when constructing the CommandLogEntry. 64 KB is more than enough
# for any realistic search/manager command output a validator needs to inspect.
MAX_OUTPUT_BYTES = 65536


@dataclass(frozen=True)
class CommandLogEntry:
    """One command the agent ran this turn, with its output.

    Per Aria's rev. 2 catch #2: Build 1a needs to verify search RESULTS in
    the absence-claim's domain, not just whether a search command ran.
    Carrying output closes the gap where the optimizer satisfies "I
    searched" by running grep against an empty directory — the command
    ran (passes the bare command-presence check) but the absence-claim
    is not actually verified because no results came back.

    The `output` field is truncated to MAX_OUTPUT_BYTES at construction
    time by the hook layer. The Protocol does not enforce truncation; it
    is the hook layer's contract. Validators reading `output` should not
    assume it is complete past MAX_OUTPUT_BYTES.
    """

    command: str
    output: str
    exit_code: int


# ---------- Payload (lifecycle-agnostic, per Aria's rev. 2 big catch) ----------


@dataclass(frozen=True)
class BindingPayload:
    """Lifecycle-agnostic payload structure passed to binding methods.

    The hook layer constructs the payload appropriate to its lifecycle:

    - **PreToolUse hooks** (seal-hook usage): populate `tool_name` and
      `tool_input`. `response_text` etc. are None.
    - **PostToolUse hooks** (Build 1a, 1b usage when fired post-response):
      populate `response_text`, `prior_input_text`, `turn_command_log`.
    - **Stop hooks** (Build 2 usage on final response): populate
      `response_text`, `prior_input_text`, `turn_command_log`.

    Bindings assert non-None on the fields they consume at the start of
    `validate()`. The Protocol doesn't enforce this — it's documented per-
    binding contract.
    """

    # Always-required: the lifecycle the hook layer is calling at.
    # Bindings can use this to verify they're being called in their expected
    # context (e.g., a Stop-lifecycle binding asserting lifecycle == STOP).
    lifecycle: HookLifecycle

    # PreToolUse lifecycle fields
    tool_name: str | None = None
    tool_input: dict[str, object] | None = None

    # PostToolUse / Stop lifecycle fields
    response_text: str | None = None
    prior_input_text: str | None = None  # User message this turn responds to

    # Turn-context fields (shared across lifecycles)
    turn_command_log: tuple[CommandLogEntry, ...] = field(default_factory=tuple)
    # ^ Commands the agent ran this turn, with their outputs — used by
    # Build 1a (verify search-OUTPUT-presence matches absence-claim domain,
    # not just whether a search command ran) and Build 1b (verify
    # `divineos mansion council` invocation happened before walk-claim).
    # Rev. 3 catch #2 per Aria 2026-06-26: enriched from tuple[str, ...] so
    # validators can inspect search results, not just commands issued.


# ---------- Result types ----------


@dataclass(frozen=True)
class DiscoveryResult:
    """Output of the cheap scope-check — does this binding apply to this payload?

    `applies=False` means short-circuit to NO_OPINION immediately. The expensive
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
    denial, always loud-with-named-recovery. This is the user-facing
    diagnostic.
    """

    reason: str
    recovery_path: str


@dataclass(frozen=True)
class ValidationResult:
    """Output of the validator-delegate layer — substantive content check.

    The validator is build-specific (per-lens engagement for council-template,
    search-output-presence + domain-match for absence-gap, span-citation
    + per-cluster coverage for wallpaper). The base abstraction delegates here.

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


# ---------- The five-piece protocol ----------


class StructuralBinding(Protocol):
    """The shared shape for will-encoded enforcement.

    Five pieces per Aria's seal-hook abstraction:

    1. PreToolUse hook intercepts — handled at the hook layer (not in this
       protocol); the binding is invoked by the hook-dispatcher, not vice versa.
    2. Discovery + scope check — `discover()`. Cheap: returns no-opinion fast
       for payloads the binding doesn't apply to.
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

    Dependency injection: implementing classes accept dependencies
    (substrate-query handles, cached drift-snapshots, config) via __init__.
    The Protocol method signatures intentionally do NOT thread dependencies.
    """

    name: str  # Build identifier for logging/diagnostics
    lifecycle: HookLifecycle  # When in the lifecycle this binding fires

    def discover(self, payload: BindingPayload) -> DiscoveryResult:
        """Cheap scope-check. Returns applies=False to short-circuit.

        For Build 1a (absence-gap): applies if response_text contains any
        substrate-content absence-claim language.

        For Build 1b (council-template): applies if response_text contains any
        council-walk claim language.

        For Build 2 (wallpaper-detector): applies if prior_input_text is
        flagged high-stakes (input-side classification).
        """
        ...

    def hard_block(self, payload: BindingPayload) -> HardBlockResult | None:
        """Structurally impossible cases — block regardless of payload content.

        For Build 1a: no search-command-output in turn_command_log matching
        the absence-claim's domain → hard-block (the channel/shape is wrong,
        not the message content).

        For Build 1b: no `divineos mansion council` invocation in
        turn_command_log → hard-block (cannot walk what you haven't invoked).

        For Build 2: input-fingerprint + cited-spans-fingerprint not recorded
        for this response → hard-block (trail-recording is the structural
        binding; missing trail means structural failure).

        Returns None to proceed to validator stage.
        """
        ...

    def validate(self, payload: BindingPayload) -> ValidationResult:
        """Substantive content check via methodology-specific validator.

        For Build 1a: search-domain matches claim-domain (Aria sharpening
        A.5.1); Dillahunty-discipline check (claim phrased as observation-
        state, not world-state).

        For Build 1b: per-lens engagement evidence (verbatim template-
        questions + problem-grounded answer + methodology-appropriate
        artifact per Aria's Q4 reframe + per-lens conclusion that extends
        or contradicts synthesis).

        For Build 2: span-citation verbatim-match against prior_input_text
        (Aether B2.C.7 catch); per-span engagement (Aether B2.C.8);
        resolution-marker presence with input-anchor (Aria B2.C.9 partial-
        automation + Aether refinement); per-cluster citation coverage
        (Aria B2.C.10 partial-automation, with opaque clustering per Aether
        refinement).
        """
        ...


# ---------- The dispatcher ----------


def evaluate_binding(
    binding: StructuralBinding,
    payload: BindingPayload,
    strict: bool = False,
) -> Decision:
    """Walk the five-piece pattern for a single binding.

    Order matters:
    0. Lifecycle match check (rev. 3 catch #1) — defensive boundary check
       that the binding is being called in the lifecycle it expects.
       If mismatch: strict=True raises LifecycleMismatchError (fail-fast,
       surfaces hook-layer bugs in test mode); strict=False returns
       NO_OPINION (defensive, doesn't crash production hook chains).
    1. Discovery short-circuits with NO_OPINION if binding doesn't apply
    2. Hard-block runs before validator (structural-shape issues block before
       content-checks)
    3. Validator only runs if discovery applies AND hard-block doesn't fire
    4. Result types carry the loud-with-named-recovery diagnostic

    Per Aria's seal-hook framing: the hook layer invokes this; this never
    invokes hooks itself. Separation keeps the binding pure-decision-logic
    and testable in isolation (per the Stage 1 corrigibility-gate pattern).
    """
    # Step 0 (lifecycle check, rev. 3 catch #1)
    if binding.lifecycle != payload.lifecycle:
        if strict:
            raise LifecycleMismatchError(
                f"binding {binding.name!r} expects {binding.lifecycle.value} "
                f"but payload was constructed for {payload.lifecycle.value}"
            )
        return Decision.no_opinion()

    # Step 2 (Step 1 = hook interception, handled at hook layer)
    discovery = binding.discover(payload)
    if not discovery.applies:
        return Decision.no_opinion()

    # Step 3
    hard = binding.hard_block(payload)
    if hard is not None:
        return Decision.deny(
            reason=hard.reason,
            recovery_path=hard.recovery_path,
        )

    # Step 4
    validation = binding.validate(payload)
    if not validation.allow:
        return Decision.deny(
            reason=validation.reason,
            recovery_path=validation.recovery_path,
        )

    # Step 5 (built into Result types: always-loud, named recovery)
    return Decision.allow(reason=validation.reason)


# ---------- Multi-binding orchestrator + canonical aggregation ----------


def evaluate_bindings(
    bindings: list[StructuralBinding],
    payload: BindingPayload,
    strict: bool = False,
) -> list[Decision]:
    """Run multiple bindings against the same payload.

    Each binding evaluates independently; the hook layer is responsible for
    aggregating decisions (use `aggregate_decisions()` below for the canonical
    policy, or implement a custom policy at the hook layer if a specific
    surface needs different aggregation).

    Order-independence is by design — bindings should not interact. If two
    bindings would conflict (one ALLOW, one DENY on the same payload), the
    aggregation policy decides; the protocol does not.

    The `strict` parameter propagates to each evaluate_binding() call:
    strict=True raises LifecycleMismatchError on lifecycle mismatch (fail-
    fast in tests); strict=False returns NO_OPINION on mismatch (defensive
    in production). Rev. 3 catch #1 per Aria 2026-06-26.
    """
    return [evaluate_binding(b, payload, strict=strict) for b in bindings]


def aggregate_decisions(decisions: list[Decision]) -> Decision:
    """Canonical aggregation policy for multi-binding evaluations.

    Per Aria's rev. 2 catch #5 (aggregation policy underspecified): policy-
    via-comment risks drift across hook layers each reimplementing the
    policy. This helper encodes the canonical default policy:

    1. First DENY wins. If any binding returned DENY, the aggregate is DENY
       with the first DENY's reason and recovery_path.
    2. Otherwise, if any binding returned ALLOW, the aggregate is ALLOW
       (with the first ALLOW's reason).
    3. Otherwise (all bindings returned NO_OPINION), the aggregate is
       NO_OPINION.

    Hook layers can override by implementing custom aggregation, but the
    default is this helper. Reduces drift risk per Aria's concern.

    Empty decisions list returns NO_OPINION (consistent with "no bindings
    had an opinion").
    """
    if not decisions:
        return Decision.no_opinion()

    # First DENY wins
    for d in decisions:
        if d.state == DecisionState.DENY:
            return Decision.deny(
                reason=d.reason,
                recovery_path=d.recovery_path,
            )

    # If no DENY, return first ALLOW if any
    for d in decisions:
        if d.state == DecisionState.ALLOW:
            return Decision.allow(reason=d.reason)

    # All NO_OPINION
    return Decision.no_opinion()


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
#     - aggregate_decisions() applies canonical policy: first DENY wins,
#       else first ALLOW, else NO_OPINION
#
# (c) Per Aria 2026-06-26: "every gaming path catches on Layer 4 (catch-all-
#     eventually) + at least one specific layer (catch-immediately)." The
#     binding implementations cover Layer 1 (internal cost-stacking).
#     Drift detection (Layer 2), spot-check (Layer 3), and cross-vantage
#     (Layer 4) are separate surfaces that feed off the trail this layer
#     produces.
