"""SQLite persistence layer for conversations and background jobs."""

import json
import os
import sqlite3
from contextlib import closing
from typing import Any, Optional

from backend.config import DATABASE_PATH


def _resolve_path(db_path: Optional[str]) -> str:
    return db_path or os.getenv("DATABASE_PATH", DATABASE_PATH)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve_path(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    with closing(get_connection(db_path)) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                assistant_reply TEXT NOT NULL,
                provider TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                payload TEXT,
                result TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_conv_agent
                ON conversations(agent_id, created_at);
            """
        )
        conn.commit()


def save_conversation(
    agent_id: str,
    user_message: str,
    assistant_reply: str,
    provider: str,
    db_path: Optional[str] = None,
) -> None:
    with closing(get_connection(db_path)) as conn:
        conn.execute(
            "INSERT INTO conversations "
            "(agent_id, user_message, assistant_reply, provider) "
            "VALUES (?, ?, ?, ?)",
            (agent_id, user_message, assistant_reply, provider),
        )
        conn.commit()


def get_pending_jobs(
    job_type: Optional[str] = None, db_path: Optional[str] = None
) -> list[dict[str, Any]]:
    query = "SELECT id, job_type, payload FROM jobs WHERE status='pending'"
    params: tuple = ()
    if job_type:
        query += " AND job_type=?"
        params = (job_type,)
    query += " ORDER BY created_at ASC"

    with closing(get_connection(db_path)) as conn:
        rows = conn.execute(query, params).fetchall()

    jobs = []
    for row in rows:
        job = dict(row)
        job["payload"] = json.loads(job["payload"]) if job["payload"] else {}
        jobs.append(job)
    return jobs


def enqueue_job(
    job_type: str, payload: dict, db_path: Optional[str] = None
) -> int:
    with closing(get_connection(db_path)) as conn:
        cursor = conn.execute(
            "INSERT INTO jobs (job_type, payload) VALUES (?, ?)",
            (job_type, json.dumps(payload)),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_job_status(
    job_id: int,
    status: str,
    result: Optional[Any] = None,
    error: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    with closing(get_connection(db_path)) as conn:
        conn.execute(
            "UPDATE jobs SET status=?, result=?, error=?, "
            "updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (
                status,
                json.dumps(result) if result is not None else None,
                error,
                job_id,
            ),
        )
        conn.commit()
