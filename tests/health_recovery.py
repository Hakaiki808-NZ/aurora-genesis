"""Always-on reliability contract: probes and restart-persistent state."""
from __future__ import annotations

import tempfile
from pathlib import Path

from genesis import Genesis
from genesis.reliability import readiness_status


def run():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state_path = root / "persistent" / "genesis.sqlite3"
        workspace = root / "workspace"
        first = Genesis(state_path=state_path, workspace=workspace, enable_ollama=False)

        assert readiness_status(first) == {"component": "genesis", "status": "ready"}
        first.respond("Learn that continuity marker is ORBIT.")
        assert state_path.exists()
        episode_count = first.store.stats()["episodes"]
        assert episode_count >= 2
        first.close()

        # The process is no longer ready, but the file remains intact.
        assert readiness_status(first)["status"] == "unavailable"

        # A new worker can rehydrate memory without repeating the user turn.
        second = Genesis(state_path=state_path, workspace=workspace, enable_ollama=False)
        assert readiness_status(second)["status"] == "ready"
        assert second.store.stats()["episodes"] == episode_count
        assert "ORBIT" in second.respond("What is continuity marker?")
        second.close()

    print("HEALTH_RECOVERY=PASS")


if __name__ == "__main__":
    run()
