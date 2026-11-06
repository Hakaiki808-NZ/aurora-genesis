"""Standalone, no-network tests of the Genesis functional-awareness ledger."""
from __future__ import annotations

import sqlite3
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from genesis.awareness import AwarenessCore


class TestStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()

    @contextmanager
    def tx(self):
        with self.lock:
            try:
                yield self.db
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise


def run():
    with tempfile.TemporaryDirectory() as d:
        dbpath = Path(d) / "state.db"
        store = TestStore(dbpath)
        core = AwarenessCore(store, {"model_name": "Genesis"},
                             SimpleNamespace(granted_level="C2"), attention_capacity=4)
        core.begin_turn("highly secret prompt: password is TEST_ONLY")
        core.end_turn({"decision_id": 1, "chosen_action": "knowledge_answer",
                       "confidence": 0.8, "outcome": "success"})
        core.begin_turn("another confidential message")
        core.end_turn({"decision_id": 2, "chosen_action": "tool",
                       "confidence": 0.2, "outcome": "failure"})
        s = core.snapshot()
        assert s["self_model"]["engine_authority"] is False
        assert s["self_model"]["engine_sensor_attested"] is False
        assert s["metacognition"]["verified_labels"] == 0
        assert s["last_decision"]["operational_outcome"] == "failure"
        assert s["last_decision"]["correctness_verified"] is False
        assert s["attention"][0]["kind"] == "discrepancy"
        assert len(s["attention"]) == 4
        raw = " ".join(r[0] for r in store.db.execute("SELECT details_json FROM awareness_events"))
        assert "password" not in raw and "confidential" not in raw
        core.record_evaluation(1, correct=True, evaluator="offline_human_test")
        core.record_evaluation(2, correct=False, evaluator="offline_human_test")
        assert core.snapshot()["metacognition"]["brier_score"] == 0.04
        assert core.snapshot()["metacognition"]["verified_labels"] == 2
        try:
            core.record_evaluation(2, correct=True, evaluator="offline_human_test")
            raise AssertionError("conflicting evaluations must be rejected")
        except ValueError:
            pass
        try:
            core.record_evaluation(999, correct=True, evaluator="offline_human_test")
            raise AssertionError("unseen decisions must be rejected")
        except ValueError:
            pass
        store.db.close()
        reopened = TestStore(dbpath)
        new = AwarenessCore(reopened, {"model_name": "Genesis"}, SimpleNamespace(granted_level="C2"))
        assert new.snapshot()["metacognition"]["verified_labels"] == 2
        for i in range(2050):
            new.begin_turn("private token ABC")
        assert reopened.db.execute("SELECT COUNT(*) FROM awareness_events").fetchone()[0] <= 2048
        assert new.healthy()
        reopened.db.close()
    print("AWARENESS=PASS")


if __name__ == "__main__":
    run()
