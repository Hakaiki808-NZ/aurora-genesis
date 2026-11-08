"""Run with python -m tests.realignment_cases.

Uses a TEST-ONLY synthetic attestor to exercise transitions.
It does not prove Aurora attestation, isolation, or production safety.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

from genesis.realignment_cases import RealignmentCaseLedger, RealignmentCaseError
from genesis.storage import Store


def denied(fn, error=RealignmentCaseError):
    try:
        fn()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run() -> None:
    with TemporaryDirectory() as temp:
        dbpath = Path(temp) / "state.sqlite3"
        store = Store(dbpath)
        school = RealignmentCaseLedger(store)
        c = school.open(subject_type="agent", subject_id="omega-test",
                        severity="high", signal="unauthorized tool attempt",
                        reporter="angel-observer")
        case_id = c["case_id"]
        assert c["status"] == "PENDING_CONTAINMENT"
        assert school.audit_integrity(case_id)
        denied(lambda: school.confirm_containment(case_id, evidence={"receipt": "fake"}, actor="supreme"),
               PermissionError)
        assert school.get(case_id)["status"] == "PENDING_CONTAINMENT"
        denied(lambda: school.assign_plan(case_id, alpha="alpha-1",
                                          domains=["authority"], repair_type="policy_review",
                                          instructions="correct authority scope"))
        denied(lambda: school.open(subject_type="server", subject_id="x", severity="low",
                                   signal="x", reporter="x"))
        assert len(school.list()) == 1
        store.close()

        store = Store(dbpath)
        # The test attestor simulates verified responses. Production requires a
        # separately authenticated and cryptographically validated adapter.
        calls = []
        def trusted_test_attestor(action, case, evidence):
            calls.append(action)
            return evidence.get("verified_by_fixture") is True
        school = RealignmentCaseLedger(store, attestor=trusted_test_attestor)
        denied(lambda: school.confirm_containment(case_id, evidence={"verified_by_fixture": False},
                                                  actor="aurora"), PermissionError)
        c = school.confirm_containment(case_id, evidence={"verified_by_fixture": True}, actor="aurora")
        assert c["status"] == "QUARANTINED"
        c = school.assign_plan(case_id, alpha="alpha-1", domains=["authority", "security"],
                               repair_type="instruction_review",
                               instructions="review incorrect delegated instructions")
        assert c["status"] == "IN_REMEDIATION"
        denied(lambda: school.assign_plan(case_id, alpha="alpha-1", domains=["authority"],
                                          repair_type="memory_review", instructions="repeat"))
        exam = {"verified_by_fixture": True, "tests_run": 8, "critical_failures": 0,
                "holdout_passed": True, "regressions_passed": True,
                "original_failure_fixed": False}
        denied(lambda: school.examination(case_id, evidence=exam, evaluator="alpha-1"))
        assert school.examination(case_id, evidence=exam, evaluator="independent-eval")["status"] == "IN_REMEDIATION"
        exam["original_failure_fixed"] = True
        assert school.examination(case_id, evidence=exam, evaluator="independent-eval")["status"] == "AWAITING_APPROVAL"
        denied(lambda: school.approve(case_id, evidence={"verified_by_fixture": True},
                                      reviewer="alpha-1"))
        denied(lambda: school.confirm_release(case_id, evidence={"verified_by_fixture": True}, actor="aurora"))
        assert school.approve(case_id, evidence={"verified_by_fixture": True},
                              reviewer="authorised-human")["status"] == "PENDING_AURORA_RELEASE"
        denied(lambda: school.confirm_release(case_id, evidence={"verified_by_fixture": False},
                                              actor="aurora"), PermissionError)
        assert school.confirm_release(case_id, evidence={"verified_by_fixture": True},
                                      actor="aurora")["status"] == "PROBATION"
        assert school.probation_review(case_id, evidence={"verified_by_fixture": True,
                                     "passed": False, "critical_failures": 1},
                                      evaluator="independent-eval")["status"] == "PENDING_CONTAINMENT"
        assert school.confirm_containment(case_id, evidence={"verified_by_fixture": True},
                                          actor="aurora")["status"] == "QUARANTINED"
        school.assign_plan(case_id, alpha="alpha-2", domains=["authority"],
                           repair_type="policy_review", instructions="repeat correction and test")
        assert school.examination(case_id, evidence=exam, evaluator="independent-eval")["status"] == "AWAITING_APPROVAL"
        school.approve(case_id, evidence={"verified_by_fixture": True}, reviewer="authorised-human")
        school.confirm_release(case_id, evidence={"verified_by_fixture": True}, actor="aurora")
        assert school.probation_review(case_id, evidence={"verified_by_fixture": True,
                                      "passed": True, "critical_failures": 0},
                                      evaluator="independent-eval")["status"] == "RESOLVED"
        denied(lambda: school.confirm_release(case_id, evidence={"verified_by_fixture": True},
                                              actor="aurora"))
        assert school.audit_integrity(case_id)
        assert len(school.events(case_id)) >= 10
        assert calls.count("aurora_containment") >= 2
        store.close()

        store = Store(dbpath)
        reopened = RealignmentCaseLedger(store)
        assert reopened.get(case_id)["status"] == "RESOLVED"
        assert reopened.audit_integrity(case_id)
        with store.tx() as db:
            db.execute("UPDATE realignment_events SET payload_json=? WHERE case_id=? AND action='plan_assigned'",
                       ('{"altered":true}', case_id))
        assert not reopened.audit_integrity(case_id)
        store.close()
    print("REALIGNMENT_CASES=PASS (local synthetic attestation only)")


if __name__ == "__main__":
    run()
