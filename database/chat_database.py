# database/chat_database.py

from pathlib import Path
import sqlite3
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "data" / "database"
DB_PATH = DB_DIR / "teku_assistant.db"


class ChatDatabase:

    def __init__(self):
        DB_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.initialize_database()

    def connect(self):
        connection = sqlite3.connect(DB_PATH)

        connection.row_factory = sqlite3.Row

        return connection

    def initialize_database(self):
        with self.connect() as conn:

            conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(chat_id)
                        REFERENCES chats(id)
                        ON DELETE CASCADE
                )
            """)

            conn.commit()

    def create_chat(self, title="New Chat"):
        now = datetime.now().isoformat()

        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chats
                (title, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (title, now, now),
            )

            conn.commit()

            return cursor.lastrowid

    def update_chat(self, chat_id, title=None):
        now = datetime.now().isoformat()

        with self.connect() as conn:

            if title is not None:
                conn.execute(
                    """
                    UPDATE chats
                    SET title=?, updated_at=?
                    WHERE id=?
                    """,
                    (title, now, chat_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE chats
                    SET updated_at=?
                    WHERE id=?
                    """,
                    (now, chat_id),
                )

            conn.commit()

    def add_message(self, chat_id, role, text):
        now = datetime.now().isoformat()

        with self.connect() as conn:

            conn.execute(
                """
                INSERT INTO messages
                (chat_id, role, text, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (chat_id, role, text, now),
            )

            conn.execute(
                """
                UPDATE chats
                SET updated_at=?
                WHERE id=?
                """,
                (now, chat_id),
            )

            conn.commit()

    def get_chats(self):
        with self.connect() as conn:

            rows = conn.execute(
                """
                SELECT *
                FROM chats
                ORDER BY updated_at DESC
                """
            ).fetchall()

            return [dict(row) for row in rows]

    def get_messages(self, chat_id):
        with self.connect() as conn:

            rows = conn.execute(
                """
                SELECT *
                FROM messages
                WHERE chat_id=?
                ORDER BY id ASC
                """,
                (chat_id,),
            ).fetchall()

            return [dict(row) for row in rows]

    def delete_chat(self, chat_id):
        with self.connect() as conn:

            conn.execute(
                "DELETE FROM messages WHERE chat_id=?",
                (chat_id,),
            )

            conn.execute(
                "DELETE FROM chats WHERE id=?",
                (chat_id,),
            )

            conn.commit()

    def delete_all_chats(self):
        with self.connect() as conn:

            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM chats")

            conn.commit()

    def chat_exists(self, chat_id):
        with self.connect() as conn:

            row = conn.execute(
                """
                SELECT id
                FROM chats
                WHERE id=?
                """,
                (chat_id,),
            ).fetchone()

            return row is not None