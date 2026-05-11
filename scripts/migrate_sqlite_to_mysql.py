"""
Migrate recordings and qa_history from SQLite to MySQL.

Usage (from repo root):
    python scripts/migrate_sqlite_to_mysql.py

Notes:
- Reads SQLite DB file: super_ai_transcript.db
- Writes into MySQL using .env DB_* settings
- Preserves IDs and timestamps where possible
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

ROOT = Path(__file__).resolve().parents[1]
SQLITE_DB = ROOT / "super_ai_transcript.db"


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def get_mysql_conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "super_ai_transcript"),
    )


def sqlite_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols


def migrate_recordings(sqlite_conn: sqlite3.Connection, mysql_conn) -> int:
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()

    has_duration = sqlite_has_column(sqlite_conn, "recordings", "duration_seconds")

    cols = [
        "id",
        "filename",
        "audio_data",
        "audio_mime_type",
        "original_transcript",
        "cleaned_transcript",
        "summary",
        "key_points",
        "created_at",
        "updated_at",
    ]
    if has_duration:
        cols.append("duration_seconds")

    cur.execute(f"SELECT {', '.join(cols)} FROM recordings ORDER BY id ASC")
    rows = cur.fetchall()

    mysql_cur = mysql_conn.cursor()

    insert_sql = """
        INSERT INTO recordings (
            id, filename, audio_data, audio_mime_type, original_transcript,
            cleaned_transcript, summary, key_points, created_at, updated_at, duration_seconds
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            filename = VALUES(filename),
            audio_data = VALUES(audio_data),
            audio_mime_type = VALUES(audio_mime_type),
            original_transcript = VALUES(original_transcript),
            cleaned_transcript = VALUES(cleaned_transcript),
            summary = VALUES(summary),
            key_points = VALUES(key_points),
            created_at = VALUES(created_at),
            updated_at = VALUES(updated_at),
            duration_seconds = VALUES(duration_seconds)
    """

    migrated = 0
    for row in rows:
        duration_seconds = row["duration_seconds"] if has_duration else None
        values = (
            row["id"],
            row["filename"],
            row["audio_data"],
            row["audio_mime_type"],
            row["original_transcript"],
            row["cleaned_transcript"],
            row["summary"],
            row["key_points"],
            row["created_at"],
            row["updated_at"],
            duration_seconds,
        )
        mysql_cur.execute(insert_sql, values)
        migrated += 1

    mysql_conn.commit()
    return migrated


def migrate_qa_history(sqlite_conn: sqlite3.Connection, mysql_conn) -> int:
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()

    cur.execute(
        "SELECT id, recording_id, question, answer, created_at FROM qa_history ORDER BY id ASC"
    )
    rows = cur.fetchall()

    mysql_cur = mysql_conn.cursor()

    insert_sql = """
        INSERT INTO qa_history (id, recording_id, question, answer, created_at)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            recording_id = VALUES(recording_id),
            question = VALUES(question),
            answer = VALUES(answer),
            created_at = VALUES(created_at)
    """

    migrated = 0
    for row in rows:
        values = (
            row["id"],
            row["recording_id"],
            row["question"],
            row["answer"],
            row["created_at"],
        )
        mysql_cur.execute(insert_sql, values)
        migrated += 1

    mysql_conn.commit()
    return migrated


def main() -> None:
    if not SQLITE_DB.exists():
        raise FileNotFoundError(f"SQLite DB not found: {SQLITE_DB}")

    load_env()

    sqlite_conn = sqlite3.connect(str(SQLITE_DB))
    mysql_conn = get_mysql_conn()

    try:
        recordings_count = migrate_recordings(sqlite_conn, mysql_conn)
        qa_count = migrate_qa_history(sqlite_conn, mysql_conn)
    finally:
        sqlite_conn.close()
        mysql_conn.close()

    print(f"✅ Migrated recordings: {recordings_count}")
    print(f"✅ Migrated Q&A rows: {qa_count}")
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Error as exc:
        print(f"❌ MySQL error: {exc}")
    except Exception as exc:
        print(f"❌ Migration failed: {exc}")
