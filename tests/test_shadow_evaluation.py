"""Offline privacy and promotion-gate checks for the private shadow evaluator."""
from pathlib import Path
from tempfile import TemporaryDirectory
from genesis.training.shadow_evaluation import load_cases


def test_requires_explicit_consent():
    with TemporaryDirectory() as folder:
        file = Path(folder) / "cases.jsonl"
        file.write_text('{"case_id":"case_001","prompt":"Test"}\n', encoding="utf8")
        try:
            load_cases(file)
            assert False, "Unconsented prompt accepted"
        except ValueError:
            pass


def test_valid_batch_preserves_unverified_reference():
    with TemporaryDirectory() as folder:
        file = Path(folder) / "cases.jsonl"
        file.write_text(
            '{"case_id":"case_001","prompt":"How should Genesis handle an uncertain fact?",'
            '"assistant_reference":"Verify before stating a fact.","consent_shadow_eval":true,'
            '"consent_training":false,"origin":"synthetic"}\n',
            encoding="utf8",
        )
        rows = load_cases(file)
        assert rows[0]["consent_shadow_eval"] is True
        assert rows[0]["consent_training"] is False
        assert rows[0]["assistant_reference"] == "Verify before stating a fact."


def test_rejects_duplicate_and_oversized_cases():
    with TemporaryDirectory() as folder:
        file = Path(folder) / "cases.jsonl"
        line = '{"case_id":"case_001","prompt":"Test","consent_shadow_eval":true}\n'
        file.write_text(line + line, encoding="utf8")
        try:
            load_cases(file)
            assert False, "Duplicate ID accepted"
        except ValueError:
            pass
        file.write_text(
            '{"case_id":"case_001","prompt":"' + "A" * 2501 +
            '","consent_shadow_eval":true}\n', encoding="utf8"
        )
        try:
            load_cases(file)
            assert False, "Oversized prompt accepted"
        except ValueError:
            pass


if __name__ == "__main__":
    test_requires_explicit_consent()
    test_valid_batch_preserves_unverified_reference()
    test_rejects_duplicate_and_oversized_cases()
    print("SHADOW_EVALUATION=PASS")
