"""
database.py
Handles all SQLite persistence for LearnInsight AI.
"""

import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "learninsight.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'txt')),
            upload_date TEXT NOT NULL DEFAULT (datetime('now')),
            extracted_text TEXT NOT NULL,
            summary TEXT NOT NULL,
            explanation TEXT NOT NULL,
            quiz TEXT NOT NULL,
            flashcards TEXT NOT NULL,
            notes TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_document(filename, file_type, extracted_text, summary, explanation, quiz, flashcards, notes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (filename, file_type, extracted_text, summary, explanation, quiz, flashcards, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        filename, file_type, extracted_text, summary, explanation,
        json.dumps(quiz), json.dumps(flashcards), notes
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_all_documents():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, upload_date FROM documents ORDER BY upload_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], "filename": row["filename"], "upload_date": row["upload_date"]} for row in rows]


def get_document_by_id(doc_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row["id"],
        "filename": row["filename"],
        "file_type": row["file_type"],
        "upload_date": row["upload_date"],
        "summary": row["summary"],
        "explanation": row["explanation"],
        "quiz": json.loads(row["quiz"]),
        "flashcards": json.loads(row["flashcards"]),
        "notes": row["notes"]
    }