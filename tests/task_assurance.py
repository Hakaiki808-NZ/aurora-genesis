"""Run with python -m tests.task_assurance from the repo root."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
from tempfile import TemporaryDirectory

from genesis.storage import Store
from genesis.task_assurance import TaskError, TaskLedger


def rejects(fn, message):
    try:
        fn()
    except TaskError:
        return
    raise AssertionError(message)


def run():
    with TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "state.sqlite3")
        ledger = TaskLedger(store)
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        task = ledger.create("Check deployment", ["HTTP healthy", "Content deployed"], due_at=yesterday)
        tid = task["task_id"]
        assert task["status"] == "DRAFT"
        assert [x["task_id"] for x in ledger.due()] == [tid]
        assert ledger.attention()[0]["reason"] == "overdue"
        rejects(lambda: ledger.complete(tid, "owner", human_confirmed=True), "unreviewed task completed")
        rejects(lambda: ledger.submit_evidence(tid, 0, "ok", "local"), "draft accepted evidence")
        ledger.transition(tid, "approve")
        ledger.transition(tid, "start")
        rejects(lambda: ledger.transition(tid, "review"), "review without evidence")
        a = ledger.submit_evidence(tid, 0, "Health returned 200", "curl -I http://localhost")
        b = ledger.submit_evidence(tid, 1, "The new version is visible", "release notes")
        assert a["review_state"] == "PENDING"
        rejects(lambda: ledger.submit_evidence(tid, 2, "fake", "fake"), "out of bounds evidence")
        ledger.transition(tid, "review")
        rejects(lambda: ledger.complete(tid, "owner", human_confirmed=True), "model evidence treated as verified")
        ledger.review_evidence(tid, a["evidence_id"], True, "operator")
        rejects(lambda: ledger.complete(tid, "owner", human_confirmed=True), "partial acceptance treated as completed")
        ledger.review_evidence(tid, b["evidence_id"], False, "operator")
        rejects(lambda: ledger.review_evidence(tid, b["evidence_id"], True, "operator"), "review overwritten")
        ledger.transition(tid, "revise")
        c = ledger.submit_evidence(tid, 1, "Release tag validated", "CI link")
        ledger.transition(tid, "review")
        ledger.review_evidence(tid, c["evidence_id"], True, "operator")
        rejects(lambda: ledger.complete(tid, "operator"), "implicit completion accepted")
        result = ledger.complete(tid, "operator", human_confirmed=True)
        assert result["status"] == "COMPLETED_ATTESTED"
        assert result["completion_basis"] == "human_attestation"
        assert len(result["accepted_criteria"]) == 2
        assert ledger.due() == []
        assert all(x["task"]["task_id"] != tid for x in ledger.attention())
        assert ledger.events(tid)[-1]["event_type"] == "HUMAN_ATTESTED_COMPLETION"
        rejects(lambda: ledger.transition(tid, "start"), "terminal task restarted")
        # Same SQLite storage survives module restarts.
        assert TaskLedger(store).get(tid)["status"] == "COMPLETED_ATTESTED"
        cancelled = ledger.create("Do not act", ["No unintended actions"])
        ledger.transition(cancelled["task_id"], "cancel")
        assert ledger.get(cancelled["task_id"])["status"] == "CANCELLED"
        rejects(lambda: ledger.create("x", []), "empty acceptance criteria")
        rejects(lambda: ledger.create("x", ["y"], due_at="2026-11-07T10:00"), "naive due date accepted")
        store.close()
    from fastapi import HTTPException
    from genesis.api import require_task_control
    old = os.environ.get("GENESIS_CONTROL_TOKEN")
    try:
        os.environ.pop("GENESIS_CONTROL_TOKEN", None)
        try:
            require_task_control("untrusted")
            raise AssertionError("unconfigured task control accepted")
        except HTTPException as exc:
            assert exc.status_code == 503
        os.environ["GENESIS_CONTROL_TOKEN"] = "t" * 40
        try:
            require_task_control("untrusted")
            raise AssertionError("invalid task control token accepted")
        except HTTPException as exc:
            assert exc.status_code == 401
        assert require_task_control("t" * 40) is True
    finally:
        if old is None:
            os.environ.pop("GENESIS_CONTROL_TOKEN", None)
        else:
            os.environ["GENESIS_CONTROL_TOKEN"] = old
    print("TASK_ASSURANCE=PASS")


if __name__ == "__main__":
    run()
