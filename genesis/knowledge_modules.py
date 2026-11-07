"""Installable, data-only subject packs for Genesis.

This is a reference knowledge-pack system, not a credential verifier, payment
processor, trusted publisher registry, or executable plugin loader.
All installed material remains untrusted reference DATA.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from .storage import Store

_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_WORD = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
_STOP = {"the", "a", "an", "and", "or", "is", "are", "was", "were",
         "can", "could", "do", "does", "did", "what", "why", "who", "how",
         "explain", "tell", "about", "with", "of", "on", "in", "at", "to",
         "for", "between", "relationship", "me", "you", "this", "that"}
_LANGUAGE_TAG = re.compile(r"^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-[A-Z]{2}|-[0-9]{3})?$")
_MAX_BYTES = 2_000_000
_MAX_CHAPTERS = 250


class KnowledgeModuleError(ValueError):
    """Invalid, incompatible, unlicensed, or conflicting package."""


def _terms(s: str) -> set[str]:
    return {t.casefold() for t in _WORD.findall(s) if t.casefold() not in _STOP}


def _required_string(obj: dict, key: str, maximum: int) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise KnowledgeModuleError(f"{key} must be a nonempty string of at most {maximum} characters")
    return value.strip()


def _validate(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise KnowledgeModuleError("package must be a JSON object")
    allowed = {"schema_version", "id", "title", "version", "publisher",
               "license", "distribution", "subject", "chapters", "category", "language_tag", "programme"}
    if set(raw) - allowed:
        raise KnowledgeModuleError("unknown package fields (executable capabilities are not supported)")
    if raw.get("schema_version") != 1 or isinstance(raw.get("schema_version"), bool):
        raise KnowledgeModuleError("unsupported knowledge-module schema")
    module_id = _required_string(raw, "id", 64)
    version = _required_string(raw, "version", 40)
    if module_id == "genesis-core":
        raise KnowledgeModuleError("Genesis Core is reserved and cannot be installed as data")
    if not _ID.fullmatch(module_id) or not _VERSION.fullmatch(version):
        raise KnowledgeModuleError("invalid module id or semantic version")
    distribution = raw.get("distribution", "open")
    if distribution != "open":
        raise KnowledgeModuleError("paid/restricted modules require a verified entitlement service; not enabled")
    normalized = {
        "schema_version": 1,
        "id": module_id,
        "title": _required_string(raw, "title", 160),
        "version": version,
        "publisher": _required_string(raw, "publisher", 160),
        "license": _required_string(raw, "license", 100),
        "subject": _required_string(raw, "subject", 120),
        "distribution": distribution,
        "chapters": [],
    }
    if "category" in raw or "language_tag" in raw:
        category = raw.get("category", "knowledge")
        if not isinstance(category, str) or category not in {"knowledge", "language", "degree_track"}:
            raise KnowledgeModuleError("unsupported category")
        if category == "language":
            language_tag = _required_string(raw, "language_tag", 35)
            if not _LANGUAGE_TAG.fullmatch(language_tag):
                raise KnowledgeModuleError("language_tag must be a supported BCP-47 language tag")
            normalized["category"] = "language"
            normalized["language_tag"] = language_tag
        else:
            if "language_tag" in raw:
                raise KnowledgeModuleError("language_tag requires category=language")
            normalized["category"] = category
    chapters = raw.get("chapters")
    if not isinstance(chapters, list) or not 1 <= len(chapters) <= _MAX_CHAPTERS:
        raise KnowledgeModuleError(f"chapters must contain 1 to {_MAX_CHAPTERS} entries")
    seen = set()
    for chapter in chapters:
        if not isinstance(chapter, dict) or set(chapter) - {"id", "title", "content", "source"}:
            raise KnowledgeModuleError("invalid chapter fields")
        chapter_id = _required_string(chapter, "id", 64)
        if not _ID.fullmatch(chapter_id) or chapter_id in seen:
            raise KnowledgeModuleError("invalid or duplicate chapter id")
        seen.add(chapter_id)
        normalized["chapters"].append({
            "id": chapter_id,
            "title": _required_string(chapter, "title", 160),
            "content": _required_string(chapter, "content", 12000),
            "source": _required_string(chapter, "source", 320),
        })
    if normalized.get("category") == "degree_track":
        programme = raw.get("programme")
        if not isinstance(programme, dict) or set(programme) != {"title", "level", "duration_years", "units"}:
            raise KnowledgeModuleError("degree_track requires programme title, level, duration_years and units")
        title = _required_string(programme, "title", 180)
        level = programme["level"]
        if not isinstance(level, str) or level not in {"bachelor", "master", "doctoral"}:
            raise KnowledgeModuleError("unsupported programme reference level")
        years = programme["duration_years"]
        if isinstance(years, bool) or not isinstance(years, int) or not 1 <= years <= 8:
            raise KnowledgeModuleError("duration_years must be 1 to 8")
        units = programme["units"]
        if not isinstance(units, list) or not 1 <= len(units) <= 40:
            raise KnowledgeModuleError("programme must include 1 to 40 units")
        chapter_ids = {c["id"] for c in normalized["chapters"]}
        seen_units = set()
        checked_units = []
        for unit in units:
            if not isinstance(unit, dict) or set(unit) != {"code", "title", "year", "chapter_ids"}:
                raise KnowledgeModuleError("invalid programme unit")
            code = _required_string(unit, "code", 24)
            unit_title = _required_string(unit, "title", 160)
            year = unit["year"]
            refs = unit["chapter_ids"]
            if (code in seen_units or isinstance(year, bool) or not isinstance(year, int)
                    or not 1 <= year <= years or not isinstance(refs, list)
                    or not refs or len(refs) > 100 or not all(
                        isinstance(x, str) and x in chapter_ids for x in refs)):
                raise KnowledgeModuleError("duplicate unit, invalid year or unknown chapter reference")
            if len(set(refs)) != len(refs):
                raise KnowledgeModuleError("duplicate chapter reference")
            seen_units.add(code)
            checked_units.append({"code": code, "title": unit_title, "year": year,
                                  "chapter_ids": refs})
        normalized["programme"] = {"title": title, "level": level,
                                    "duration_years": years, "units": checked_units}
    elif "programme" in raw:
        raise KnowledgeModuleError("programme is allowed only for degree_track")
    raw_bytes = json.dumps(normalized, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8")
    if len(raw_bytes) > _MAX_BYTES:
        raise KnowledgeModuleError("module exceeds size limit")
    return normalized


class KnowledgeModuleStore:
    """Versioned, removable reference content stored alongside Genesis state.

    Never turns a pack into a tool, policy, system instruction, model weight,
    credential, or Aurora capability. Package license metadata is self-declared.
    """

    def __init__(self, store: Store):
        self.store = store
        with store.tx() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge_modules(
                    module_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    version TEXT NOT NULL,
                    publisher TEXT NOT NULL,
                    license TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'knowledge',
                    language_tag TEXT,
                    programme_json TEXT,
                    sha256 TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    installed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS knowledge_module_chapters(
                    module_id TEXT NOT NULL REFERENCES knowledge_modules(module_id)
                        ON DELETE CASCADE,
                    chapter_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    PRIMARY KEY(module_id, chapter_id)
                );
                CREATE INDEX IF NOT EXISTS idx_module_chapter_parent
                    ON knowledge_module_chapters(module_id);
            """)
            # Compatible with databases created before language-category metadata.
            columns = {r[1] for r in db.execute("PRAGMA table_info(knowledge_modules)")}
            if "category" not in columns:
                db.execute("ALTER TABLE knowledge_modules ADD COLUMN category TEXT NOT NULL DEFAULT 'knowledge'")
            if "language_tag" not in columns:
                db.execute("ALTER TABLE knowledge_modules ADD COLUMN language_tag TEXT")
            if "programme_json" not in columns:
                db.execute("ALTER TABLE knowledge_modules ADD COLUMN programme_json TEXT")

    def list(self) -> list[dict[str, Any]]:
        with self.store._lock:
            rows = self.store.db.execute(
                """SELECT m.*, (SELECT COUNT(*) FROM knowledge_module_chapters c
                    WHERE c.module_id=m.module_id) AS chapters
                    FROM knowledge_modules m ORDER BY m.module_id"""
            ).fetchall()
        return [{k: v for k, v in dict(r).items() if k != "programme_json"} | {"enabled": bool(r["enabled"]), "distribution": "open",
                           "is_free": True} |
                ({"programme": json.loads(r["programme_json"])} if r["programme_json"] else {})
                for r in rows]

    def install(self, package: dict[str, Any], *, replace: bool = False) -> dict[str, Any]:
        payload = _validate(package)
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True,
            ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        module_id = payload["id"]
        with self.store.tx() as db:
            existing = db.execute(
                "SELECT sha256,enabled FROM knowledge_modules WHERE module_id=?", (module_id,)
            ).fetchone()
            if existing and existing["sha256"] == digest:
                return {"id": module_id, "version": payload["version"], "status": "already_installed",
                        "sha256": digest}
            if existing and not replace:
                raise KnowledgeModuleError("module already exists; explicit replace=True required")
            enabled = int(existing["enabled"]) if existing else 1
            # Replace metadata and chapters in one transaction; disabled stays disabled.
            db.execute("""INSERT INTO knowledge_modules
                (module_id,title,version,publisher,license,subject,category,language_tag,programme_json,sha256,enabled,installed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(module_id) DO UPDATE SET
                title=excluded.title,version=excluded.version,publisher=excluded.publisher,
                license=excluded.license,subject=excluded.subject,category=excluded.category,
                language_tag=excluded.language_tag,programme_json=excluded.programme_json,
                sha256=excluded.sha256,
                enabled=excluded.enabled,installed_at=excluded.installed_at""",
                (module_id,payload["title"],payload["version"],payload["publisher"],
                 payload["license"],payload["subject"],payload.get("category","knowledge"),
                 payload.get("language_tag"),
                 json.dumps(payload.get("programme")) if payload.get("programme") else None,
                 digest,enabled,
                 datetime.now(timezone.utc).isoformat()))
            db.execute("DELETE FROM knowledge_module_chapters WHERE module_id=?", (module_id,))
            db.executemany("""INSERT INTO knowledge_module_chapters
                (module_id,chapter_id,title,content,source) VALUES (?,?,?,?,?)""",
                [(module_id,c["id"],c["title"],c["content"],c["source"])
                 for c in payload["chapters"]])
        return {"id": module_id, "version": payload["version"],
                "status": "replaced" if existing else "installed", "sha256": digest}

    def set_enabled(self, module_id: str, enabled: bool) -> dict[str, Any]:
        if module_id == "genesis-core":
            raise KnowledgeModuleError("Genesis Core cannot be managed as a knowledge module")
        with self.store.tx() as db:
            row = db.execute("UPDATE knowledge_modules SET enabled=? WHERE module_id=?",
                             (int(enabled), module_id))
            if row.rowcount == 0:
                raise KnowledgeModuleError("unknown module")
        return {"id": module_id, "enabled": enabled}

    def uninstall(self, module_id: str) -> dict[str, Any]:
        if module_id == "genesis-core":
            raise KnowledgeModuleError("Genesis Core cannot be uninstalled")
        with self.store.tx() as db:
            row = db.execute("DELETE FROM knowledge_modules WHERE module_id=?", (module_id,))
            if row.rowcount == 0:
                raise KnowledgeModuleError("unknown module")
        return {"id": module_id, "status": "uninstalled"}

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not 1 <= len(query) <= 5000:
            raise KnowledgeModuleError("query must have 1 to 5000 characters")
        if not 1 <= limit <= 20:
            raise KnowledgeModuleError("limit must be between 1 and 20")
        terms = _terms(query)
        if not terms:
            return []
        with self.store._lock:
            rows = self.store.db.execute("""
                SELECT c.module_id,c.chapter_id,c.title,c.content,c.source,
                       m.title AS module_title,m.version,m.publisher,m.license,m.subject,
                       m.category,m.language_tag
                FROM knowledge_module_chapters c
                JOIN knowledge_modules m ON m.module_id=c.module_id
                WHERE m.enabled=1 ORDER BY c.module_id,c.chapter_id
            """).fetchall()
        hits = []
        for row in rows:
            title_terms = _terms(row["title"] + " " + row["subject"])
            body_terms = _terms(row["content"])
            common = terms & (title_terms | body_terms)
            min_matches = min(2, len(terms))
            if len(common) < min_matches:
                continue
            score = round(4 * len(common & title_terms) + len(common & body_terms)
                          + 2 * len(common) / len(terms), 3)
            hits.append({
                "module_id": row["module_id"], "module_title": row["module_title"],
                "version": row["version"], "chapter_id": row["chapter_id"],
                "title": row["title"], "excerpt": row["content"][:1800],
                "source": row["source"], "publisher": row["publisher"],
                "license": row["license"], "category": row["category"],
                "language_tag": row["language_tag"], "distribution": "open",
                "is_free": True, "score": score,
                "trust": "unverified_reference_data"
            })
        hits.sort(key=lambda h: (-h["score"], h["module_id"], h["chapter_id"]))
        return hits[:limit]
