from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import settings


@contextmanager
def get_connection():
    if not settings.postgres_url:
        raise RuntimeError("POSTGRES_URL is not configured.")
    connection = psycopg.connect(settings.postgres_url, row_factory=dict_row)
    try:
        yield connection
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_log (
                    id SERIAL PRIMARY KEY,
                    question TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    pdf_name TEXT,
                    answer_length INTEGER
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id UUID PRIMARY KEY,
                    pdf_name TEXT NOT NULL,
                    chunks JSONB NOT NULL,
                    faiss_index BYTEA NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
        connection.commit()


def store_document(document_id: str, pdf_name: str, chunks: List[str], faiss_index: bytes) -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO documents (id, pdf_name, chunks, faiss_index)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET pdf_name = EXCLUDED.pdf_name,
                    chunks = EXCLUDED.chunks,
                    faiss_index = EXCLUDED.faiss_index;
                """,
                (document_id, pdf_name, Jsonb(chunks), faiss_index),
            )
        connection.commit()


def fetch_document(document_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, pdf_name, chunks, faiss_index, created_at
                FROM documents
                WHERE id = %s;
                """,
                (document_id,),
            )
            return cursor.fetchone()


def log_question(question: str, pdf_name: Optional[str], answer_length: int) -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO usage_log (question, pdf_name, answer_length)
                VALUES (%s, %s, %s);
                """,
                (question, pdf_name, answer_length),
            )
        connection.commit()


def fetch_insights() -> Dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total_questions FROM usage_log;")
            total_questions = cursor.fetchone()["total_questions"]

            cursor.execute(
                """
                SELECT question, COUNT(*)::INT AS count
                FROM usage_log
                GROUP BY question
                ORDER BY COUNT(*) DESC, question ASC
                LIMIT 10;
                """
            )
            most_asked_questions = cursor.fetchall()

            cursor.execute(
                """
                SELECT DATE(timestamp) AS day, COUNT(*)::INT AS count
                FROM usage_log
                GROUP BY DATE(timestamp)
                ORDER BY day ASC;
                """
            )
            questions_per_day = cursor.fetchall()

            cursor.execute(
                """
                SELECT pdf_name
                FROM usage_log
                WHERE pdf_name IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 1;
                """
            )
            latest_row = cursor.fetchone()

            return {
                "total_questions": total_questions,
                "most_asked_questions": most_asked_questions,
                "questions_per_day": questions_per_day,
                "latest_pdf_name": latest_row["pdf_name"] if latest_row else None,
            }
