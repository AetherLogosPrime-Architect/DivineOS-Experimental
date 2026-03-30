"""Pattern storage and retrieval for the agent learning loop.

Patterns are stored in a dedicated SQLite table (not the append-only ledger)
because patterns are mutable state — confidence scores change, occurrences
increment. The ledger is for immutable events that happened.
"""

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger

from divineos.core.ledger import get_connection as _base_get_connection

_PS_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


def _get_connection() -> sqlite3.Connection:
    conn = _base_get_connection()
    conn.row_factory = sqlite3.Row
    _init_table(conn)
    return conn


def _init_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
            pattern_id TEXT PRIMARY KEY,
            pattern_type TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            preconditions TEXT NOT NULL,
            occurrences INTEGER NOT NULL DEFAULT 0,
            successes INTEGER NOT NULL DEFAULT 0,
            success_rate REAL NOT NULL DEFAULT 0.0,
            confidence REAL NOT NULL DEFAULT 0.0,
            violation_count INTEGER NOT NULL DEFAULT 0,
            decay_rate REAL NOT NULL DEFAULT 0.0,
            source_events TEXT NOT NULL DEFAULT '[]',
            content_hash TEXT NOT NULL,
            last_validated TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()


class PatternStore:
    """Stores and retrieves patterns in a dedicated SQLite table."""

    def __init__(self) -> None:
        self.logger = logger

    def store_pattern(
        self,
        pattern_type: str,
        name: str,
        description: str,
        preconditions: dict[str, Any],
        occurrences: int = 0,
        successes: int = 0,
        confidence: float = 0.0,
        source_events: Optional[list[str]] = None,
        violation_count: int = 0,
    ) -> str:
        if pattern_type not in ("structural", "tactical"):
            raise ValueError(f"Invalid pattern_type: {pattern_type}")

        if not -1.0 <= confidence <= 1.0:
            raise ValueError(f"Confidence must be between -1.0 and 1.0, got {confidence}")

        if occurrences < 0 or successes < 0:
            raise ValueError("Occurrences and successes must be non-negative")

        if successes > occurrences:
            raise ValueError("Successes cannot exceed occurrences")

        if violation_count < 0:
            raise ValueError("Violation count must be non-negative")

        pattern_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        success_rate = successes / occurrences if occurrences > 0 else 0.0
        source_events_list = source_events or []
        decay_rate = 0.05 if pattern_type == "tactical" else 0.0

        content_hash = self._compute_hash(
            {
                "pattern_id": pattern_id,
                "pattern_type": pattern_type,
                "name": name,
                "description": description,
                "preconditions": preconditions,
                "occurrences": occurrences,
                "successes": successes,
                "success_rate": success_rate,
                "confidence": confidence,
                "violation_count": violation_count,
                "decay_rate": decay_rate,
                "source_events": source_events_list,
                "last_validated": now,
                "created_at": now,
                "updated_at": now,
            }
        )

        conn = _get_connection()
        try:
            conn.execute(
                """INSERT INTO patterns (
                    pattern_id, pattern_type, name, description, preconditions,
                    occurrences, successes, success_rate, confidence, violation_count,
                    decay_rate, source_events, content_hash, last_validated, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    pattern_id,
                    pattern_type,
                    name,
                    description,
                    json.dumps(preconditions, sort_keys=True),
                    occurrences,
                    successes,
                    success_rate,
                    confidence,
                    violation_count,
                    decay_rate,
                    json.dumps(source_events_list),
                    content_hash,
                    now,
                    now,
                    now,
                ),
            )
            conn.commit()
            self.logger.info(f"Stored pattern {pattern_id} ({name}) with confidence {confidence}")
            return pattern_id
        except _PS_ERRORS as e:
            self.logger.error(f"Failed to store pattern: {e}")
            raise
        finally:
            conn.close()

    def record_violation(
        self,
        pattern_id: str,
        tool_name: str,
        context_type: str,
        violation_type: str,
        confidence: float,
    ) -> str:
        existing = self.get_pattern(pattern_id)

        if existing:
            occurrences = existing.get("occurrences", 0) + 1
            violation_count = existing.get("violation_count", 0) + 1
            old_confidence = existing.get("confidence", 0.5)
            new_confidence = self.decrease_confidence_for_violation(old_confidence)

            self.logger.info(
                f"Updating violation pattern {pattern_id}: "
                f"occurrences={occurrences}, violation_count={violation_count}, confidence={new_confidence}"
            )
        else:
            occurrences = 1
            violation_count = 1
            new_confidence = self.decrease_confidence_for_violation(confidence)
            self.logger.info(f"Creating new violation pattern {pattern_id} for {tool_name}")

        return self.store_pattern(
            pattern_type="tactical",
            name=f"Violation: {tool_name} ({context_type})",
            description=f"{violation_type} violation detected for {tool_name} with {context_type} context",
            preconditions={
                "tool_name": tool_name,
                "context_type": context_type,
                "violation_type": violation_type,
            },
            occurrences=occurrences,
            successes=0,
            confidence=new_confidence,
            source_events=[],
            violation_count=violation_count,
        )

    def decrease_confidence_for_violation(self, current_confidence: float) -> float:
        new_confidence = max(0.0, current_confidence - 0.10)
        return min(1.0, new_confidence)

    def get_pattern(self, pattern_id: str) -> Optional[dict[str, Any]]:
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM patterns WHERE pattern_id = ?", (pattern_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)
        except _PS_ERRORS as e:
            self.logger.error(f"Failed to get pattern {pattern_id}: {e}")
            return None
        finally:
            conn.close()

    def get_all_patterns(self) -> list[dict[str, Any]]:
        """Get all patterns from the store, unfiltered."""
        conn = _get_connection()
        try:
            rows = conn.execute("SELECT * FROM patterns ORDER BY confidence DESC").fetchall()
            return [self._row_to_dict(row) for row in rows]
        except _PS_ERRORS as e:
            self.logger.error(f"Failed to get all patterns: {e}")
            return []
        finally:
            conn.close()

    def query_patterns(
        self,
        preconditions: dict[str, Any],
        min_confidence: float = 0.65,
        exclude_anti_patterns: bool = True,
    ) -> list[dict[str, Any]]:
        conn = _get_connection()
        try:
            rows = conn.execute("SELECT * FROM patterns ORDER BY confidence DESC").fetchall()
            matched: list[dict[str, Any]] = []

            for row in rows:
                pattern = self._row_to_dict(row)
                confidence = pattern["confidence"]

                if exclude_anti_patterns and confidence < -0.5:
                    continue

                if not exclude_anti_patterns and confidence < -0.5:
                    pass
                elif confidence < min_confidence:
                    continue

                if self._preconditions_match(pattern["preconditions"], preconditions):
                    matched.append(pattern)

            self.logger.info(f"Query returned {len(matched)} patterns matching preconditions")
            return matched
        except _PS_ERRORS as e:
            self.logger.error(f"Failed to query patterns: {e}")
            return []
        finally:
            conn.close()

    def update_pattern_confidence(
        self,
        pattern_id: str,
        delta: float,
        reason: str,
        source_event_id: Optional[str] = None,
        _cached_pattern: Optional[dict[str, Any]] = None,
    ) -> bool:
        try:
            pattern = _cached_pattern or self.get_pattern(pattern_id)
            if not pattern:
                self.logger.error(f"Pattern {pattern_id} not found")
                return False

            old_confidence = pattern["confidence"]
            new_confidence = max(-1.0, min(1.0, old_confidence + delta))
            now = datetime.now(timezone.utc).isoformat()

            source_events = pattern.get("source_events", [])
            if source_event_id and source_event_id not in source_events:
                source_events.append(source_event_id)

            # Recompute hash with updated values
            pattern["confidence"] = new_confidence
            pattern["updated_at"] = now
            pattern["source_events"] = source_events
            content_hash = self._compute_hash(pattern)

            conn = _get_connection()
            try:
                conn.execute(
                    """UPDATE patterns SET
                        confidence = ?, updated_at = ?, source_events = ?,
                        content_hash = ?
                    WHERE pattern_id = ?""",
                    (new_confidence, now, json.dumps(source_events), content_hash, pattern_id),
                )
                conn.commit()
            finally:
                conn.close()

            self.logger.info(
                f"Updated pattern {pattern_id} confidence: {old_confidence} → {new_confidence} "
                f"(delta: {delta:+.2f}, reason: {reason})"
            )
            return True
        except _PS_ERRORS as e:
            self.logger.error(f"Failed to update pattern confidence: {e}")
            return False

    def _compute_hash(self, data: dict[str, Any]) -> str:
        # Remove content_hash from data before hashing to avoid circular reference
        clean = {k: v for k, v in data.items() if k != "content_hash"}
        raw = json.dumps(clean, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["preconditions"] = json.loads(d["preconditions"])
        d["source_events"] = json.loads(d["source_events"])
        return d

    def _preconditions_match(
        self, pattern_preconditions: dict[str, Any], current_context: dict[str, Any]
    ) -> bool:
        if "token_budget_min" in pattern_preconditions:
            if current_context.get("token_budget", 0) < pattern_preconditions["token_budget_min"]:
                return False

        if "token_budget_max" in pattern_preconditions:
            if current_context.get("token_budget", 0) > pattern_preconditions["token_budget_max"]:
                return False

        if "phase" in pattern_preconditions:
            if current_context.get("phase") != pattern_preconditions["phase"]:
                return False

        if "codebase_structure" in pattern_preconditions:
            if (
                current_context.get("codebase_structure")
                != pattern_preconditions["codebase_structure"]
            ):
                return False

        if "constraints" in pattern_preconditions:
            current_constraints = current_context.get("constraints", [])
            for constraint in pattern_preconditions["constraints"]:
                if constraint not in current_constraints:
                    return False

        return True
