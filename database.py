"""
Database Module for Super AI Transcript - MySQL Version
========================================================
This module handles all database operations using MySQL.
MySQL is a robust database server that can handle multiple users
and larger applications.
"""

import mysql.connector
from mysql.connector import Error, pooling
import os
from datetime import datetime
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure UTF-8 console output on Windows (avoid UnicodeEncodeError for ✅ logs)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# MySQL connection configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'super_ai_transcript'),
    'raise_on_warnings': False
}

# Create connection pool for better performance
connection_pool = None


def init_pool():
    """Initialize the connection pool."""
    global connection_pool
    try:
        connection_pool = pooling.MySQLConnectionPool(
            pool_name="super_ai_pool",
            pool_size=5,
            pool_reset_session=True,
            **DB_CONFIG
        )
        print(f"✅ MySQL connection pool created")
    except Error as e:
        print(f"❌ Error creating connection pool: {e}")
        raise e


def get_connection():
    """
    Get a connection from the pool.
    Creates pool if it doesn't exist.
    """
    global connection_pool
    try:
        if connection_pool is None:
            init_pool()
        return connection_pool.get_connection()
    except Error as e:
        print(f"❌ Database connection error: {e}")
        raise e


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
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            audio_data LONGBLOB,
            audio_mime_type VARCHAR(50) DEFAULT 'audio/webm',
            original_transcript LONGTEXT,
            cleaned_transcript LONGTEXT,
            summary LONGTEXT,
            key_points LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_recordings_table)

        # Add duration_seconds column if missing (lightweight migration)
        try:
            cursor.execute("SHOW COLUMNS FROM recordings LIKE 'duration_seconds'")
            col = cursor.fetchone()
            if not col:
                cursor.execute("ALTER TABLE recordings ADD COLUMN duration_seconds FLOAT NULL")
                print("✅ Added recordings.duration_seconds column")
        except Exception as e:
            print(f"⚠️ Could not ensure duration_seconds column: {e}")

        # Create Q&A history table (stores questions and answers about recordings)
        create_qa_table = """
        CREATE TABLE IF NOT EXISTS qa_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            recording_id INT,
            question TEXT NOT NULL,
            answer LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
        )
        """
        cursor.execute(create_qa_table)

        connection.commit()
        print(f"✅ MySQL database initialized: {DB_CONFIG['database']}")

    except Error as e:
        print(f"❌ Error initializing database: {e}")
        raise e
    finally:
        if connection:
            connection.close()


def save_recording(filename, audio_data, audio_mime_type, original_transcript,
                   cleaned_transcript=None, duration_seconds=None):
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
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(sql, (filename, audio_data, audio_mime_type,
                            original_transcript, cleaned_transcript, duration_seconds))

        connection.commit()
        recording_id = cursor.lastrowid
        print(f"✅ Recording saved with ID: {recording_id}")
        return recording_id

    except Error as e:
        print(f"❌ Error saving recording: {e}")
        raise e
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
        set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
        values = list(updates.values())
        values.append(recording_id)

        sql = f"UPDATE recordings SET {set_clause} WHERE id = %s"
        cursor.execute(sql, values)
        connection.commit()
        print(f"✅ Recording {recording_id} updated")

    except Error as e:
        print(f"❌ Error updating recording: {e}")
        raise e
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
        cursor = connection.cursor(dictionary=True)

        sql = """
        SELECT id, filename, audio_mime_type, original_transcript, 
               cleaned_transcript, summary, key_points, created_at, duration_seconds
        FROM recordings
        ORDER BY created_at DESC
        LIMIT %s
        """
        cursor.execute(sql, (limit,))
        recordings = cursor.fetchall()
        return recordings

    except Error as e:
        print(f"❌ Error fetching recordings: {e}")
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
        cursor = connection.cursor(dictionary=True)

        if include_audio:
            sql = "SELECT * FROM recordings WHERE id = %s"
        else:
            sql = """
            SELECT id, filename, audio_mime_type, original_transcript, 
                   cleaned_transcript, summary, key_points, created_at, duration_seconds
            FROM recordings WHERE id = %s
            """

        cursor.execute(sql, (recording_id,))
        recording = cursor.fetchone()
        return recording

    except Error as e:
        print(f"❌ Error fetching recording {recording_id}: {e}")
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
        cursor = connection.cursor(dictionary=True)

        sql = "SELECT audio_data, audio_mime_type FROM recordings WHERE id = %s"
        cursor.execute(sql, (recording_id,))
        result = cursor.fetchone()

        if result:
            return result['audio_data'], result['audio_mime_type']
        return None, None

    except Error as e:
        print(f"❌ Error fetching audio: {e}")
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

        sql = "DELETE FROM recordings WHERE id = %s"
        cursor.execute(sql, (recording_id,))
        connection.commit()

        if cursor.rowcount > 0:
            print(f"✅ Recording {recording_id} deleted")
            return True
        return False

    except Error as e:
        print(f"❌ Error deleting recording: {e}")
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
        VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (recording_id, question, answer))
        connection.commit()

        qa_id = cursor.lastrowid
        print(f"✅ Q&A saved for recording {recording_id}")
        return qa_id

    except Error as e:
        print(f"❌ Error saving Q&A: {e}")
        raise e
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
        cursor = connection.cursor(dictionary=True)

        sql = """
        SELECT id, question, answer, created_at
        FROM qa_history
        WHERE recording_id = %s
        ORDER BY created_at DESC
        """
        cursor.execute(sql, (recording_id,))
        qa_list = cursor.fetchall()
        return qa_list

    except Error as e:
        print(f"❌ Error fetching Q&A history: {e}")
        return []
    finally:
        if connection:
            connection.close()
