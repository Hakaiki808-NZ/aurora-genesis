"""Seven capability UX foundation regression suite.

The source/provenance review states here are *human attestations*, not checks
of external URLs or claims. No background processes or AWS services are used.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from genesis.storage import Store
from genesis.user_capabilities import UserCapabilityServices, UserCapabilityError
from genesis import Genesis


def denied(fn):
    try:
        fn()
    except UserCapabilityError:
        return
    raise AssertionError("a denied operation was allowed")


def run():
    with TemporaryDirectory() as tmp:
        state=Path(tmp)/"state.db"
        store=Store(state)
        a=UserCapabilityServices(store, "alice")
        b=UserCapabilityServices(store, "bob")
        assert not any(a.consents().values())
        denied(lambda: a.remember("memory","project","NORTH"))
        denied(lambda: a.remember("preference","theme","light"))
        denied(lambda: a.add_claim("Example"))
        denied(lambda: a.propose_nudge("Check status","2026-11-07T09:00:00Z"))
        a.consent("memory",True)
        a.consent("personalization",True)
        a.consent("provenance",True)
        a.consent("proactive",True)
        assert all(a.consents().values())
        assert not any(b.consents().values())
        soon=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        a.remember("memory","project","NORTH",expires_at=soon)
        a.remember("preference","theme","light")
        assert a.recall("memory","project")[0]["value"]=="NORTH"
        assert a.recall("preference","theme")[0]["value"]=="light"
        denied(lambda: b.recall("memory"))
        b.consent("memory",True)
        assert b.recall("memory")==[], "cross-profile leak"
        b.remember("memory","project","SOUTH")
        assert b.recall("memory")[0]["value"]=="SOUTH"
        assert a.recall("memory")[0]["value"]=="NORTH"
        denied(lambda: a.remember("memory","stale","x",expires_at="2020-01-01T00:00:00Z"))
        denied(lambda: a.remember("memory","naive","x",expires_at="2035-01-01T00:00:00"))
        a.remember("memory","project","NORTH-V2")
        assert a.recall("memory")[0]["value"]=="NORTH-V2"
        a.remember("memory","escape'; DELETE FROM ux_records;--","literal")
        assert len(a.recall("memory"))==2
        assert a.forget("memory","escape'; DELETE FROM ux_records;--")
        assert not a.forget("memory","escape'; DELETE FROM ux_records;--")

        claim=a.add_claim("Water is wet", [{"reference":"https://example.org/ref","label":"Example reference"}])
        assert claim["review_state"]=="SOURCES_LISTED_UNCHECKED"
        assert claim["independently_verified"] is False
        verified=a.review_claim(claim["claim_id"],True,"operator")
        assert verified["review_state"]=="HUMAN_ATTESTED_SUPPORT"
        assert verified["independently_verified"] is False
        denied(lambda: a.review_claim(claim["claim_id"],False,"operator"))
        denied(lambda: b.claim(claim["claim_id"]))
        denied(lambda: a.add_claim("bad",[{"reference":"x","unexpected":"y"}]))

        yesterday=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
        pending=a.propose_nudge("Inspect deploy",yesterday)
        assert a.attention()[0]["nudge_id"]==pending["nudge_id"]
        assert a.attention()[0]["title"]=="Inspect deploy"
        assert a.dismiss_nudge(pending["nudge_id"]) is True
        assert a.dismiss_nudge(pending["nudge_id"]) is False
        assert a.attention()==[]
        future=a.propose_nudge("Tomorrow",soon)
        assert a.attention()==[]
        assert a.attention(now=soon)[0]["nudge_id"]==future["nudge_id"]

        comparison=a.compare_options(
            [{"name":"cost","weight":3},{"name":"speed","weight":1}],
            [{"name":"Option A","scores":{"cost":5,"speed":1}},
             {"name":"Option B","scores":{"cost":2,"speed":5}}])
        assert comparison["ranking"][0]["name"]=="Option A"
        assert comparison["auto_action"] is False
        denied(lambda: a.compare_options(
            [{"name":"cost","weight":1}],
            [{"name":"A","scores":{"cost":5}},{"name":"B","scores":{}}]))
        denied(lambda: a.compare_options(
            [{"name":"cost","weight":float("nan")}],
            [{"name":"A","scores":{"cost":5}},{"name":"B","scores":{"cost":2}}]))
        denied(lambda: a.compare_options(
            [{"name":"cost","weight":0}],
            [{"name":"A","scores":{"cost":5}},{"name":"B","scores":{"cost":2}}]))

        exported=a.export_profile()
        assert len(exported["records"])==2
        assert len(exported["claims"])==1
        assert "source" in exported["records"][0]
        assert exported["includes_legacy_genesis_memory"] is False

        a.consent("memory",False)
        assert a.export_profile()["records"]==[r for r in exported["records"] if r["kind"]=="preference"]
        denied(lambda: a.recall("memory"))
        assert a.recall("preference")[0]["value"]=="light"
        a.consent("proactive",False)
        denied(lambda: a.attention())
        assert a.export_profile()["nudges"]==[]
        a.consent("provenance",False)
        assert a.export_profile()["claims"]==[]
        gone=a.erase_profile()
        assert gone["scope"]=="new_ux_tables_only"
        assert not any(a.consents().values())
        assert b.recall("memory")[0]["value"]=="SOUTH"
        store.close()
        assert UserCapabilityServices(Store(state),"bob").recall("memory")[0]["value"]=="SOUTH"

    with TemporaryDirectory() as tmp:
        model=Genesis(state_path=Path(tmp)/"model.db",workspace=Path(tmp)/"workspace",
                      enable_ollama=False,profile_id="operator")
        assert not model.ux_consents()["memory"]
        model.ux_set_consent("memory",True)
        model.ux_remember("memory","demo","stored")
        assert model.ux_recall("memory")[0]["value"]=="stored"
        assert model.ux_export_profile()["profile"]=="operator"
        model.close()

    # Do not mount the new profile service directly as an unauthenticated HTTP API.
    from genesis.api import app
    paths={r.path for r in app.routes}
    assert all(not p.startswith("/ux") and not p.startswith("/profile") for p in paths)
    print("USER_CAPABILITIES=PASS")


if __name__=="__main__":
    run()
