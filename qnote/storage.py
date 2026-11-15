"""
Lightweight Single-File SQLite Storage for Qnote
All pages are saved in a single database file (~/.config/qnote/qnote.db or %APPDATA%/qnote/qnote.db).
No scattered single files, no heavy external database services.
"""
import sqlite3
import json
import time
from typing import Optional, Dict, Any, List
from .config import get_db_path

class NoteStorage:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database tables with WAL mode for speed and reliability."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    text_content TEXT DEFAULT '',
                    strokes_data TEXT DEFAULT '[]',
                    theme_id INTEGER DEFAULT 0,
                    is_archived INTEGER DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at DESC);")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Fetch a persistent user preference."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        """Save a persistent user preference."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            conn.commit()

    def get_latest_active_note(self) -> Optional[Dict[str, Any]]:
        """Fetch the most recently created non-archived note."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notes 
                WHERE is_archived = 0 
                ORDER BY id DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def create_new_note(self, theme_id: int = 0) -> int:
        """Create a fresh new sheet of paper."""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notes (created_at, updated_at, text_content, strokes_data, theme_id, is_archived)
                VALUES (?, ?, '', '[]', ?, 0)
            """, (now, now, theme_id))
            conn.commit()
            return cursor.lastrowid

    def get_or_create_current_note(self, default_theme_id: int = 0) -> Dict[str, Any]:
        """Get the current paper or create a new one if none exists."""
        note = self.get_latest_active_note()
        if note is not None:
            return note
        new_id = self.create_new_note(theme_id=default_theme_id)
        return self.get_note_by_id(new_id)

    def get_note_by_id(self, note_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def save_note(self, note_id: int, text_content: str, strokes: list, theme_id: int):
        """Save text and drawing strokes to the current sheet."""
        now = time.time()
        strokes_json = json.dumps(strokes)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE notes 
                SET text_content = ?, strokes_data = ?, theme_id = ?, updated_at = ?
                WHERE id = ?
            """, (text_content, strokes_json, theme_id, now, note_id))
            conn.commit()

    def get_all_notes_summary(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent notes for quick navigation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, created_at, updated_at, 
                       SUBSTR(text_content, 1, 60) AS preview,
                       LENGTH(text_content) AS text_len,
                       LENGTH(strokes_data) AS strokes_len,
                       theme_id
                FROM notes
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_note_position(self, note_id: int) -> tuple:
        """
        Returns (1-based index, total_count) for the note ordered by id ASC.
        E.g. (3, 7) means page 3 out of 7 total notes.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM notes WHERE is_archived = 0")
            total = cursor.fetchone()["total"]
            
            cursor.execute("""
                SELECT COUNT(*) AS pos FROM notes 
                WHERE is_archived = 0 AND id <= ?
            """, (note_id,))
            pos = cursor.fetchone()["pos"]
            return max(1, pos), max(1, total)

    def get_adjacent_note_id(self, current_id: int, direction: str = "prev") -> Optional[int]:
        """
        direction:
          'prev' (older note): id < current_id ORDER BY id DESC LIMIT 1
          'next' (newer note): id > current_id ORDER BY id ASC LIMIT 1
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if direction == "prev":
                cursor.execute("""
                    SELECT id FROM notes 
                    WHERE is_archived = 0 AND id < ? 
                    ORDER BY id DESC LIMIT 1
                """, (current_id,))
            else:
                cursor.execute("""
                    SELECT id FROM notes 
                    WHERE is_archived = 0 AND id > ? 
                    ORDER BY id ASC LIMIT 1
                """, (current_id,))
            row = cursor.fetchone()
            return row["id"] if row else None

    def delete_note(self, note_id: int) -> bool:
        """Delete an empty or unneeded sheet."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_total_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS cnt FROM notes")
            return cursor.fetchone()["cnt"]
