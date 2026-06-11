"""进化引擎 - 指纹存储（SQLite）"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from .fingerprint import Fingerprint, FingerprintStatus


class FingerprintStore:
    """指纹库 —— 本地 SQLite 持久化 + 基因池同步"""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            # 默认存储在用户目录
            home = Path.home() / ".qvc"
            home.mkdir(exist_ok=True)
            db_path = home / "fingerprints.db"
        self.db_path = db_path
        self._init_db()
        self._load_seeds()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fingerprints (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                description TEXT NOT NULL,
                abstract_signature TEXT NOT NULL,
                severity TEXT DEFAULT 'SEVERE',
                confidence REAL DEFAULT 0.5,
                occurrence_count INTEGER DEFAULT 1,
                status TEXT DEFAULT 'candidate',
                source_bugs TEXT DEFAULT '[]',
                contributor TEXT DEFAULT 'anonymous',
                fix_template TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                promoted_at TEXT,
                verifier TEXT DEFAULT '',
                source TEXT DEFAULT 'local'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bug_title TEXT NOT NULL,
                bug_description TEXT,
                code_snippet TEXT,
                gap_category TEXT NOT NULL,
                file_path TEXT,
                line_number INTEGER,
                severity TEXT,
                discovered_at TEXT NOT NULL,
                abstracted INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evolution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event TEXT NOT NULL,
                details TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _load_seeds(self):
        """V3.0: Load bundled seed fingerprints from 4 categorized files"""
        conn = __import__("sqlite3").connect(str(self.db_path))
        try:
            count = conn.execute("SELECT COUNT(*) FROM fingerprints WHERE source = 'seed'").fetchone()[0]
            if count > 0:
                return  # Already loaded
        finally:
            conn.close()

        seeds_dir = Path(__file__).parent / "seeds"
        seed_files = ["python_seeds.json", "cwe_seeds.json", "js_seeds.json", "react_seeds.json", "go_seeds.json", "seed_fingerprints.json"]

        all_seeds = []
        for filename in seed_files:
            seed_file = seeds_dir / filename
            if seed_file.exists():
                try:
                    with open(seed_file, "r", encoding="utf-8-sig") as f:
                        seeds = json.load(f)
                    all_seeds.extend(seeds)
                except Exception:
                    pass

        # Fallback to legacy single file
        if not all_seeds:
            legacy = seeds_dir / "seed_fingerprints.json"
            if legacy.exists():
                try:
                    with open(legacy, "r", encoding="utf-8-sig") as f:
                        all_seeds = json.load(f)
                except Exception:
                    pass

        if not all_seeds:
            return

        import_fps = []
        for s in all_seeds:
            # Normalize V7 fields
            if "ai_blindspot" not in s:
                s["ai_blindspot"] = "boundary_condition"
            if "verified_projects" not in s:
                s["verified_projects"] = []
            import_fps.append({
                "fingerprint_id": s["fingerprint_id"],
                "category": s["category"],
                "pattern_name": s["pattern_name"],
                "description": s["description"],
                "abstract_signature": s.get("abstract_signature", {}),
                "severity": s.get("severity", "SEVERE"),
                "confidence": s.get("confidence", 0.8),
                "occurrence_count": 1,
                "status": "active",
                "fix_template": s.get("fix_template", ""),
                "created_at": "2026-06-11T00:00:00",
                "source": "seed",
            })

        from .fingerprint import Fingerprint
        for fp_data in import_fps:
            fp = Fingerprint.from_dict(fp_data)
            self.add_fingerprint(fp, source="seed")

        self.log_event("seeds_loaded", f"V3.0: Loaded {len(import_fps)} seed fingerprints")
    # ── 指纹 CRUD ──

    def add_fingerprint(self, fp: Fingerprint, source: str = "local"):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT OR REPLACE INTO fingerprints
                (id, category, pattern_name, description, abstract_signature,
                 severity, confidence, occurrence_count, status, source_bugs,
                 contributor, fix_template, created_at, promoted_at, verifier, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fp.id, fp.category, fp.pattern_name, fp.description,
                json.dumps(fp.abstract_signature, ensure_ascii=False),
                fp.severity, fp.confidence, fp.occurrence_count,
                fp.status.value, json.dumps(fp.source_bugs),
                fp.contributor, fp.fix_template,
                fp.created_at.isoformat(),
                fp.promoted_at.isoformat() if fp.promoted_at else None,
                fp.verifier, source,
            ))
            conn.commit()
        finally:
            conn.close()

    def get_fingerprint(self, fp_id: str) -> Fingerprint | None:
        conn = sqlite3.connect(str(self.db_path))
        try:
            row = conn.execute(
                "SELECT * FROM fingerprints WHERE id = ?", (fp_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_fingerprint(row)
        finally:
            conn.close()

    def get_active_fingerprints(self, category: str | None = None) -> list[Fingerprint]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            if category:
                rows = conn.execute(
                    "SELECT * FROM fingerprints WHERE status = 'active' AND category = ?",
                    (category,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM fingerprints WHERE status = 'active'"
                ).fetchall()
            return [self._row_to_fingerprint(r) for r in rows]
        finally:
            conn.close()

    def get_candidates(self, min_occurrences: int = 2) -> list[Fingerprint]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            rows = conn.execute(
                "SELECT * FROM fingerprints WHERE status = 'candidate' AND occurrence_count >= ?",
                (min_occurrences,)
            ).fetchall()
            return [self._row_to_fingerprint(r) for r in rows]
        finally:
            conn.close()

    def get_pending_review(self) -> list[Fingerprint]:
        return self.get_candidates(min_occurrences=3)

    def promote(self, fp_id: str, verifier: str = "user") -> bool:
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                UPDATE fingerprints
                SET status = 'active', promoted_at = ?, verifier = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), verifier, fp_id))
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def reject(self, fp_id: str, verifier: str = "user") -> bool:
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                UPDATE fingerprints SET status = 'rejected', verifier = ?
                WHERE id = ?
            """, (verifier, fp_id))
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def increment_occurrence(self, fp_id: str) -> bool:
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "UPDATE fingerprints SET occurrence_count = occurrence_count + 1 WHERE id = ?",
                (fp_id,)
            )
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def count_by_status(self) -> dict:
        conn = sqlite3.connect(str(self.db_path))
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) FROM fingerprints GROUP BY status"
            ).fetchall()
            return {row[0]: row[1] for row in rows}
        finally:
            conn.close()

    def count_by_source(self) -> dict:
        conn = sqlite3.connect(str(self.db_path))
        try:
            rows = conn.execute(
                "SELECT source, COUNT(*) FROM fingerprints GROUP BY source"
            ).fetchall()
            return {row[0]: row[1] for row in rows}
        finally:
            conn.close()

    # ── 知识缺口 CRUD ──

    def add_gap(self, bug_title: str, bug_description: str, code_snippet: str,
                gap_category: str, file_path: str, line_number: int, severity: str):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT INTO knowledge_gaps
                (bug_title, bug_description, code_snippet, gap_category,
                 file_path, line_number, severity, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (bug_title, bug_description, code_snippet[:500],
                  gap_category, file_path, line_number, severity,
                  datetime.now().isoformat()))
            conn.commit()
        finally:
            conn.close()

    def get_gaps_by_category(self, min_count: int = 2) -> list[dict]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            rows = conn.execute("""
                SELECT gap_category, COUNT(*) as cnt, GROUP_CONCAT(bug_title, '|||') as titles,
                       GROUP_CONCAT(code_snippet, '|||') as snippets
                FROM knowledge_gaps
                WHERE abstracted = 0
                GROUP BY gap_category
                HAVING cnt >= ?
                ORDER BY cnt DESC
            """, (min_count,)).fetchall()

            return [
                {
                    "category": r[0],
                    "count": r[1],
                    "titles": r[2].split("|||") if r[2] else [],
                    "snippets": r[3].split("|||") if r[3] else [],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def mark_gaps_abstracted(self, category: str):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "UPDATE knowledge_gaps SET abstracted = 1 WHERE gap_category = ?",
                (category,)
            )
            conn.commit()
        finally:
            conn.close()

    # ── 进化日志 ──

    def log_event(self, event: str, details: str = ""):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "INSERT INTO evolution_log (timestamp, event, details) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), event, details)
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent_events(self, limit: int = 20) -> list[dict]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            rows = conn.execute(
                "SELECT * FROM evolution_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [
                {"timestamp": r[1], "event": r[2], "details": r[3]}
                for r in rows
            ]
        finally:
            conn.close()

    # ── 基因池同步 ──

    def import_from_pool(self, fingerprints: list[Fingerprint]):
        for fp in fingerprints:
            self.add_fingerprint(fp, source="pool")

    def export_for_pool(self) -> list[dict]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            rows = conn.execute(
                "SELECT * FROM fingerprints WHERE status = 'active' AND source = 'local'"
            ).fetchall()
            return [self._row_to_fingerprint(r).to_dict() for r in rows]
        finally:
            conn.close()

    # ── 统计 ──

    def get_stats(self) -> dict:
        by_status = self.count_by_status()
        by_source = self.count_by_source()
        return {
            "total": sum(by_status.values()),
            "active": by_status.get("active", 0),
            "candidates": by_status.get("candidate", 0),
            "verified": by_status.get("verified", 0),
            "rejected": by_status.get("rejected", 0),
            "local": by_source.get("local", 0),
            "pool": by_source.get("pool", 0),
            "seed": by_source.get("seed", 0),
        }

    # ── 工具方法 ──

    def _row_to_fingerprint(self, row) -> Fingerprint:
        cols = [c[0] for c in row.keys()] if hasattr(row, 'keys') else [
            "id", "category", "pattern_name", "description", "abstract_signature",
            "severity", "confidence", "occurrence_count", "status", "source_bugs",
            "contributor", "fix_template", "created_at", "promoted_at", "verifier", "source"
        ]
        d = dict(zip(cols, row))
        return Fingerprint(
            id=d["id"],
            category=d["category"],
            pattern_name=d["pattern_name"],
            description=d["description"],
            abstract_signature=json.loads(d["abstract_signature"]) if isinstance(d["abstract_signature"], str) else d["abstract_signature"],
            severity=d.get("severity", "SEVERE"),
            confidence=d.get("confidence", 0.5),
            occurrence_count=d.get("occurrence_count", 1),
            status=FingerprintStatus(d.get("status", "candidate")),
            source_bugs=json.loads(d["source_bugs"]) if isinstance(d.get("source_bugs", "[]"), str) else d.get("source_bugs", []),
            contributor=d.get("contributor", "anonymous"),
            fix_template=d.get("fix_template", ""),
            created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.now(),
            promoted_at=datetime.fromisoformat(d["promoted_at"]) if d.get("promoted_at") else None,
            verifier=d.get("verifier", ""),
        )
