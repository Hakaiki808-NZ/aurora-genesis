from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(text: str) -> str:
    return " ".join(text.casefold().strip().split())


class Store:
    """Versioned persistent state for Genesis v0.1.

    SQLite is used intentionally: it gives atomic revisions, restart persistence,
    inspectability, and clean export without relying on the neural context window.
    """

    SCHEMA_VERSION = 6

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute("PRAGMA temp_store=MEMORY")
        self.db.execute("PRAGMA cache_size=-8192")
        self.db.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    @contextmanager
    def tx(self):
        with self._lock:
            try:
                yield self.db
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

    def _migrate(self) -> None:
        with self.tx() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta(
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS episodes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL, role TEXT NOT NULL, text TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 0.5
                );
                CREATE TABLE IF NOT EXISTS facts(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    namespace TEXT NOT NULL DEFAULT 'world',
                    key TEXT NOT NULL, key_norm TEXT NOT NULL,
                    value TEXT NOT NULL, value_norm TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    source TEXT NOT NULL DEFAULT 'interaction',
                    truth_state TEXT NOT NULL DEFAULT 'ASSERTED',
                    status TEXT NOT NULL DEFAULT 'active',
                    use_count INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(namespace, key_norm)
                );
                CREATE INDEX IF NOT EXISTS idx_facts_active_namespace_key ON facts(status, namespace, key_norm);
                CREATE INDEX IF NOT EXISTS idx_facts_active_updated ON facts(status, updated_at);
                CREATE TABLE IF NOT EXISTS fact_history(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL, fact_id INTEGER,
                    namespace TEXT NOT NULL, key TEXT NOT NULL,
                    old_value TEXT, new_value TEXT NOT NULL,
                    old_confidence REAL, new_confidence REAL NOT NULL,
                    source TEXT NOT NULL,
                    FOREIGN KEY(fact_id) REFERENCES facts(id)
                );
                CREATE TABLE IF NOT EXISTS triples(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    subject TEXT NOT NULL, subject_norm TEXT NOT NULL,
                    relation TEXT NOT NULL, relation_norm TEXT NOT NULL,
                    object TEXT NOT NULL, object_norm TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    source TEXT NOT NULL DEFAULT 'interaction',
                    truth_state TEXT NOT NULL DEFAULT 'ASSERTED',
                    status TEXT NOT NULL DEFAULT 'active'
                );
                CREATE INDEX IF NOT EXISTS idx_triples_sro ON triples(subject_norm, relation_norm, object_norm);
                CREATE INDEX IF NOT EXISTS idx_triples_active_subject ON triples(status, subject_norm, relation_norm);
                CREATE TABLE IF NOT EXISTS rules(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    trigger TEXT NOT NULL, trigger_norm TEXT NOT NULL,
                    response TEXT,
                    condition_json TEXT,
                    consequence_json TEXT,
                    priority INTEGER NOT NULL DEFAULT 100,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    source TEXT NOT NULL DEFAULT 'interaction',
                    use_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS decisions(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL, input_text TEXT NOT NULL,
                    candidates_json TEXT NOT NULL,
                    chosen_action TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    confidence REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reflections(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL, decision_id INTEGER,
                    outcome TEXT NOT NULL, note TEXT NOT NULL,
                    FOREIGN KEY(decision_id) REFERENCES decisions(id)
                );
                CREATE TABLE IF NOT EXISTS goals(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    goal TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
                    priority INTEGER NOT NULL DEFAULT 50,
                    context_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS goal_steps(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_id INTEGER NOT NULL,
                    step_no INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    action TEXT NOT NULL,
                    args_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'pending',
                    result_json TEXT,
                    FOREIGN KEY(goal_id) REFERENCES goals(id)
                );
                CREATE TABLE IF NOT EXISTS skills(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    name TEXT NOT NULL UNIQUE, description TEXT NOT NULL,
                    steps_json TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
                    source TEXT NOT NULL DEFAULT 'interaction'
                );
                CREATE TABLE IF NOT EXISTS training_examples(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL, input_text TEXT NOT NULL,
                    target_text TEXT NOT NULL, source TEXT NOT NULL,
                    quality REAL NOT NULL DEFAULT 1.0,
                    consumed INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS policy_audit(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL, stage TEXT NOT NULL, subject TEXT NOT NULL,
                    verdict TEXT NOT NULL, commandments_json TEXT NOT NULL,
                    reason TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS action_transactions(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    state TEXT NOT NULL, action_type TEXT NOT NULL,
                    action_json TEXT NOT NULL, result_json TEXT,
                    engine_request_id TEXT, engine_receipt_id TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_action_transactions_state ON action_transactions(state, id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_action_transactions_receipt ON action_transactions(engine_receipt_id) WHERE engine_receipt_id IS NOT NULL;
                """
            )
            fact_cols={r[1] for r in db.execute("PRAGMA table_info(facts)").fetchall()}
            if "truth_state" not in fact_cols:
                db.execute("ALTER TABLE facts ADD COLUMN truth_state TEXT NOT NULL DEFAULT 'ASSERTED'")
            triple_cols={r[1] for r in db.execute("PRAGMA table_info(triples)").fetchall()}
            if "truth_state" not in triple_cols:
                db.execute("ALTER TABLE triples ADD COLUMN truth_state TEXT NOT NULL DEFAULT 'ASSERTED'")
            db.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)",
                (str(self.SCHEMA_VERSION),),
            )

    def add_episode(self, role: str, text: str, importance: float = 0.5) -> int:
        with self.tx() as db:
            cur = db.execute(
                "INSERT INTO episodes(ts,role,text,importance) VALUES(?,?,?,?)",
                (utc_now(), role, text, float(importance)),
            )
            return int(cur.lastrowid)

    def recent(self, limit: int = 8) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM episodes ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def learn_fact(self, key: str, value: str, namespace: str = "world", confidence: float = 1.0, source: str = "interaction", truth_state: str = "ASSERTED") -> dict[str, Any]:
        key, value, namespace = key.strip(), value.strip(), namespace.strip() or "world"
        truth_state=truth_state.upper()
        if truth_state not in {"ASSERTED","INFERRED","CORROBORATED","VERIFIED","DISPUTED","SUPERSEDED"}: raise ValueError("invalid truth state")
        kn, vn, now = norm(key), norm(value), utc_now()
        with self.tx() as db:
            row = db.execute(
                "SELECT * FROM facts WHERE namespace=? AND key_norm=?", (namespace, kn)
            ).fetchone()
            if row:
                old = dict(row)
                status = "unchanged" if old["value_norm"] == vn else "revised"
                db.execute(
                    "UPDATE facts SET updated_at=?,key=?,value=?,value_norm=?,confidence=?,source=?,truth_state=?,status='active' WHERE id=?",
                    (now, key, value, vn, float(confidence), source, truth_state, row["id"]),
                )
                if status == "revised" or float(confidence) != float(old["confidence"]):
                    db.execute(
                        """INSERT INTO fact_history(ts,fact_id,namespace,key,old_value,new_value,old_confidence,new_confidence,source)
                           VALUES(?,?,?,?,?,?,?,?,?)""",
                        (now, row["id"], namespace, key, old["value"], value, old["confidence"], float(confidence), source),
                    )
                fid = int(row["id"])
            else:
                cur = db.execute(
                    """INSERT INTO facts(created_at,updated_at,namespace,key,key_norm,value,value_norm,confidence,source,truth_state)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (now, now, namespace, key, kn, value, vn, float(confidence), source, truth_state),
                )
                fid = int(cur.lastrowid)
                db.execute(
                    """INSERT INTO fact_history(ts,fact_id,namespace,key,old_value,new_value,old_confidence,new_confidence,source)
                       VALUES(?,?,?,?,NULL,?,NULL,?,?)""",
                    (now, fid, namespace, key, value, float(confidence), source),
                )
                status = "learned"
        return {"kind": "fact", "status": status, "id": fid, "namespace": namespace, "key": key, "value": value, "confidence": float(confidence), "truth_state": truth_state}

    def get_fact(self, key: str, namespace: str | None = None) -> dict[str, Any] | None:
        if namespace:
            row = self.db.execute(
                "SELECT * FROM facts WHERE namespace=? AND key_norm=? AND status='active'",
                (namespace, norm(key)),
            ).fetchone()
        else:
            row = self.db.execute(
                "SELECT * FROM facts WHERE key_norm=? AND status='active' ORDER BY confidence DESC, updated_at DESC LIMIT 1",
                (norm(key),),
            ).fetchone()
        return dict(row) if row else None

    def all_facts(self, namespace: str | None=None) -> list[dict[str, Any]]:
        if namespace is None:
            rows=self.db.execute("SELECT * FROM facts WHERE status='active' ORDER BY id")
        else:
            rows=self.db.execute("SELECT * FROM facts WHERE status='active' AND namespace=? ORDER BY id",(namespace,))
        return [dict(r) for r in rows]

    def fact_revision_token(self) -> tuple[int,str]:
        row=self.db.execute("SELECT COUNT(*),COALESCE(MAX(updated_at),'') FROM facts WHERE status='active'").fetchone()
        return int(row[0]),str(row[1])

    def mark_fact_used(self, fact_id: int) -> None:
        with self.tx() as db:
            db.execute("UPDATE facts SET use_count=use_count+1 WHERE id=?", (fact_id,))

    def add_triple(self, subject: str, relation: str, object_: str, confidence: float = 1.0, source: str = "interaction", truth_state: str = "ASSERTED") -> dict[str, Any]:
        subject, relation, object_ = subject.strip(), relation.strip(), object_.strip()
        truth_state=truth_state.upper()
        if truth_state not in {"ASSERTED","INFERRED","CORROBORATED","VERIFIED","DISPUTED","SUPERSEDED"}: raise ValueError("invalid truth state")
        sn, rn, on = norm(subject), norm(relation), norm(object_)
        with self.tx() as db:
            existing = db.execute(
                "SELECT id FROM triples WHERE subject_norm=? AND relation_norm=? AND object_norm=? AND status='active'",
                (sn, rn, on),
            ).fetchone()
            if existing:
                return {"kind":"triple","status":"unchanged","id":int(existing["id"]),"subject":subject,"relation":relation,"object":object_}
            cur = db.execute(
                """INSERT INTO triples(created_at,subject,subject_norm,relation,relation_norm,object,object_norm,confidence,source,truth_state)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (utc_now(), subject, sn, relation, rn, object_, on, float(confidence), source, truth_state),
            )
            return {"kind":"triple","status":"learned","id":int(cur.lastrowid),"subject":subject,"relation":relation,"object":object_}

    def triples(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.db.execute("SELECT * FROM triples WHERE status='active' ORDER BY id")]

    def learn_response_rule(self, trigger: str, response: str, source: str = "interaction", priority: int = 120) -> dict[str, Any]:
        tn, now = norm(trigger), utc_now()
        with self.tx() as db:
            row = db.execute("SELECT * FROM rules WHERE kind='response' AND trigger_norm=?", (tn,)).fetchone()
            if row:
                db.execute("UPDATE rules SET updated_at=?,trigger=?,response=?,priority=?,enabled=1,source=? WHERE id=?", (now, trigger, response, priority, source, row["id"]))
                rid, status = int(row["id"]), "revised"
            else:
                cur = db.execute("""INSERT INTO rules(created_at,updated_at,kind,trigger,trigger_norm,response,priority,source)
                                    VALUES(?,?,?,?,?,?,?,?)""", (now,now,"response",trigger,tn,response,priority,source))
                rid, status = int(cur.lastrowid), "learned"
        return {"kind":"rule","status":status,"id":rid,"trigger":trigger,"response":response}

    def response_rule(self, text: str) -> dict[str, Any] | None:
        nt = norm(text)
        rows = self.db.execute("SELECT * FROM rules WHERE kind='response' AND enabled=1 ORDER BY priority DESC,id DESC").fetchall()
        for row in rows:
            if nt == row["trigger_norm"]:
                return dict(row)
        return None

    def mark_rule_used(self, rule_id: int) -> None:
        with self.tx() as db:
            db.execute("UPDATE rules SET use_count=use_count+1 WHERE id=?", (rule_id,))

    def record_decision(self, input_text: str, candidates: Iterable[dict[str, Any]], chosen_action: str, rationale: str, confidence: float) -> int:
        with self.tx() as db:
            cur = db.execute("""INSERT INTO decisions(ts,input_text,candidates_json,chosen_action,rationale,confidence)
                              VALUES(?,?,?,?,?,?)""", (utc_now(),input_text,json.dumps(list(candidates),ensure_ascii=False),chosen_action,rationale,float(confidence)))
            return int(cur.lastrowid)

    def last_decision(self) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM decisions ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def last_reflection(self) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM reflections ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def add_reflection(self, decision_id: int | None, outcome: str, note: str) -> int:
        with self.tx() as db:
            cur = db.execute("INSERT INTO reflections(ts,decision_id,outcome,note) VALUES(?,?,?,?)", (utc_now(),decision_id,outcome,note))
            return int(cur.lastrowid)

    def create_goal(self, goal: str, priority: int = 50, context: dict[str, Any] | None = None) -> int:
        now=utc_now()
        with self.tx() as db:
            cur=db.execute("INSERT INTO goals(created_at,updated_at,goal,status,priority,context_json) VALUES(?,?,?,'active',?,?)", (now,now,goal,int(priority),json.dumps(context or {})))
            return int(cur.lastrowid)

    def set_goal_steps(self, goal_id: int, steps: list[dict[str, Any]]) -> None:
        with self.tx() as db:
            db.execute("DELETE FROM goal_steps WHERE goal_id=?", (goal_id,))
            for i,s in enumerate(steps,1):
                db.execute("""INSERT INTO goal_steps(goal_id,step_no,description,action,args_json,status)
                              VALUES(?,?,?,?,?,'pending')""", (goal_id,i,s["description"],s["action"],json.dumps(s.get("args",{}))))

    def goal(self, goal_id: int) -> dict[str, Any] | None:
        row=self.db.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
        if not row: return None
        out=dict(row)
        out["steps"]=[dict(r) for r in self.db.execute("SELECT * FROM goal_steps WHERE goal_id=? ORDER BY step_no", (goal_id,))]
        return out

    def active_goals(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.db.execute("SELECT * FROM goals WHERE status='active' ORDER BY priority DESC,id")]

    def complete_step(self, step_id: int, result: Any, ok: bool = True) -> None:
        with self.tx() as db:
            db.execute("UPDATE goal_steps SET status=?,result_json=? WHERE id=?", ("done" if ok else "failed",json.dumps(result,ensure_ascii=False,default=str),step_id))

    def set_goal_status(self, goal_id: int, status: str) -> None:
        with self.tx() as db:
            db.execute("UPDATE goals SET status=?,updated_at=? WHERE id=?", (status,utc_now(),goal_id))

    def deactivate_fact(self, key: str, namespace: str | None = None, source: str = "interaction") -> bool:
        with self.tx() as db:
            if namespace:
                row=db.execute("SELECT * FROM facts WHERE namespace=? AND key_norm=? AND status='active'",(namespace,norm(key))).fetchone()
            else:
                row=db.execute("SELECT * FROM facts WHERE key_norm=? AND status='active' ORDER BY confidence DESC,updated_at DESC LIMIT 1",(norm(key),)).fetchone()
            if not row:
                return False
            d=dict(row); now=utc_now()
            db.execute("UPDATE facts SET status='inactive',truth_state='SUPERSEDED',updated_at=?,source=? WHERE id=?",(now,source,row["id"]))
            db.execute("""INSERT INTO fact_history(ts,fact_id,namespace,key,old_value,new_value,old_confidence,new_confidence,source)
                          VALUES(?,?,?,?,?,?,?,?,?)""",(now,row["id"],d["namespace"],d["key"],d["value"],"[forgotten]",d["confidence"],0.0,source))
            return True

    def reset_failed_goal_steps(self, goal_id: int) -> int:
        with self.tx() as db:
            cur=db.execute("UPDATE goal_steps SET status='pending',result_json=NULL WHERE goal_id=? AND status='failed'",(goal_id,))
            if cur.rowcount:
                db.execute("UPDATE goals SET status='active',updated_at=? WHERE id=?",(utc_now(),goal_id))
            return int(cur.rowcount)

    def cancel_goal(self, goal_id: int) -> bool:
        with self.tx() as db:
            row=db.execute("SELECT id FROM goals WHERE id=?",(goal_id,)).fetchone()
            if not row:
                return False
            db.execute("UPDATE goals SET status='cancelled',updated_at=? WHERE id=?",(utc_now(),goal_id))
            return True

    def goals(self, limit: int = 100) -> list[dict[str, Any]]:
        rows=self.db.execute("SELECT * FROM goals ORDER BY id DESC LIMIT ?",(int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def recent_decisions(self, limit: int = 20) -> list[dict[str, Any]]:
        rows=self.db.execute("SELECT * FROM decisions ORDER BY id DESC LIMIT ?",(int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def learn_skill(self, name: str, description: str, steps: list[dict[str, Any]], source: str="interaction") -> dict[str,Any]:
        now=utc_now(); payload=json.dumps(steps,ensure_ascii=False)
        with self.tx() as db:
            row=db.execute("SELECT id FROM skills WHERE name=?", (name,)).fetchone()
            if row:
                db.execute("UPDATE skills SET updated_at=?,description=?,steps_json=?,enabled=1,source=? WHERE id=?", (now,description,payload,source,row["id"]))
                sid,status=int(row["id"]),"revised"
            else:
                cur=db.execute("INSERT INTO skills(created_at,updated_at,name,description,steps_json,source) VALUES(?,?,?,?,?,?)", (now,now,name,description,payload,source))
                sid,status=int(cur.lastrowid),"learned"
        return {"kind":"skill","status":status,"id":sid,"name":name}

    def skill(self, name: str) -> dict[str,Any] | None:
        row=self.db.execute("SELECT * FROM skills WHERE name=? AND enabled=1", (name,)).fetchone()
        if not row: return None
        d=dict(row); d["steps"]=json.loads(d.pop("steps_json")); return d

    def add_training_example(self, input_text: str, target_text: str, source: str="interaction", quality: float=1.0) -> int:
        with self.tx() as db:
            cur=db.execute("INSERT INTO training_examples(ts,input_text,target_text,source,quality) VALUES(?,?,?,?,?)", (utc_now(),input_text,target_text,source,float(quality)))
            return int(cur.lastrowid)

    def add_policy_audit(self, stage: str, subject: str, verdict: str, commandments: list[str], reason: str, details: dict[str,Any] | None=None) -> int:
        with self.tx() as db:
            cur=db.execute("INSERT INTO policy_audit(ts,stage,subject,verdict,commandments_json,reason,details_json) VALUES(?,?,?,?,?,?,?)",
                           (utc_now(),stage,subject,verdict,json.dumps(commandments,ensure_ascii=False),reason,json.dumps(details or {},ensure_ascii=False,default=str)))
            return int(cur.lastrowid)

    def recent_policy_audit(self, limit: int=50) -> list[dict[str,Any]]:
        rows=self.db.execute("SELECT * FROM policy_audit ORDER BY id DESC LIMIT ?",(int(limit),)).fetchall()
        out=[]
        for row in rows:
            d=dict(row); d["commandments"]=json.loads(d.pop("commandments_json")); d["details"]=json.loads(d.pop("details_json")); out.append(d)
        return out

    def prepare_action(self, action_id: str, action_type: str, action: dict[str,Any], engine_request_id: str | None=None) -> int:
        now=utc_now()
        with self.tx() as db:
            cur=db.execute("INSERT INTO action_transactions(action_id,created_at,updated_at,state,action_type,action_json,engine_request_id) VALUES(?,?,?,?,?,?,?)",
                           (action_id,now,now,"PREPARED",action_type,json.dumps(action,ensure_ascii=False,default=str),engine_request_id))
            return int(cur.lastrowid)

    def set_action_state(self, action_id: str, state: str, result: Any=None, engine_receipt_id: str | None=None) -> None:
        state=state.upper()
        if state not in {"PREPARED","EXECUTING","COMMITTED","FAILED","CANCELLED"}: raise ValueError("invalid action state")
        with self.tx() as db:
            db.execute("UPDATE action_transactions SET updated_at=?,state=?,result_json=?,engine_receipt_id=COALESCE(?,engine_receipt_id) WHERE action_id=?",
                       (utc_now(),state,json.dumps(result,ensure_ascii=False,default=str) if result is not None else None,engine_receipt_id,action_id))

    def action_transaction(self, action_id: str) -> dict[str,Any] | None:
        row=self.db.execute("SELECT * FROM action_transactions WHERE action_id=?",(action_id,)).fetchone()
        return dict(row) if row else None

    def recent_actions(self, limit: int=50) -> list[dict[str,Any]]:
        return [dict(r) for r in self.db.execute("SELECT * FROM action_transactions ORDER BY id DESC LIMIT ?",(int(limit),)).fetchall()]

    def action_by_engine_request(self, request_id: str) -> dict[str,Any] | None:
        row=self.db.execute("SELECT * FROM action_transactions WHERE engine_request_id=? ORDER BY id DESC LIMIT 1",(request_id,)).fetchone()
        return dict(row) if row else None

    def action_by_engine_receipt(self, receipt_id: str) -> dict[str,Any] | None:
        row=self.db.execute("SELECT * FROM action_transactions WHERE engine_receipt_id=? ORDER BY id DESC LIMIT 1",(receipt_id,)).fetchone()
        return dict(row) if row else None

    def pending_engine_actions(self, limit: int=100) -> list[dict[str,Any]]:
        rows=self.db.execute("SELECT * FROM action_transactions WHERE state='PREPARED' AND engine_request_id IS NOT NULL ORDER BY id LIMIT ?",(int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def set_fact_truth_state(self, key: str, truth_state: str, namespace: str | None=None) -> bool:
        truth_state=truth_state.upper()
        if truth_state not in {"ASSERTED","INFERRED","CORROBORATED","VERIFIED","DISPUTED","SUPERSEDED"}: raise ValueError("invalid truth state")
        with self.tx() as db:
            if namespace:
                row=db.execute("SELECT id FROM facts WHERE namespace=? AND key_norm=? AND status='active'",(namespace,norm(key))).fetchone()
            else:
                row=db.execute("SELECT id FROM facts WHERE key_norm=? AND status='active' ORDER BY confidence DESC,updated_at DESC LIMIT 1",(norm(key),)).fetchone()
            if not row: return False
            db.execute("UPDATE facts SET truth_state=?,updated_at=? WHERE id=?",(truth_state,utc_now(),row["id"]))
            return True

    def stats(self) -> dict[str,int]:
        names=["episodes","facts","fact_history","triples","rules","decisions","reflections","goals","goal_steps","skills","training_examples","policy_audit","action_transactions"]
        return {n:int(self.db.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0]) for n in names}

    def export_json(self, path: str | Path) -> Path:
        p=Path(path).expanduser().resolve(); p.parent.mkdir(parents=True,exist_ok=True)
        payload={"exported_at":utc_now(),"schema_version":self.SCHEMA_VERSION,"facts":self.all_facts(),"triples":self.triples(),"goals":self.active_goals(),"actions":self.recent_actions(10000),"stats":self.stats()}
        p.write_text(json.dumps(payload,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
        return p

    def backup(self, path: str | Path) -> Path:
        p=Path(path).expanduser().resolve(); p.parent.mkdir(parents=True,exist_ok=True)
        target=sqlite3.connect(p)
        try:
            with self._lock: self.db.backup(target)
        finally: target.close()
        return p

    def close(self) -> None:
        self.db.close()
