"""Opt-in hierarchical/associative memory for Genesis.

This is *retrieval memory*, not neural weight training, consciousness, or an
Aurora execution capability. Kyro must authenticate the profile_id supplied to
Genesis. Nothing from these records is automatically executed as a procedure.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Sequence

from .storage import Store, norm, utc_now

_WORD = re.compile(r"\w+", re.UNICODE)
_TIERS = {"transient", "working", "short", "long"}
_KINDS = {"semantic", "episodic", "procedural"}
_DEFAULT_TTL = {"transient": 45, "working": 900, "short": 86400, "long": None}


class MemoryNetworkError(ValueError):
    pass


def _str(value: str, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise MemoryNetworkError(f"{name} must have 1-{maximum} characters")
    return value.strip()


def _float(value: float, name: str) -> float:
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise MemoryNetworkError(f"{name} must be a number between 0 and 1") from exc
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise MemoryNetworkError(f"{name} must be a finite number between 0 and 1")
    return number


def _expires(ttl_seconds: int | None) -> str | None:
    if ttl_seconds is None:
        return None
    if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 365 * 86400:
        raise MemoryNetworkError("TTL must be 1 second to 365 days")
    return (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    ab = sum(x * y for x, y in zip(a, b))
    aa = math.sqrt(sum(x * x for x in a))
    bb = math.sqrt(sum(y * y for y in b))
    return max(0.0, ab / aa / bb) if aa and bb else 0.0


class MemoryNetwork:
    """L0 cache, volatile transient, session memory, durable typed records and links.

    All public methods check consent. The existing Genesis Store owns the SQLite
    connection and transactions; memory rows never confer Aurora permissions.
    An optional caller-provided text encoder enables actual dense similarity,
    but the default is deterministic lexical + associative retrieval, no GPU/API.
    """

    def __init__(self, store: Store, profile_id: str, *,
                 encoder: Callable[[str], Sequence[float]] | None = None,
                 encoder_id: str = ""):
        self.store = store
        self.profile = _str(profile_id, "profile_id", 120)
        self.encoder = encoder
        self.encoder_id = _str(encoder_id, "encoder_id", 100) if encoder else ""
        if encoder and not encoder_id:
            raise MemoryNetworkError("encoder_id is required for neural vectors")
        self._volatile: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
        self._hot: OrderedDict[tuple[str, str], tuple[int, float, list[dict[str, Any]]]] = OrderedDict()
        with self.store.tx() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS ux_consents (
                    profile TEXT NOT NULL, scope TEXT NOT NULL,
                    enabled INTEGER NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY(profile,scope)
                );
                CREATE TABLE IF NOT EXISTS mn_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile TEXT NOT NULL, thread TEXT NOT NULL,
                    tier TEXT NOT NULL, kind TEXT NOT NULL,
                    item_key TEXT NOT NULL, key_norm TEXT NOT NULL,
                    content TEXT NOT NULL, source TEXT NOT NULL,
                    confidence REAL NOT NULL, importance REAL NOT NULL,
                    embedding_json TEXT, embedding_model TEXT,
                    created_at TEXT NOT NULL, expires_at TEXT,
                    status TEXT NOT NULL DEFAULT 'active'
                );
                CREATE INDEX IF NOT EXISTS ix_mn_lookup
                    ON mn_items(profile,status,thread,tier,kind,key_norm);
                CREATE INDEX IF NOT EXISTS ix_mn_expiry
                    ON mn_items(profile,status,expires_at);
                CREATE TABLE IF NOT EXISTS mn_links (
                    profile TEXT NOT NULL, src INTEGER NOT NULL, dst INTEGER NOT NULL,
                    relation TEXT NOT NULL, weight REAL NOT NULL,
                    reinforced INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(profile,src,dst),
                    FOREIGN KEY(src) REFERENCES mn_items(id) ON DELETE CASCADE,
                    FOREIGN KEY(dst) REFERENCES mn_items(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS ix_mn_links_dst ON mn_links(profile,dst);
                CREATE TABLE IF NOT EXISTS mn_revisions (
                    profile TEXT PRIMARY KEY, revision INTEGER NOT NULL DEFAULT 0
                );
                CREATE TRIGGER IF NOT EXISTS mn_revoke_consent
                AFTER UPDATE OF enabled ON ux_consents
                WHEN NEW.scope='memory' AND NEW.enabled=0
                BEGIN
                    DELETE FROM mn_items WHERE profile=NEW.profile;
                    INSERT INTO mn_revisions(profile,revision) VALUES(NEW.profile,1)
                    ON CONFLICT(profile) DO UPDATE SET revision=revision+1;
                END;
            """)
            # FTS5 may be omitted in lean SQLite builds; fallback remains usable.
            try:
                db.executescript("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS mn_fts USING fts5(
                        item_key, content, content='mn_items', content_rowid='id',
                        tokenize='unicode61'
                    );
                    CREATE TRIGGER IF NOT EXISTS mn_fts_insert AFTER INSERT ON mn_items BEGIN
                        INSERT INTO mn_fts(rowid,item_key,content)
                        VALUES(new.id,new.item_key,new.content);
                    END;
                    CREATE TRIGGER IF NOT EXISTS mn_fts_delete AFTER DELETE ON mn_items BEGIN
                        INSERT INTO mn_fts(mn_fts,rowid,item_key,content)
                        VALUES('delete',old.id,old.item_key,old.content);
                    END;
                    CREATE TRIGGER IF NOT EXISTS mn_fts_update AFTER UPDATE ON mn_items BEGIN
                        INSERT INTO mn_fts(mn_fts,rowid,item_key,content)
                        VALUES('delete',old.id,old.item_key,old.content);
                        INSERT INTO mn_fts(rowid,item_key,content)
                        VALUES(new.id,new.item_key,new.content);
                    END;
                """)
                self.fts = True
            except Exception:
                self.fts = False

    def _require(self, db) -> None:
        row = db.execute("SELECT enabled FROM ux_consents WHERE profile=? AND scope='memory'",
                         (self.profile,)).fetchone()
        if not row or row[0] != 1:
            self.clear_volatile()
            raise MemoryNetworkError("memory consent is not enabled for this profile")

    def _rev(self, db) -> int:
        row = db.execute("SELECT revision FROM mn_revisions WHERE profile=?", (self.profile,)).fetchone()
        return row[0] if row else 0

    def _bump(self, db) -> None:
        db.execute("INSERT INTO mn_revisions(profile,revision) VALUES(?,1) "
                   "ON CONFLICT(profile) DO UPDATE SET revision=revision+1", (self.profile,))
        self._hot.clear()

    def _vector(self, text: str) -> list[float] | None:
        if not self.encoder:
            return None
        values = [float(x) for x in self.encoder(text)]
        if not 1 <= len(values) <= 4096 or any(not math.isfinite(v) for v in values):
            raise MemoryNetworkError("encoder returned invalid vector")
        return values

    def clear_volatile(self) -> None:
        self._volatile.clear()
        self._hot.clear()

    def remember(self, tier: str, kind: str, key: str, content: str, *,
                 thread: str = "default", ttl_seconds: int | None = None,
                 source: str = "user_explicit", confidence: float = 1.0,
                 importance: float = 0.5) -> dict[str, Any]:
        if tier not in _TIERS or kind not in _KINDS:
            raise MemoryNetworkError("invalid tier or kind")
        key = _str(key, "key", 160)
        content = _str(content, "content", 4000)
        thread = _str(thread, "thread", 120)
        source = _str(source, "source", 200)
        confidence = _float(confidence, "confidence")
        importance = _float(importance, "importance")
        if tier == "long" and source.casefold().startswith("untrusted"):
            raise MemoryNetworkError("untrusted data cannot be promoted to long-term automatically")
        if ttl_seconds is None:
            ttl_seconds = _DEFAULT_TTL[tier]
        expiry = _expires(ttl_seconds)
        with self.store.tx() as db:
            self._require(db)
            if tier == "transient":
                # Deliberately no persistent copy or learned association.
                self._volatile[(thread, norm(key))] = (
                    time.monotonic() + (ttl_seconds or 45),
                    {"tier": tier, "kind": kind, "key": key, "content": content,
                     "source": source, "confidence": confidence, "importance": importance,
                     "expires_at": expiry})
                if len(self._volatile) > 128:
                    self._volatile.pop(next(iter(self._volatile)))
                return {"tier": "transient", "key": key, "stored": "ram_only"}
            scope_thread = "" if tier == "long" else thread
            existing = db.execute("""SELECT id FROM mn_items WHERE profile=? AND thread=?
                AND tier=? AND kind=? AND key_norm=? AND status='active'""",
                (self.profile, scope_thread, tier, kind, norm(key))).fetchall()
            for item in existing:
                db.execute("UPDATE mn_items SET status='superseded' WHERE id=?", (item[0],))
            vec = self._vector(key + " " + content)
            cur = db.execute("""INSERT INTO mn_items(
                profile,thread,tier,kind,item_key,key_norm,content,source,confidence,
                importance,embedding_json,embedding_model,created_at,expires_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (self.profile, scope_thread, tier, kind, key, norm(key), content,
                 source, confidence, importance, json.dumps(vec) if vec else None,
                 self.encoder_id if vec else None, utc_now(), expiry))
            if tier in {"working", "short"}:
                maximum = 40 if tier == "working" else 240
                db.execute("""UPDATE mn_items SET status='pruned' WHERE id IN (
                    SELECT id FROM mn_items WHERE profile=? AND thread=? AND tier=?
                    AND status='active' ORDER BY created_at DESC,id DESC LIMIT -1 OFFSET ?
                )""", (self.profile, scope_thread, tier, maximum))
            self._bump(db)
            return {"id": int(cur.lastrowid), "tier": tier, "kind": kind,
                    "key": key, "expires_at": expiry, "replaced": len(existing)}

    def link(self, src: int, dst: int, *, relation: str = "related",
             weight: float = 0.6) -> dict[str, Any]:
        relation = _str(relation, "relation", 80)
        weight = _float(weight, "weight")
        if type(src) is not int or type(dst) is not int or src == dst:
            raise MemoryNetworkError("link needs two distinct integer IDs")
        with self.store.tx() as db:
            self._require(db)
            rows = db.execute("SELECT id FROM mn_items WHERE profile=? AND status='active' "
                              "AND id IN (?,?) AND (expires_at IS NULL OR expires_at>?)",
                              (self.profile, src, dst, utc_now())).fetchall()
            if len(rows) != 2:
                raise MemoryNetworkError("both memory IDs must belong to this profile and be active")
            db.execute("""INSERT INTO mn_links(profile,src,dst,relation,weight) VALUES(?,?,?,?,?)
                    ON CONFLICT(profile,src,dst) DO UPDATE SET relation=excluded.relation,
                    weight=excluded.weight""", (self.profile, src, dst, relation, weight))
            self._bump(db)
        return {"from": src, "to": dst, "relation": relation, "weight": weight}

    def reinforce(self, src: int, dst: int, *, positive: bool = True) -> float:
        """Feedback-based associative plasticity, not training neural parameters."""
        with self.store.tx() as db:
            self._require(db)
            row = db.execute("SELECT weight FROM mn_links WHERE profile=? AND src=? AND dst=?",
                             (self.profile, src, dst)).fetchone()
            if row is None:
                raise MemoryNetworkError("link not found")
            weight = round(max(0.05, min(1.0, row[0] + (0.1 if positive else -0.1))), 3)
            db.execute("UPDATE mn_links SET weight=?,reinforced=reinforced+1 "
                       "WHERE profile=? AND src=? AND dst=?", (weight, self.profile, src, dst))
            self._bump(db)
        return weight

    def recall(self, query: str, *, thread: str = "default", limit: int = 8,
               include_transient: bool = True) -> list[dict[str, Any]]:
        query = _str(query, "query", 500)
        thread = _str(thread, "thread", 120)
        if type(limit) is not int or not 1 <= limit <= 50:
            raise MemoryNetworkError("limit must be 1-50")
        qterms = list(dict.fromkeys(w.casefold() for w in _WORD.findall(query)))[:16]
        with self.store.tx() as db:
            self._require(db)
            now = utc_now()
            revision = self._rev(db)
            cache_key = (thread, norm(query))
            cached = self._hot.get(cache_key)
            if cached and cached[0] == revision and time.monotonic() < cached[1]:
                result = [r for r in cached[2] if r["expires_at"] is None or r["expires_at"] > now]
                self._hot.move_to_end(cache_key)
            else:
                # FTS is a bounded shortlist, augmented by direct exact-key matches.
                candidate_ids: set[int] = set()
                if self.fts and qterms:
                    # Quoted isolated tokens avoid MATCH operator injection.
                    match = " OR ".join('"' + w.replace('"', '""') + '"' for w in qterms)
                    try:
                        found = db.execute("""SELECT m.id FROM mn_fts f JOIN mn_items m ON m.id=f.rowid
                            WHERE mn_fts MATCH ? AND m.profile=? AND m.status='active'
                            AND (m.thread=? OR m.tier='long')
                            AND (m.expires_at IS NULL OR m.expires_at>?) LIMIT 200""",
                            (match, self.profile, thread, now)).fetchall()
                        candidate_ids.update(int(r[0]) for r in found)
                    except Exception:
                        pass
                direct = db.execute("""SELECT id FROM mn_items WHERE profile=? AND status='active'
                    AND (thread=? OR tier='long') AND (expires_at IS NULL OR expires_at>?)
                    AND (key_norm=? OR content LIKE ?) LIMIT 100""",
                    (self.profile, thread, now, norm(query), "%" + query + "%")).fetchall()
                candidate_ids.update(int(r[0]) for r in direct)
                if self.encoder:
                    # v1 exact dense scan is bounded; scale out to vector ANN later.
                    dense = db.execute("""SELECT id FROM mn_items WHERE profile=? AND status='active'
                        AND (thread=? OR tier='long') AND embedding_model=?
                        AND (expires_at IS NULL OR expires_at>?) ORDER BY id DESC LIMIT 1000""",
                        (self.profile, thread, self.encoder_id, now)).fetchall()
                    candidate_ids.update(int(r[0]) for r in dense)
                if not candidate_ids:
                    result = []
                else:
                    ids = sorted(candidate_ids)
                    rows = db.execute("SELECT * FROM mn_items WHERE id IN (" +
                        ",".join("?" for _ in ids) + ")", ids).fetchall()
                    qvec = self._vector(query) if self.encoder else None
                    scored: dict[int, dict[str, Any]] = {}
                    for row in rows:
                        rec = dict(row)
                        haystack = (rec["item_key"] + " " + rec["content"]).casefold()
                        word_overlap = sum(1 for w in qterms if w in haystack)
                        lexical = word_overlap / max(1, len(qterms))
                        exact = 2.0 if rec["key_norm"] == norm(query) else 0.0
                        dense_score = 0.0
                        if qvec and rec["embedding_json"] and rec["embedding_model"] == self.encoder_id:
                            dense_score = _cosine(qvec, json.loads(rec["embedding_json"]))
                        score = exact + lexical * 1.2 + dense_score * 1.1
                        if score <= 0.0:
                            continue
                        score *= (0.6 + 0.4 * rec["confidence"]) * (0.7 + 0.3 * rec["importance"])
                        rec["score"] = round(score, 5)
                        rec["via"] = "direct"
                        rec.pop("embedding_json", None)
                        scored[rec["id"]] = rec
                    # One-hop directed neural-style associations: only grounded,
                    # visible, nonexpired target memories can be activated.
                    seeds = sorted(scored.values(), key=lambda r: r["score"], reverse=True)[:5]
                    for seed in seeds:
                        edges = db.execute("""SELECT m.*,l.weight,l.relation FROM mn_links l
                            JOIN mn_items m ON m.id=l.dst
                            WHERE l.profile=? AND l.src=? AND m.profile=?
                            AND m.status='active' AND (m.thread=? OR m.tier='long')
                            AND (m.expires_at IS NULL OR m.expires_at>?)
                            ORDER BY l.weight DESC LIMIT 8""",
                            (self.profile, seed["id"], self.profile, thread, now)).fetchall()
                        for edge in edges:
                            rec = dict(edge)
                            activation = round(seed["score"] * 0.38 * rec["weight"], 5)
                            if rec["id"] in scored and scored[rec["id"]]["score"] >= activation:
                                continue
                            rec["score"] = activation
                            rec["via"] = f"association:{rec['relation']}"
                            rec.pop("embedding_json", None)
                            rec.pop("weight", None)
                            rec.pop("relation", None)
                            scored[rec["id"]] = rec
                    result = sorted(scored.values(), key=lambda r: (r["score"], r["id"]), reverse=True)[:50]
                self._hot[cache_key] = (revision, time.monotonic() + 3.0, result)
                if len(self._hot) > 64:
                    self._hot.popitem(last=False)
            out = result[:limit]
            if include_transient:
                for (session, key), (deadline, item) in list(self._volatile.items()):
                    if time.monotonic() >= deadline:
                        del self._volatile[(session, key)]
                    elif session == thread and (norm(query) in key or norm(query) in norm(item["content"])):
                        out = [dict(item, score=3.0, via="ram")]+out
                        break
            return out[:limit]

    def promote(self, item_id: int) -> dict[str, Any]:
        """Human/control-plane approved promotion, never an automatic model action."""
        with self.store.tx() as db:
            self._require(db)
            row = db.execute("SELECT * FROM mn_items WHERE id=? AND profile=? AND status='active'",
                             (item_id, self.profile)).fetchone()
            if row is None or row["tier"] == "long":
                raise MemoryNetworkError("promotion requires an active working/short item")
            if row["expires_at"] and row["expires_at"] <= utc_now():
                raise MemoryNetworkError("cannot promote expired memory")
            if row["source"].casefold().startswith("untrusted"):
                raise MemoryNetworkError("untrusted item requires separate human review")
            details = dict(row)
        return self.remember("long", details["kind"], details["item_key"], details["content"],
                             source=f"promoted:{item_id}:{details['source']}",
                             confidence=details["confidence"], importance=details["importance"])

    def forget(self, item_id: int) -> bool:
        with self.store.tx() as db:
            self._require(db)
            row = db.execute("SELECT tier,kind,thread,key_norm FROM mn_items "
                             "WHERE id=? AND profile=?", (item_id, self.profile)).fetchone()
            if row is None:
                return False
            # Erase the key's revision history as well as its live value.
            changed = db.execute("""DELETE FROM mn_items WHERE profile=? AND tier=?
                AND kind=? AND thread=? AND key_norm=?""",
                (self.profile, row["tier"], row["kind"], row["thread"], row["key_norm"])).rowcount
            if changed:
                self._bump(db)
            return bool(changed)

    def purge_expired(self) -> int:
        with self.store.tx() as db:
            self._require(db)
            count = db.execute("DELETE FROM mn_items WHERE profile=? AND expires_at IS NOT NULL "
                               "AND expires_at<=?", (self.profile, utc_now())).rowcount
            if count:
                self._bump(db)
        return int(count)

    def erase_profile(self) -> int:
        with self.store.tx() as db:
            self._require(db)
            count = db.execute("DELETE FROM mn_items WHERE profile=?", (self.profile,)).rowcount
            self._bump(db)
        self.clear_volatile()
        return count

    def stats(self) -> dict[str, Any]:
        with self.store.tx() as db:
            self._require(db)
            rows = db.execute("""SELECT tier,kind,COUNT(*) AS count FROM mn_items
                WHERE profile=? AND status='active' AND (expires_at IS NULL OR expires_at>?)
                GROUP BY tier,kind""", (self.profile, utc_now())).fetchall()
            links = db.execute("SELECT COUNT(*) FROM mn_links WHERE profile=?", (self.profile,)).fetchone()[0]
            return {"tiers": [dict(r) for r in rows], "links": links,
                    "fts_enabled": self.fts, "neural_encoder_configured": bool(self.encoder),
                    "transient_entries": len(self._volatile)}
