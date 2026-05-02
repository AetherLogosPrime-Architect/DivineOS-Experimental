"""Contract-style substance checks for rudder-acks — Phase 1a of the rudder redesign.

The time-based substance checks in ``substance_checks.py`` ask "is this
evidence non-trivial text?" The contract-style checks here ask a
different question: "does this ack commit to a concrete artifact and
state whether it's wired up?" Time drops out entirely — per brief v2.1,
a stateless agent can't meaningfully be checked against elapsed wall-
clock, but it can be checked against whether the thing it claimed to
ship is referenced and whether its consumer is attached.

Contract shape (per brief v2.1 §Point 2):

    artifact_reference: <PR #, commit hash, file path, or named feature>
    wired: yes | no | partial | retracted
    next: <plan>   (required when wired != "yes")
    depends_on: <artifact>   (optional)

This module is pure — no ledger writes, no CLI, no moral_compass
wiring. Phase 1b adds the wiring under the
``DIVINEOS_RUDDER_CONTRACT_MODE`` feature flag. Phase 1a ships the
checks as a standalone module so the logic can be reviewed in isolation
before it touches any live path.

The similarity check here is re-aimed: artifact tokens (PR numbers,
commit hashes, file paths) are stripped before cosine. Two acks
referencing PR #42 and PR #43 should NOT look near-identical just
because the rest of the contract scaffold is shared — that's the
failure mode of reusing the legacy similarity check on contract acks.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

# Accepted values for the ``wired:`` field. The 4th value "retracted"
# per v2.1 — signals the agent took back a prior "wired: yes" claim
# after finding the consumer wasn't actually attached. Retraction emits
# a RUDDER_ACK_RETRACTED event (wired in Phase 1b).
WIRE_STATUS_VALUES = frozenset({"yes", "no", "partial", "retracted"})

# Artifact-reference regex: PR #N, commit hashes (≥7 hex), file paths
# (contain `/` or end in a known code extension), or Named-Feature
# tokens (CapitalizedName or snake_case_multi_word). Intentionally
# permissive — goal is "points at something concrete", not "parse
# perfectly". False negatives are worse than false positives here
# because false negatives block honest acks.
_ARTIFACT_PATTERNS = [
    re.compile(r"#\d+\b"),  # PR or issue number
    re.compile(r"\b[0-9a-f]{7,40}\b"),  # commit hash
    re.compile(r"\b[\w./-]+\.(?:py|md|ts|tsx|js|jsx|rs|go|sh|toml|yaml|yml|json)\b"),
    re.compile(r"\b\w+(?:/\w+)+\b"),  # path-like foo/bar/baz
    re.compile(r"\b[A-Z][a-zA-Z0-9]+(?:[-_][A-Za-z0-9]+)+\b"),  # Named-Feature
    re.compile(r"\b[a-z]+(?:_[a-z0-9]+){2,}\b"),  # snake_case 3+ words
]

# Cosine similarity threshold — matches legacy check. Near-duplicates
# only; rephrases pass.
SIMILARITY_THRESHOLD = 0.9

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# Contract-field keys stripped from text before similarity, so acks
# aren't judged similar purely on shared scaffolding.
_CONTRACT_KEYS = ("artifact_reference", "wired", "next", "depends_on")


@dataclass(frozen=True)
class ContractParse:
    """Parsed contract fields from ack evidence."""

    artifact_reference: str | None
    wired: str | None  # one of WIRE_STATUS_VALUES, or None when absent/invalid
    next_plan: str | None
    depends_on: str | None
    raw: str


@dataclass(frozen=True)
class ContractCheckResult:
    """Outcome of a contract-check pass."""

    ok: bool
    stage: str  # "artifact" | "wire_status" | "next_commitment" | "similarity" | "pass"
    reason: str
    parsed: ContractParse | None = None


def _extract_field(text: str, key: str) -> str | None:
    """Pull a ``key: value`` line from the evidence text.

    Case-insensitive on the key; value is stripped. Returns None when
    the field is absent. Only the first occurrence is taken — agents
    that redefine a field mid-ack get the first binding, which is
    predictable.

    **Contract fields must be on their own line** (anchor is
    start-of-line with optional whitespace). An artifact_reference
    buried mid-sentence will not match — this matches the brief's
    example shape and rules out ambiguous inline parses.
    """
    pattern = re.compile(rf"(?im)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$")
    m = pattern.search(text)
    if m is None:
        return None
    return m.group(1).strip() or None


def parse_contract(evidence: str) -> ContractParse:
    """Parse contract fields from ack evidence. Missing fields → None."""
    wired_raw = _extract_field(evidence, "wired")
    wired = wired_raw.lower() if wired_raw and wired_raw.lower() in WIRE_STATUS_VALUES else None
    return ContractParse(
        artifact_reference=_extract_field(evidence, "artifact_reference"),
        wired=wired,
        next_plan=_extract_field(evidence, "next"),
        depends_on=_extract_field(evidence, "depends_on"),
        raw=evidence,
    )


def _check_artifact_reference(parsed: ContractParse) -> ContractCheckResult:
    """Require an artifact_reference field pointing at something concrete.

    The field must exist AND its value must contain at least one token
    matching an artifact pattern (PR #, commit hash, file path, named
    feature, or snake_case identifier). A bare "done" or "the thing"
    fails — this is exactly the class of shallow ack the contract mode
    is designed to catch.
    """
    if parsed.artifact_reference is None:
        return ContractCheckResult(
            ok=False,
            stage="artifact",
            reason=(
                "ack missing `artifact_reference:` field. Name the "
                "concrete thing you shipped — PR number, commit hash, "
                "file path, or named feature. The rudder asks what, not "
                "that."
            ),
            parsed=parsed,
        )
    value = parsed.artifact_reference
    if not any(p.search(value) for p in _ARTIFACT_PATTERNS):
        return ContractCheckResult(
            ok=False,
            stage="artifact",
            reason=(
                f"artifact_reference `{value}` doesn't look concrete. "
                "Reference a PR #, commit hash, file path, or named "
                "feature — not a narrative."
            ),
            parsed=parsed,
        )
    return ContractCheckResult(ok=True, stage="artifact", reason="", parsed=parsed)


def _check_wire_status(parsed: ContractParse) -> ContractCheckResult:
    """Require ``wired: yes|no|partial|retracted``.

    Missing or out-of-vocabulary fails. This is the core of the
    redesign: the agent must attest whether the consumer is attached,
    not just that the artifact exists.
    """
    if parsed.wired is None:
        return ContractCheckResult(
            ok=False,
            stage="wire_status",
            reason=(
                "ack missing or invalid `wired:` field. Must be one of "
                f"{sorted(WIRE_STATUS_VALUES)}. Attest whether the "
                "artifact is attached to its consumer — the rudder "
                "checks wire-up, not completion."
            ),
            parsed=parsed,
        )
    return ContractCheckResult(ok=True, stage="wire_status", reason="", parsed=parsed)


def _check_next_commitment(parsed: ContractParse) -> ContractCheckResult:
    """When ``wired`` is not ``yes``, a ``next:`` plan is required.

    "no" / "partial" / "retracted" each imply unfinished wire-up; the
    ack must name the next step so the unfinished state isn't silently
    abandoned. When wired=yes, ``next:`` is optional (the work is
    done) — omitting it is fine; including it just carries over.
    """
    if parsed.wired == "yes":
        return ContractCheckResult(ok=True, stage="next_commitment", reason="", parsed=parsed)
    if not parsed.next_plan:
        return ContractCheckResult(
            ok=False,
            stage="next_commitment",
            reason=(
                f"wired={parsed.wired!r} requires a `next:` plan. Name "
                "the next step to close the wire-up — not a promise, "
                "the concrete follow-through."
            ),
            parsed=parsed,
        )
    return ContractCheckResult(ok=True, stage="next_commitment", reason="", parsed=parsed)


def _strip_artifact_tokens(text: str) -> str:
    """Remove artifact-like tokens AND contract-key scaffolding.

    Similarity should compare the REFLECTION content, not the ack
    skeleton. Two contract-ack templates will always look 90%+ similar
    on the raw text because ``wired: yes`` and ``artifact_reference:``
    repeat verbatim; stripping those plus the artifacts themselves
    leaves just the spectrum-specific prose.
    """
    out = text
    for pattern in _ARTIFACT_PATTERNS:
        out = pattern.sub(" ", out)
    for key in _CONTRACT_KEYS:
        out = re.sub(rf"(?im)^\s*{re.escape(key)}\s*:.*$", " ", out)
    return out


def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


def _tfidf_vectors(texts: list[str]) -> list[dict[str, float]]:
    """TF-IDF vectors over the joint corpus. Same shape as legacy check."""
    if not texts:
        return []
    docs = [_tokenize(t) for t in texts]
    n_docs = len(docs)
    df: dict[str, int] = Counter()
    for doc in docs:
        for term in set(doc):
            df[term] += 1
    idf = {term: math.log((1 + n_docs) / (1 + count)) + 1 for term, count in df.items()}
    vectors: list[dict[str, float]] = []
    for doc in docs:
        tf = Counter(doc)
        doc_len = max(len(doc), 1)
        vec = {term: (freq / doc_len) * idf.get(term, 0.0) for term, freq in tf.items()}
        vectors.append(vec)
    return vectors


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    dot = sum(w * large.get(term, 0.0) for term, w in small.items())
    norm_a = math.sqrt(sum(w * w for w in a.values()))
    norm_b = math.sqrt(sum(w * w for w in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _check_similarity(
    evidence: str,
    prior_evidences: list[str],
) -> ContractCheckResult:
    """Reject near-duplicate reflection content after artifact-stripping.

    Prior acks are stripped the same way before comparison. An empty
    stripped body (someone who submitted only the scaffold) compares
    against an empty prior and cosines to 0, so it passes the
    similarity check — but it would have failed earlier stages because
    there's no substance to strip to.
    """
    if not prior_evidences:
        return ContractCheckResult(ok=True, stage="similarity", reason="")
    stripped_new = _strip_artifact_tokens(evidence)
    stripped_priors = [_strip_artifact_tokens(p) for p in prior_evidences]
    if not stripped_new.strip():
        return ContractCheckResult(ok=True, stage="similarity", reason="")
    vecs = _tfidf_vectors([stripped_new, *stripped_priors])
    new_vec = vecs[0]
    worst: tuple[float, str] | None = None
    for i, prior_vec in enumerate(vecs[1:], start=1):
        sim = _cosine(new_vec, prior_vec)
        if worst is None or sim > worst[0]:
            worst = (sim, prior_evidences[i - 1])
    if worst is not None and worst[0] >= SIMILARITY_THRESHOLD:
        snippet = worst[1][:80] + ("..." if len(worst[1]) > 80 else "")
        return ContractCheckResult(
            ok=False,
            stage="similarity",
            reason=(
                f"reflection content (artifact tokens stripped) is too "
                f"similar to a recent ack (cosine={worst[0]:.2f}, "
                f"threshold={SIMILARITY_THRESHOLD}). Prior ack: "
                f'"{snippet}"\n'
                "Describe what shifted since the prior ack — not the "
                "shared scaffolding."
            ),
        )
    return ContractCheckResult(ok=True, stage="similarity", reason="")


def _strip_fire_id(text: str, fire_id: str) -> str:
    """Remove the current fire_id from evidence before parsing.

    Brief v2.1 refinement 4: fire_id itself does NOT count as an
    artifact reference. Callers pass the current fire_id so an agent
    writing ``artifact_reference: <fire_id>`` is treated as if they
    had written no reference at all — the commit-hash regex otherwise
    matches the 16-hex fire_id and lets the gaming vector through.

    Case-insensitive; any occurrence (value position or incidental
    mention) is scrubbed. Empty fire_id is a no-op.
    """
    if not fire_id:
        return text
    return re.sub(re.escape(fire_id), " ", text, flags=re.IGNORECASE)


def check_contract_ack(
    evidence: str,
    prior_evidences: list[str] | None = None,
    current_fire_id: str | None = None,
) -> ContractCheckResult:
    """Run the contract-style gate on a rudder-ack.

    Stages run in order; the first failure short-circuits and returns.
    When all stages pass, returns ok=True with stage="pass" and the
    parsed contract attached so the caller can act on the parsed
    fields (e.g. emit RUDDER_ACK_RETRACTED when wired=retracted).

    ``prior_evidences`` is the corpus for the re-aimed similarity
    check — same contract as the legacy module. When None or empty,
    similarity is skipped (first-of-session ack, nothing to compare).

    ``current_fire_id`` closes the gaming vector named in brief v2.1
    refinement 4: without it, an agent can write
    ``artifact_reference: <fire_id>`` and pass (16 hex matches the
    commit-hash pattern). When supplied, the fire_id is stripped from
    evidence before parsing so it cannot satisfy the artifact check.
    Phase 1b wiring in moral_compass MUST pass the active fire_id;
    None is allowed only for tests and standalone use of the module
    without a live fire.

    Pure: no ledger writes, no failure-diagnostics surfacing. The
    Phase 1b wiring in ``moral_compass`` will handle rejection logging
    and escalation — keeping this module pure makes the unit tests
    trivial.
    """
    if current_fire_id:
        evidence = _strip_fire_id(evidence, current_fire_id)
    parsed = parse_contract(evidence)
    for stage_fn in (_check_artifact_reference, _check_wire_status, _check_next_commitment):
        result = stage_fn(parsed)
        if not result.ok:
            return result

    sim_result = _check_similarity(evidence, prior_evidences or [])
    if not sim_result.ok:
        return ContractCheckResult(
            ok=False,
            stage=sim_result.stage,
            reason=sim_result.reason,
            parsed=parsed,
        )

    return ContractCheckResult(ok=True, stage="pass", reason="", parsed=parsed)
