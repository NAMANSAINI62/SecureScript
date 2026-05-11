"""
Database Module for Super AI Transcript - SQLite Version
========================================================
This module handles all database operations using SQLite.
SQLite stores everything in a single local file.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime

# Database file location - in the same folder as this script
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "super_ai_transcript.db")


def get_connection():
    """
    Connect to the SQLite database.
    This creates the database file if it doesn't exist.
    """
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        # Access columns by name (instead of index)
        connection.row_factory = sqlite3.Row
        return connection
    except Exception as exc:
        print(f"Database connection error: {exc}")
        raise


def init_db():
    """
    Initialize the database by creating tables if they don't exist.
    This is called once when the app starts.
    """
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        # Create recordings table (stores audio files and their transcripts)
        create_recordings_table = """
        CREATE TABLE IF NOT EXISTS recordings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            audio_data BLOB,
            audio_mime_type TEXT DEFAULT 'audio/webm',
            original_transcript TEXT,
            cleaned_transcript TEXT,
            summary TEXT,
            key_points TEXT,
            duration_seconds REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_recordings_table)

        # Create Q&A history table (stores questions and answers about recordings)
        create_qa_table = """
        CREATE TABLE IF NOT EXISTS qa_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recording_id INTEGER,
            question TEXT NOT NULL,
            answer TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
        )
        """
        cursor.execute(create_qa_table)

        # Lightweight migration: add duration_seconds if missing
        cursor.execute("PRAGMA table_info(recordings)")
        cols = [row[1] for row in cursor.fetchall()]
        if "duration_seconds" not in cols:
            cursor.execute("ALTER TABLE recordings ADD COLUMN duration_seconds REAL")

        connection.commit()
        print(f"Database initialized at {DATABASE_PATH}")

    except Exception as exc:
        print(f"Error initializing database: {exc}")
        raise
    finally:
        if connection:
            connection.close()


def save_recording(
    filename,
    audio_data,
    audio_mime_type,
    original_transcript,
    cleaned_transcript=None,
    duration_seconds=None,
):
    """
    Save a new recording to the database.

    Args:
        filename: Name of the audio file
        audio_data: The actual audio bytes
        audio_mime_type: Type of audio (e.g., 'audio/webm')
        original_transcript: The transcribed text
        cleaned_transcript: Optional cleaned version of transcript

    Returns:
        The ID of the newly saved recording
    """
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
        INSERT INTO recordings 
        (filename, audio_data, audio_mime_type, original_transcript, cleaned_transcript, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
        """

        cursor.execute(
            sql,
            (
                filename,
                audio_data,
                audio_mime_type,
                original_transcript,
                cleaned_transcript,
                duration_seconds,
            ),
        )

        connection.commit()
        print(f"Recording saved with ID: {cursor.lastrowid}")
        return cursor.lastrowid

    except Exception as exc:
        print(f"Error saving recording: {exc}")
        raise
    finally:
        if connection:
            connection.close()


def update_recording(recording_id, **updates):
    """
    Update an existing recording with new information.

    Args:
        recording_id: The ID of the recording to update
        **updates: Key-value pairs to update (e.g., cleaned_transcript="...", summary="...")
    """
    if not updates:
        return

    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        # Add updated timestamp
        updates['updated_at'] = datetime.now()

        # Build the UPDATE query dynamically
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.append(recording_id)

        sql = f"UPDATE recordings SET {set_clause} WHERE id = ?"
        cursor.execute(sql, values)
        connection.commit()
        print(f"Recording {recording_id} updated")

    except Exception as exc:
        print(f"Error updating recording: {exc}")
        raise
    finally:
        if connection:
            connection.close()


def get_all_recordings(limit=50):
    """
    Get all recordings from the database (most recent first).

    Args:
        limit: Maximum number of recordings to return

    Returns:
        List of recording dictionaries
    """
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
        SELECT id, filename, audio_mime_type, original_transcript, 
               cleaned_transcript, summary, key_points, created_at, duration_seconds
        FROM recordings
        ORDER BY created_at DESC
        LIMIT ?
        """
        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except Exception as exc:
        print(f"Error fetching recordings: {exc}")
        return []
    finally:
        if connection:
            connection.close()


def get_recording_by_id(recording_id, include_audio=False):
    """
    Get a specific recording by ID.

    Args:
        recording_id: The ID of the recording
        include_audio: Whether to include the audio_data (large!) in the result

    Returns:
        Recording dictionary or None if not found
    """
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        if include_audio:
            sql = "SELECT * FROM recordings WHERE id = ?"
        else:
            sql = """
            SELECT id, filename, audio_mime_type, original_transcript, 
                   cleaned_transcript, summary, key_points, created_at, duration_seconds
            FROM recordings WHERE id = ?
            """

        cursor.execute(sql, (recording_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    except Exception as exc:
        print(f"Error fetching recording {recording_id}: {exc}")
        return None
    finally:
        if connection:
            connection.close()


def get_audio_data(recording_id):
    """
    Get the audio file data for a recording.

    Args:
        recording_id: The ID of the recording

    Returns:
        Tuple of (audio_data, mime_type) or (None, None) if not found
    """
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = "SELECT audio_data, audio_mime_type FROM recordings WHERE id = ?"
        cursor.execute(sql, (recording_id,))
        result = cursor.fetchone()

        if result:
            return result[0], result[1]
        return None, None

    except Exception as exc:
        print(f"Error fetching audio: {exc}")
        return None, None
    finally:
        if connection:
            connection.close()


def delete_recording(recording_id):
    """
    Delete a recording and all its associated data.

    Args:
        recording_id: The ID of the recording to delete

    Returns:
        True if deletion was successful, False otherwise
    """
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = "DELETE FROM recordings WHERE id = ?"
        cursor.execute(sql, (recording_id,))
        connection.commit()

        if cursor.rowcount > 0:
            print(f"Recording {recording_id} deleted")
            return True
        return False

    except Exception as exc:
        print(f"Error deleting recording: {exc}")
        return False
    finally:
        if connection:
            connection.close()


def save_qa(recording_id, question, answer):
    """
    Save a question and answer about a recording.

    Args:
        recording_id: The ID of the recording
        question: The user's question
        answer: The AI's answer

    Returns:
        The ID of the newly saved Q&A entry
    """
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
        INSERT INTO qa_history (recording_id, question, answer)
        VALUES (?, ?, ?)
        """
        cursor.execute(sql, (recording_id, question, answer))
        connection.commit()

        print(f"Q&A saved for recording {recording_id}")
        return cursor.lastrowid

    except Exception as exc:
        print(f"Error saving Q&A: {exc}")
        raise
    finally:
        if connection:
            connection.close()


def get_qa_history(recording_id):
    """
    Get all questions and answers for a specific recording.

    Args:
        recording_id: The ID of the recording

    Returns:
        List of Q&A dictionaries
    """
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
        SELECT id, question, answer, created_at
        FROM qa_history
        WHERE recording_id = ?
        ORDER BY created_at DESC
        """
        cursor.execute(sql, (recording_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except Exception as exc:
        print(f"Error fetching Q&A history: {exc}")
        return []
    finally:
        if connection:
            connection.close()
