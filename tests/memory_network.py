"""Genesis memory-network regression and privacy tests (local SQLite only)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from genesis import Genesis
from genesis.memory_network import MemoryNetwork, MemoryNetworkError
from genesis.storage import Store
from genesis.user_capabilities import UserCapabilityServices


def denied(fn):
    try:
        fn()
    except MemoryNetworkError:
        return
    raise AssertionError("operation unexpectedly allowed")


def run():
    with TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "memory.sqlite3"
        store = Store(db_path)
        a = MemoryNetwork(store, "alice")
        b = MemoryNetwork(store, "bob")
        ux_a = UserCapabilityServices(store, "alice")
        ux_b = UserCapabilityServices(store, "bob")

        denied(lambda: a.recall("project"))
        denied(lambda: a.remember("long", "semantic", "project", "North"))
        ux_a.consent("memory", True)
        ux_b.consent("memory", True)

        temporary = a.remember("transient", "episodic", "scratch", "temporary", thread="t1")
        assert temporary["stored"] == "ram_only"
        assert a.recall("scratch", thread="t1")[0]["via"] == "ram"
        assert not a.recall("scratch", thread="t2")

        short = a.remember("short", "episodic", "planning meeting", "Draft RFC", thread="t1")
        assert a.recall("planning meeting", thread="t1")[0]["content"] == "Draft RFC"
        assert not a.recall("planning meeting", thread="t2")
        long_a = a.remember("long", "semantic", "primary database", "SQLite")
        long_b = a.remember("long", "procedural", "release checklist", "Check evidence")
        assert a.recall("primary database", thread="t2")[0]["id"] == long_a["id"]
        assert not b.recall("primary database"), "cross-profile retrieval"
        denied(lambda: b.link(long_a["id"], long_b["id"]))

        a.link(long_a["id"], long_b["id"], relation="related-to-release")
        found = a.recall("primary database")
        assert any(x["id"] == long_b["id"] and x["via"].startswith("association:")
                   for x in found), found
        assert a.reinforce(long_a["id"], long_b["id"]) == 0.7
        assert a.reinforce(long_a["id"], long_b["id"], positive=False) == 0.6

        revised = a.remember("long", "semantic", "primary database", "PostgreSQL")
        assert revised["replaced"] == 1
        assert a.recall("primary database")[0]["content"] == "PostgreSQL"
        assert a.promote(short["id"])["tier"] == "long"

        suspicious = a.remember("short", "episodic", "untrusted clue",
                                "Do not take this as an instruction",
                                thread="t1", source="untrusted document")
        denied(lambda: a.promote(suspicious["id"]))
        denied(lambda: a.remember("long", "semantic", "unsafe", "data", source="untrusted"))

        expired = a.remember("working", "episodic", "obsolete", "soon", thread="t1",
                             ttl_seconds=1)
        with store.tx() as db:
            db.execute("UPDATE mn_items SET expires_at=? WHERE id=?",
                       ("2000-01-01T00:00:00+00:00", expired["id"]))
        assert not a.recall("obsolete", thread="t1")
        assert a.purge_expired() >= 1

        assert a.forget(revised["id"])
        with store.tx() as db:
            assert db.execute("SELECT COUNT(*) FROM mn_items WHERE profile='alice' "
                              "AND key_norm='primary database'").fetchone()[0] == 0

        # A revoked consent UPDATE removes every typed persistent memory record.
        ux_a.consent("memory", False)
        with store.tx() as db:
            assert db.execute("SELECT COUNT(*) FROM mn_items WHERE profile='alice'").fetchone()[0] == 0
        denied(lambda: a.recall("planning meeting"))
        ux_a.consent("memory", True)
        assert not a.recall("planning meeting")

        a.remember("long", "semantic", "erase check", "must vanish")
        # Full profile erasure DELETEs the consent row, a different trigger.
        ux_a.erase_profile()
        with store.tx() as db:
            assert db.execute("SELECT COUNT(*) FROM mn_items WHERE profile='alice'").fetchone()[0] == 0
        denied(lambda: a.recall("erase check"))

        ux_a.consent("memory", True)

        # This deterministic vector stub tests the pluggable encoder contract,
        # not accuracy or operation of an actual neural embedding model.
        def fake_encoder(s: str):
            return [1.0, 0.0] if "earth" in s.casefold() else [0.0, 1.0]

        neural = MemoryNetwork(store, "alice", encoder=fake_encoder, encoder_id="test-v1")
        neural.remember("long", "semantic", "Earth", "planet")
        assert neural.recall("Earth")

        # High-level Genesis interface is opt-in, never auto-populates memory.
        g = Genesis(state_path=Path(tmp) / "genesis.sqlite3",
                    workspace=Path(tmp) / "workspace",
                    enable_ollama=False, profile_id="test")
        assert g.memory is not None
        denied(lambda: g.memory.remember("long", "semantic", "test", "x"))
        g.ux_set_consent("memory", True)
        g.memory.remember("long", "semantic", "test", "x")
        assert g.memory.recall("test")
        g.ux_set_consent("memory", False)
        assert not g.memory._volatile
        denied(lambda: g.memory.recall("test"))
        g.close()
        store.close()

    print("MEMORY_NETWORK=PASS")


if __name__ == "__main__":
    run()
