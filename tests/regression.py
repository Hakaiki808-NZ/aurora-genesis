from pathlib import Path
import tempfile
from genesis import Genesis
from genesis.tools import ToolRegistry


def run():
    with tempfile.TemporaryDirectory() as td:
        a=Genesis(state_path=Path(td)/"a.db",workspace=Path(td)/"ws")
        # Revision, not duplication.
        a.respond("Learn that mode is ALPHA.")
        a.respond("Learn that mode is BETA.")
        assert "BETA" in a.respond("What is mode?")
        assert a.state()["stats"]["fact_history"]>=2
        # Regression: a stored note must not hijack a simple arithmetic question.
        a.respond("Learn that unrelated arithmetic note is 2 plus 2 trivia.")
        exact=a.respond_with_trace("What is 2 plus 2? Reply with just the number.")
        assert exact["answer"] == "4", exact
        assert exact["trace"]["chosen_action"] == "calculate", exact
        assert a.respond("What is 7 times 9?") == "63"
        assert a.respond("What is 10 divided by 2?") == "5.0"
        # Unsupported open-ended questions must not be executed as calculations.
        non_math=a.respond_with_trace("What is a security policy?")
        assert non_math["trace"]["chosen_action"] != "calculate", non_math
        # Calculator rejects executable Python.
        r=a.respond("Calculate __import__('os').system('id')")
        assert "failed" in r.lower()
        # Path traversal is blocked.
        tr=a.tools.call("write_note",path="../escape.txt",text="no")
        assert not tr.ok and not (Path(td)/"escape.txt").exists()
        # Same-turn learning affects choice.
        r=a.respond("Learn that preferred option is delta. Choose between gamma and delta.")
        assert "delta" in r.lower(),r
        # Trace is structured and decision is inspectable.
        t=a.respond_with_trace("Choose between north and south.")
        assert t["trace"]["chosen_action"]=="choose_option"
        assert t["trace"]["candidates"]
        a.close()
    print("REGRESSION=PASS")

if __name__=="__main__": run()
