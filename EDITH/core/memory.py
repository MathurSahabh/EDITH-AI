import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class MemoryStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        self.conn.commit()

    # ------------------------------------------------------------------
    # Conversation logs
    # ------------------------------------------------------------------
    def log(self, role: str, content: str):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO interactions(ts, role, content) VALUES(?,?,?)",
            (datetime.utcnow().isoformat(timespec="seconds"), role, content),
        )
        self.conn.commit()

    def fetch_interactions(self, limit: int = 20) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT ts, role, content FROM interactions ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        rows = list(reversed(rows))
        return [{"ts": r["ts"], "role": r["role"], "content": r["content"]} for r in rows]

    # ------------------------------------------------------------------
    # Generic KV
    # ------------------------------------------------------------------
    def _set_kv(self, key: str, value: str):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO kv(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.conn.commit()

    def _get_kv(self, key: str, default=None):
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM kv WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default

    def delete_profile_key(self, key: str):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM kv WHERE key = ?", (key,))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Sticky note APIs
    # ------------------------------------------------------------------
    def set_note(self, note: str):
        self._set_kv("note", note)

    def get_note(self) -> Optional[str]:
        return self._get_kv("note", None)

    # ------------------------------------------------------------------
    # User/Profile APIs
    # ------------------------------------------------------------------
    def set_user_name(self, name: str):
        self._set_kv("user.name", name)

    def get_user_name(self) -> Optional[str]:
        return self._get_kv("user.name", None)

    def set_preference(self, key: str, value):
        # prefix all preferences with pref.
        self._set_kv(f"pref.{key}", str(value))

    def get_preference(self, key: str, default=None):
        v = self._get_kv(f"pref.{key}", None)
        if v is None:
            return default

        # typed conversions for common booleans
        low = v.lower()
        if low in {"true", "false"}:
            return low == "true"
        return v

    def get_all_profile(self) -> Dict[str, str]:
        cur = self.conn.cursor()
        cur.execute("SELECT key, value FROM kv WHERE key LIKE 'pref.%' OR key = 'user.name' ORDER BY key")
        rows = cur.fetchall()
        return {r["key"]: r["value"] for r in rows}

    # ------------------------------------------------------------------
    # housekeeping
    # ------------------------------------------------------------------
    def close(self):
        self.conn.close()