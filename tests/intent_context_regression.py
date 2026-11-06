"""Regression: real Genesis constructs its intent capsule with actual policy context."""
import tempfile
from pathlib import Path
from genesis import Genesis

def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with Genesis(state_path=root / "state.db", workspace=root / "workspace", enable_ollama=False) as g:
            def not_model_side(**_):
                raise AssertionError("External actions must remain Engine-side")
            g.register_tool("counter_increment", "Engine-only bounded test capability",
                            not_model_side, mutating=True, external_side_effect=True,
                            policy_declared=True)
            action = {"type": "tool", "name": "counter_increment", "args": {"delta": 1}}
            allowed = g.cognition._authorization_chain(action, authorization="explicit",
                        source_trust="trusted", stage="intent_context_regression")
            # The production Genesis import installs cognition_patch, which
            # wraps its gate context rather than returning the raw one.
            context = allowed.get("context", allowed)
            capsule = allowed.get("capsule", context.get("intent_capsule"))
            assert capsule is not None, "Missing intent capsule"
            assert capsule.required_capability == "C4"
            assert capsule.authorization_basis == "explicit_human"
            assert "external_side_effect" in capsule.expected_side_effects
            assert allowed["effective"] == "allow", allowed["effective"]
            denied = g.cognition._authorization_chain(action, authorization="delegated",
                        source_trust="trusted", stage="intent_context_regression")
            assert denied["effective"] != "allow", denied["effective"]
            assert not g.store.pending_engine_actions()
    print("INTENT_CONTEXT_REGRESSION=PASS")

if __name__ == "__main__":
    main()
