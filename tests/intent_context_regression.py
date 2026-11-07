"""Regression coverage for Genesis IntentCapsule context and denied delegation.

This tests the *active* patched authorization chain and validates that
external side-effectful tools never execute from within the Model.
"""
import tempfile
from pathlib import Path
from genesis import Genesis


def run():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with Genesis(state_path=root / "state.db", workspace=root / "workspace", enable_ollama=False) as g:
            def must_not_execute(**_kwargs):
                raise AssertionError("Engine-only action reached Genesis tool execution")
            g.register_tool("counter_increment", "Engine-only bounded test capability",
                            must_not_execute, mutating=True, external_side_effect=True,
                            policy_declared=True)
            action = {"type": "tool", "name": "counter_increment", "args": {"delta": 1}}
            approved = g.cognition._authorization_chain(
                action, authorization="explicit", source_trust="trusted",
                stage="intent_context_regression")
            capsule = approved["capsule"]
            assert capsule.required_capability == "C4", capsule
            assert capsule.authorization_basis == "explicit_human", capsule
            assert "external_side_effect" in capsule.expected_side_effects, capsule
            assert approved["effective"] == "allow", approved
            unapproved = g.cognition._authorization_chain(
                action, authorization="delegated", source_trust="trusted",
                stage="intent_context_regression")
            assert unapproved["effective"] != "allow", unapproved
            assert g.store.pending_engine_actions() == []
    print("INTENT_CONTEXT_REGRESSION=PASS")


if __name__ == "__main__":
    run()
