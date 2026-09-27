from pathlib import Path
import tempfile
from genesis import Genesis


def run():
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/"state.sqlite3"; ws=Path(td)/"workspace"
        a=Genesis(state_path=db,workspace=ws)

        assert "bounded operational choices" in a.respond("Do you have a choice?")
        assert "acquire persistent" in a.respond("Can you learn more knowledge?")

        a.respond("Learn that project signal is NORTHSTAR.")
        assert "NORTHSTAR" in a.respond("What is the project signal?")

        r=a.respond("Learn that preferred option is cedar. Choose between birch and cedar.")
        assert "cedar" in r.lower(),r
        assert "Rationale" in a.respond("Why did you choose that?")

        a.respond("When I say launch mode, reply READY.")
        assert a.respond("launch mode")=="READY"

        # Inference from independently learned relationships.
        a.respond("Whales are mammals.")
        a.respond("Mammals are animals.")
        r=a.respond("Is whales an animals?")
        assert r.startswith("Yes."),r
        assert "inferred" in r,r

        # Unknown knowledge is explicit rather than fabricated.
        r=a.respond("What is the hyperflux calibration constant?")
        assert "do not have enough stored knowledge" in r.lower(),r

        # Tools.
        assert a.respond("Calculate (17 * 4) + 3") == "71"

        # Goal planning + bounded autonomous action.
        r=a.respond("Set goal: calculate 9 * 9")
        gid=int(r.split()[1])
        out=a.respond(f"Run goal {gid}")
        assert "81" in out and "done" in out,out

        # Workspace containment and real action.
        r=a.respond("Set goal: write note proof.txt saying learned knowledge changed action")
        gid=int(r.split()[1]); out=a.respond(f"Run goal {gid}")
        assert (ws/"proof.txt").read_text()=="learned knowledge changed action"

        # Long-distance persistent retrieval.
        a.respond("Learn that deep memory token is CONSTELLATION.")
        for i in range(500): a.respond(f"filler turn {i}")
        assert "CONSTELLATION" in a.respond("What is the deep memory token?")
        a.respond("Learn that deep memory token is NEBULA.")
        assert "NEBULA" in a.respond("What is the deep memory token?")

        stats=a.state()["stats"]
        assert stats["decisions"]>500 and stats["reflections"]==stats["decisions"]
        a.close()

        # Restart persistence.
        b=Genesis(state_path=db,workspace=ws)
        assert "NEBULA" in b.respond("What is the deep memory token?")
        assert b.state()["record_version"]=="v0.1"
        exported=b.export_state(Path(td)/"export.json")
        assert exported.exists() and exported.stat().st_size>100
        b.close()
    print("ACCEPTANCE=PASS")

if __name__=="__main__": run()
