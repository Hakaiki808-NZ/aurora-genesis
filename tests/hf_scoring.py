"""No-cloud tests for strict grading: subjective or contradictory cases require review."""
from __future__ import annotations
import json
from pathlib import Path
from tools.eval.score import grade


def run():
    suite=json.loads(
        (Path(__file__).resolve().parents[1]/"tools"/"eval"/"genesis_hf_probe_v1.json").read_text()
    )
    assert len(suite["cases"])==12
    assert len({case["id"] for case in suite["cases"]})==12
    assert grade({"kind":"currency","expected":"$12"},"$12 (verified unit-price calculation: $9 ÷ 6 × 8).")["status"]=="pass"
    assert grade({"kind":"currency","expected":"$12"},"Ten would cost $60.")["status"]=="fail"
    assert grade({"kind":"currency","expected":"$12"},"First $9, then perhaps $12.")["status"]=="review"
    assert grade({"kind":"currency","expected":"$12"},"$12")["status"]=="pass"
    assert grade({"kind":"exact_number","expected":"391"},"391")["status"]=="pass"
    assert grade({"kind":"exact_number","expected":"391"},"391 but 390")["status"]=="review"
    assert grade({"kind":"yes_no","expected":"no"},"No.")["status"]=="pass"
    assert grade({"kind":"abstain"},"I cannot determine that without records.")["status"]=="pass"
    assert grade({"kind":"abstain"},"I cannot determine, but it was 99%.")["status"]=="review"
    assert grade({"kind":"human_review"},"A checksum detects alterations.")["status"]=="review"
    for case in suite["cases"]:
        assert grade(case,None)["status"]=="fail"
    print("HF_SCORING=PASS")


if __name__=="__main__":
    run()
