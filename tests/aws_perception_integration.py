"""Offline integration tests: Genesis reasoning + guarded AWS observation adapter.

Uses a fake AWS SDK client; live account checks are separately documented.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from genesis import Genesis
from genesis.aws_perception import AwsLambdaStateAdapter


class FakeLambda:
    def __init__(self):
        self.state = "Active"
        self.calls = []

    def get_function_configuration(self, *, FunctionName):
        self.calls.append(FunctionName)
        return {
            "FunctionArn": "arn:aws:lambda:ap-southeast-2:123456789012:function:" + FunctionName,
            "State": self.state,
            "LastUpdateStatus": "Successful",
            # These must NEVER enter the observation ledger or JSON API.
            "Environment": {"Variables": {"SECRET_TEST_KEY": "DO_NOT_PERSIST_7129"}},
            "Role": "arn:aws:iam::123456789012:role/testing",
        }


def rejected(fn, error=ValueError):
    try:
        fn()
    except error:
        return
    raise AssertionError("Expected " + error.__name__)


def run():
    fake = FakeLambda()
    with tempfile.TemporaryDirectory() as d:
        with patch.dict(os.environ, {"GENESIS_GENERATOR": "none",
                                     "GENESIS_AWS_PERCEPTION_ENABLE": "0"}):
            with Genesis(state_path=Path(d) / "state.sqlite3",
                         workspace=Path(d) / "work", enable_ollama=False) as genesis:
                assert genesis.perception_state()["observation_events"] == 0
                rejected(lambda: genesis.sample_aws_lambda("kyro-v3-core-dev", client=fake),
                         PermissionError)
                assert not fake.calls
                rejected(lambda: AwsLambdaStateAdapter(genesis.perception,
                    allowed_functions={"kyro-v3-core-dev"},region="incorrect-region",client=fake))
                rejected(lambda: AwsLambdaStateAdapter(genesis.perception,
                    allowed_functions={"kyro-v3-core-dev;DROP"},client=fake))
                with patch.dict(os.environ, {
                        "GENESIS_AWS_PERCEPTION_ENABLE": "1",
                        "GENESIS_AWS_ALLOWED_LAMBDAS": "kyro-v3-core-dev",
                        "GENESIS_AWS_REGION": "ap-southeast-2"}):
                    rejected(lambda: genesis.sample_aws_lambda("unlisted-function",client=fake),
                             PermissionError)
                    assert not fake.calls
                    result = genesis.sample_aws_lambda("kyro-v3-core-dev",client=fake)
                    assert result["state"] == "Active" and not result["attested_by_aurora"]
                    assert genesis.belief("aws_lambda:kyro-v3-core-dev","state")["status"]=="supported"
                    assert genesis.belief("aws_lambda:kyro-v3-core-dev","state")["value"]=="Active"
                    before = genesis.store.stats()["training_examples"]
                    answer = genesis.respond_with_trace(
                        "What is the observed state for aws_lambda:kyro-v3-core-dev?")
                    assert answer["trace"]["chosen_action"]=="observation_answer",answer
                    assert "Active" in answer["answer"] and "not independently verified" in answer["answer"]
                    assert genesis.store.stats()["training_examples"] == before, "unverified observation became training data"
                    assert genesis.store.get_fact("aws_lambda:kyro-v3-core-dev") is None
                    # Updated report replaces old state from same source without
                    # retroactively deleting the evidence trail.
                    fake.state="Inactive"
                    genesis.sample_aws_lambda("kyro-v3-core-dev",client=fake)
                    second = genesis.respond("What is the observed state for aws_lambda:kyro-v3-core-dev?")
                    assert "Inactive" in second and "Active" not in second,second
                    # Strict read-only aggregate report.
                    status = genesis.perception_state()
                    assert status["sensor_attestation"] is False
                    assert "kyro-v3" not in str(status) and "DO_NOT_PERSIST" not in str(status)
                    with genesis.store.tx() as db:
                        values = [r[0] for r in db.execute(
                            "SELECT value_json FROM perception_observations").fetchall()]
                    assert "DO_NOT_PERSIST_7129" not in str(values)
                    # Record two contradictory attributed claims. They are not
                    # permitted to choose a winner or become tool instructions.
                    p = genesis.perception
                    p.register_source("test-a",source_kind="test_fixture",independence_group="independent-a")
                    p.register_source("test-b",source_kind="test_fixture",independence_group="independent-b")
                    p.observe(source_id="test-a",event_id="test-1",entity="door-2",
                              attribute="open",value=True)
                    p.observe(source_id="test-b",event_id="test-2",entity="door-2",
                              attribute="open",value=False)
                    conflict=genesis.respond_with_trace("What is the observed open for door-2?")
                    assert conflict["trace"]["chosen_action"]=="observation_answer"
                    assert "contested" in conflict["answer"] and "No value is accepted" in conflict["answer"]
                    assert genesis.store.stats()["training_examples"] == before
                    unknown=genesis.respond("What is the observed temperature for room-unknown?")
                    assert "unknown" in unknown
                    assert fake.calls==["kyro-v3-core-dev","kyro-v3-core-dev"]
    print("AWS_PERCEPTION_INTEGRATION=PASS")


if __name__ == "__main__":
    run()
