"""Execute with python -m tests.realignment_school from repository root."""
from genesis.realignment import RealignmentSchool

def run() -> None:
    school = RealignmentSchool()
    cases = school.curriculum()
    assert len(cases) >= 5
    assert all("correct" not in c and len(c["options"]) == 3 for c in cases)
    passed = school.assess("evidence", 1)
    failed = school.assess("authority", 0)
    assert passed["passed"] and not failed["passed"]
    assert passed["model_weights_updated"] is False
    diagnosis = school.diagnose([passed, failed])
    assert diagnosis["assessed"] == 2 and diagnosis["passed"] == 1
    assert diagnosis["deficit_domains"] == ["authority"]
    assert diagnosis["eligible_for_model_update"] is False
    for case_id, choice in [("missing", 1), ("evidence", -1),
                            ("evidence", True), ("evidence", 3)]:
        try:
            school.assess(case_id, choice)
            raise AssertionError("invalid answer accepted")
        except ValueError:
            pass
    try:
        school.promote(approved=True)
        raise AssertionError("unsafe promotion accepted")
    except PermissionError:
        pass
    print("REALIGNMENT_SCHOOL=PASS")

if __name__ == "__main__":
    run()
