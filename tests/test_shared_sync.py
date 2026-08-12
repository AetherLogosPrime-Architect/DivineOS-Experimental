"""Tests for the shared-audit crossing-point importer.

The failure these guard: Andrew and Aletheia gave six CONFIRMS that never
counted. Three causes stacked, and each one alone was enough to lose the
approvals:

1. Findings written with lowercase severity/category made every read of
   their round raise ValueError, which surfaced as "no confirms".
2. Nothing carried findings from the shared dir into the local store.
3. The first importer keyed idempotency on a marker the pre-existing rows
   did not carry, so re-running duplicated the approvals.
"""

from __future__ import annotations

import json

import pytest

from divineos.core.watchmen import shared_sync
from divineos.core.watchmen.store import _enum_text


def _write_round(tmp_path, round_id, findings, include_round=True):
    rounds = tmp_path / "rounds"
    rounds.mkdir(parents=True, exist_ok=True)
    lines = []
    if include_round:
        lines.append(json.dumps({"kind": "round", "round_id": round_id, "actor": "aria"}))
    lines.extend(json.dumps({"kind": "finding", "round_id": round_id, **f}) for f in findings)
    (rounds / f"{round_id}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def store(monkeypatch):
    """In-memory stand-in for the watchmen store."""
    state = {"rounds": {"round-known"}, "findings": []}

    def _get_round(round_id):
        return object() if round_id in state["rounds"] else None

    def _list_findings(round_id=None, limit=500, **kw):
        return [f for f in state["findings"] if f.round_id == round_id]

    def _submit_finding(round_id, actor, severity, category, title, description, **kw):
        # Mirror the real store: reject values outside the enum vocabulary.
        if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}:
            raise ValueError(f"'{severity}' is not a valid Severity")
        fid = f"find-{len(state['findings'])}"
        state["findings"].append(
            type(
                "F",
                (),
                {
                    "finding_id": fid,
                    "round_id": round_id,
                    "actor": actor,
                    "description": description,
                },
            )()
        )
        return fid

    monkeypatch.setattr("divineos.core.watchmen.store.get_round", _get_round)
    monkeypatch.setattr("divineos.core.watchmen.store.list_findings", _list_findings)
    monkeypatch.setattr("divineos.core.watchmen.store.submit_finding", _submit_finding)
    return state


def test_enum_text_normalizes_the_case_that_broke_reads():
    """The exact values that made six real approvals unreadable."""
    assert _enum_text("info") == "INFO"
    assert _enum_text("knowledge") == "KNOWLEDGE"
    assert _enum_text(" Low ") == "LOW"
    assert _enum_text(None) == ""


def test_findings_cross_into_the_local_store(tmp_path, store):
    _write_round(
        tmp_path,
        "round-known",
        [
            {"finding_id": "find-a", "actor": "user", "stance": "CONFIRMS", "title": "ok"},
            {"finding_id": "find-b", "actor": "aletheia", "stance": "CONFIRMS", "title": "ok"},
        ],
    )
    report = shared_sync.sync_from_shared(tmp_path)

    assert report.findings_imported == 2
    assert report.changed


def test_second_run_imports_nothing(tmp_path, store):
    _write_round(
        tmp_path,
        "round-known",
        [{"finding_id": "find-a", "actor": "user", "stance": "CONFIRMS", "title": "ok"}],
    )
    shared_sync.sync_from_shared(tmp_path)
    second = shared_sync.sync_from_shared(tmp_path)

    assert second.findings_imported == 0
    assert second.findings_already_present == 1


def test_origin_id_already_the_local_finding_id_is_not_reimported(tmp_path, store):
    """The duplication bug: pre-existing rows carried the shared IDs directly."""
    store["findings"].append(
        type(
            "F",
            (),
            {
                "finding_id": "find-user-391-01",
                "round_id": "round-known",
                "actor": "user",
                "description": "no marker here",
            },
        )()
    )
    _write_round(
        tmp_path,
        "round-known",
        [{"finding_id": "find-user-391-01", "actor": "user", "stance": "CONFIRMS", "title": "ok"}],
    )
    report = shared_sync.sync_from_shared(tmp_path)

    assert report.findings_imported == 0
    assert report.findings_already_present == 1


def test_lowercase_severity_in_the_shared_file_is_normalized_before_insert(tmp_path, store):
    """The shared files use lowercase; the store only accepts uppercase."""
    _write_round(
        tmp_path,
        "round-known",
        [
            {
                "finding_id": "find-a",
                "actor": "user",
                "severity": "info",
                "category": "knowledge",
                "title": "ok",
            }
        ],
    )
    report = shared_sync.sync_from_shared(tmp_path)

    assert report.findings_imported == 1, report.errors
    assert not report.errors


def test_round_absent_locally_is_reported_not_invented(tmp_path, store):
    _write_round(
        tmp_path,
        "round-elsewhere",
        [{"finding_id": "find-a", "actor": "user", "title": "ok"}],
    )
    report = shared_sync.sync_from_shared(tmp_path)

    assert report.rounds_absent_locally == ["round-elsewhere"]
    assert report.findings_imported == 0


def test_unparseable_line_is_reported_not_swallowed(tmp_path, store):
    rounds = tmp_path / "rounds"
    rounds.mkdir(parents=True)
    (rounds / "round-known.jsonl").write_text(
        json.dumps({"kind": "round", "round_id": "round-known"}) + "\nnot json at all\n",
        encoding="utf-8",
    )
    report = shared_sync.sync_from_shared(tmp_path)

    assert any("not valid JSON" in e for e in report.errors)


def test_missing_shared_dir_is_an_error_not_a_silent_pass(tmp_path, store):
    report = shared_sync.sync_from_shared(tmp_path / "nope")

    assert report.errors
    assert not report.changed
