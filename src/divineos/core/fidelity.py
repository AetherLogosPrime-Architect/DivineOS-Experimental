"""Data Fidelity System.

Manifest-receipt pattern for verifying data integrity.
Every message stored must be retrievable byte-for-byte identical.

Key concept:
- Manifest = what we intend to store (before)
- Receipt = what actually got stored (after)
- Verify = compare them, they must match exactly
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FidelityManifest:
    """What we intend to store."""

    count: int
    content_hash: str
    bytes_total: int


@dataclass
class FidelityReceipt:
    """What actually got stored."""

    count: int
    content_hash: str
    bytes_total: int
    stored_ids: list[str] = field(default_factory=list)


@dataclass
class FidelityResult:
    """Result of comparing manifest to receipt."""

    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content, truncated to 32 chars."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


def create_manifest(messages: list[dict[str, Any]]) -> FidelityManifest:
    """Create a manifest for a batch of messages to be stored."""
    if not messages:
        return FidelityManifest(count=0, content_hash="", bytes_total=0)

    combined = ""
    total_bytes = 0

    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False, sort_keys=True)
        combined += str(content)
        total_bytes += len(str(content).encode("utf-8"))

    return FidelityManifest(
        count=len(messages),
        content_hash=compute_content_hash(combined),
        bytes_total=total_bytes,
    )


def create_receipt(stored_events: list[dict[str, Any]]) -> FidelityReceipt:
    """Create a receipt from stored events (read back from DB)."""
    if not stored_events:
        return FidelityReceipt(count=0, content_hash="", bytes_total=0, stored_ids=[])

    combined = ""
    total_bytes = 0
    stored_ids = []

    for event in stored_events:
        payload = event.get("payload", {})
        content = payload.get("content", "")
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False, sort_keys=True)
        combined += str(content)
        total_bytes += len(str(content).encode("utf-8"))
        stored_ids.append(event.get("event_id", ""))

    return FidelityReceipt(
        count=len(stored_events),
        content_hash=compute_content_hash(combined),
        bytes_total=total_bytes,
        stored_ids=stored_ids,
    )


def reconcile(manifest: FidelityManifest, receipt: FidelityReceipt) -> FidelityResult:
    """Compare manifest to receipt. All checks must pass."""
    result = FidelityResult(passed=True, checks={})

    count_match = manifest.count == receipt.count
    result.checks["count_match"] = count_match
    if not count_match:
        result.errors.append(f"COUNT MISMATCH: expected {manifest.count}, got {receipt.count}")
        result.passed = False

    if manifest.count > 0 and receipt.count == 0:
        result.checks["no_total_loss"] = False
        result.errors.append("TOTAL DATA LOSS: all messages lost")
        result.passed = False
    else:
        result.checks["no_total_loss"] = True

    hash_match = manifest.content_hash == receipt.content_hash
    result.checks["hash_match"] = hash_match
    if not hash_match:
        result.errors.append(
            f"HASH MISMATCH: content was modified. Expected {manifest.content_hash}, got {receipt.content_hash}",
        )
        result.passed = False

    bytes_match = manifest.bytes_total == receipt.bytes_total
    result.checks["bytes_match"] = bytes_match
    if not bytes_match:
        delta = manifest.bytes_total - receipt.bytes_total
        if delta > 0:
            result.warnings.append(f"BYTE LOSS: {delta} bytes missing")
        else:
            result.warnings.append(f"BYTE GROWTH: {-delta} extra bytes (unexpected)")

    return result


def verify_single_event(event: dict[str, Any]) -> tuple[bool, str]:
    """Verify a single event's content matches its stored hash."""
    payload = event.get("payload", {})
    content = payload.get("content", "")
    stored_hash = payload.get("content_hash", "")

    if not stored_hash:
        return False, "NO_HASH: event has no content_hash"

    if isinstance(content, dict):
        content = json.dumps(content, ensure_ascii=False, sort_keys=True)

    computed = compute_content_hash(str(content))

    if computed != stored_hash:
        return False, f"HASH_MISMATCH: stored={stored_hash}, computed={computed}"

    return True, "OK"
