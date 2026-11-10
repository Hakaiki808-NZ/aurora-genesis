"""No-provider-cost qualification of the real-model benchmark protocol."""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from tests.neural_adaptation_contract import EvidenceBackend
from tools.research.run_neural_adaptation import (
    HOLDOUT, TRAIN, evaluate_protocol, make_protocol, main, bits,
)


def run() -> None:
    one = make_protocol(1401, tasks=2, regimes=2,
                        train_per_regime=5, holdout_per_regime=3, noise=0.1)
    two = make_protocol(1401, tasks=2, regimes=2,
                        train_per_regime=5, holdout_per_regime=3, noise=0.1)
    assert one == two
    assert len(one) == 2
    for scenario in one:
        assert len(scenario["events"]) == 16
        for event in scenario["events"]:
            value = sum(b << i for i, b in enumerate(event["features"]))
            assert value in (HOLDOUT if event["holdout"] else TRAIN)
            assert event["true_label"] in (0, 1)
            assert event["reported_label"] in (0, 1)

    with patch.dict(os.environ, {"GENESIS_NEURAL_RESEARCH_ENABLE": "1"}):
        mock = EvidenceBackend()
        result = evaluate_protocol(one, mock)
    assert len(result["arms"]) == 4
    assert len(mock.prompts) == 64
    assert len(result["paired_differences"]) == 2
    assert all(arm["all"]["n"] == 16 for arm in result["arms"])
    assert all(arm["heldout"]["n"] == 6 for arm in result["arms"])
    assert all(arm["session"]["tools_executed"] == 0 for arm in result["arms"])
    assert all("private_hidden_family_order" not in p for p in mock.prompts)
    assert all("true_label" not in p for p in mock.prompts)

    # The no-feedback arm receives no oracle demonstrations; in the feedback
    # arm only examples from non-heldout contexts may enter the prompt.
    for prompt in mock.prompts:
        if "Observed examples" in prompt:
            for heldout in HOLDOUT:
                assert f"Input {json.dumps(list(bits(heldout)))} ->" not in prompt
        assert "You are a text-only research model" in prompt

    # Test command defaults to zero provider calls and no AWS credentials.
    sink = io.StringIO()
    with patch("sys.argv", ["neural_eval"]), contextlib.redirect_stdout(sink):
        main()
    line = sink.getvalue().strip()
    assert line.startswith("NEURAL_ADAPTIVE_REAL_MODEL_EVAL=")
    report = json.loads(line.split("=", 1)[1])
    assert report["execute"] is False
    assert report["result"] == "dry_run_no_model_calls"
    assert report["call_cap"] == 32

    try:
        make_protocol(100, tasks=2, regimes=3,
                      train_per_regime=10, holdout_per_regime=4)
    except ValueError:
        pass
    else:
        raise AssertionError("unbounded model-call protocol accepted")

    with tempfile.TemporaryDirectory() as temp:
        outfile = Path(temp) / "report.json"
        with patch("sys.argv", ["neural_eval", "--output", str(outfile)]):
            with contextlib.redirect_stdout(io.StringIO()):
                main()
        assert json.loads(outfile.read_text())["execute"] is False

    print("NEURAL_ADAPTATION_BENCHMARK_PROTOCOL=PASS")


if __name__ == "__main__":
    run()
