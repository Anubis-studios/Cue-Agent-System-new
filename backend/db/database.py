"""Database persistence layer: conversations, jobs and agent memories.

Backend selection (real database integrations):
  * ``DATABASE_URL`` set   -> PostgreSQL via SQLAlchemy 2.x + psycopg (v3)
      e.g. ``postgresql+psycopg://user:pass@host:5432/cue?sslmode=require``
      (Supabase / Neon / Render Postgres / RDS all work unchanged)
  * otherwise              -> SQLite at ``DATABASE_PATH`` (local dev / disk)

All public functions are plain sync helpers; FastAPI handlers call them via
``fastapi.concurrency.run_in_threadpool`` so the event loop is never blocked.
"""

import json
import logging
import os
from typing import Any, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    create_engine,
    func,
    or_,
    select,
    text as sa_text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import DATABASE_PATH

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(128), nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    assistant_reply = Column(Text, nullable=False)
    provider = Column(String(191))
    created_at = Column(String(32), server_default=sa_text("CURRENT_TIMESTAMP"))


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(64), nullable=False, index=True)
    status = Column(String(16), default="pending", index=True)
    payload = Column(Text)
    result = Column(Text)
    error = Column(Text)
    created_at = Column(String(32), server_default=sa_text("CURRENT_TIMESTAMP"))
    updated_at = Column(String(32), server_default=sa_text("CURRENT_TIMESTAMP"))


class Memory(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(128), nullable=False, index=True)
    kind = Column(String(32), default="fact")          # fact | preference | conversation
    content = Column(Text, nullable=False)
    tags = Column(Text)                                 # JSON array of strings
    created_at = Column(String(32), server_default=sa_text("CURRENT_TIMESTAMP"))


_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None
_backend_name = "sqlite"


def _database_url() -> str:
    global _backend_name
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        _backend_name = "postgres"
        if url.startswith("postgres://"):  # Heroku/Render-style scheme
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url
    _backend_name = "sqlite"
    return f"sqlite:///{DATABASE_PATH}"


def get_engine() -> Engine:
    global _engine, _SessionFactory
    if _engine is None:
        url = _database_url()
        kwargs: dict[str, Any] = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs.update(pool_size=5, max_overflow=10)
        _engine = create_engine(url, **kwargs)
        _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
        logger.info("Database engine initialised (%s)", _backend_name)
    return _engine


def db_backend() -> str:
    get_engine()
    return _backend_name


def init_db(db_path: Optional[str] = None) -> None:
    """Create tables if they do not exist. Safe to call repeatedly."""
    if db_path:  # test override: rebuild engine against an explicit sqlite file
        global _engine, _SessionFactory
        _engine = None
        os.environ.pop("DATABASE_URL", None)
        os.environ["DATABASE_PATH"] = db_path
    get_engine()
    assert _SessionFactory is not None
    Base.metadata.create_all(_engine)
    with _SessionFactory() as session:
        session.commit()


def _session() -> Session:
    get_engine()
    assert _SessionFactory is not None
    return _SessionFactory()


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

def save_conversation(
    agent_id: str,
    user_message: str,
    assistant_reply: str,
    provider: str,
    db_path: Optional[str] = None,
) -> None:
    with _session() as session:
        session.add(
            Conversation(
                agent_id=agent_id,
                user_message=user_message,
                assistant_reply=assistant_reply,
                provider=provider,
            )
        )
        session.commit()


def get_conversations(agent_id: str, limit: int = 50) -> list[dict[str, Any]]:
    stmt = (
        select(Conversation)
        .where(Conversation.agent_id == agent_id)
        .order_by(Conversation.id.desc())
        .limit(min(limit, 200))
    )
    with _session() as session:
        rows = session.execute(stmt).scalars().all()
    return [
        {
            "id": r.id,
            "user_message": r.user_message,
            "assistant_reply": r.assistant_reply,
            "provider": r.provider,
            "created_at": str(r.created_at),
        }
        for r in reversed(rows)
    ]


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

def enqueue_job(job_type: str, payload: dict, db_path: Optional[str] = None) -> int:
    with _session() as session:
        job = Job(job_type=job_type, payload=json.dumps(payload))
        session.add(job)
        session.commit()
        return int(job.id)


def get_pending_jobs(
    job_type: Optional[str] = None, db_path: Optional[str] = None
) -> list[dict[str, Any]]:
    stmt = select(Job).where(Job.status == "pending")
    if job_type:
        stmt = stmt.where(Job.job_type == job_type)
    stmt = stmt.order_by(Job.id.asc()).limit(50)
    with _session() as session:
        rows = session.execute(stmt).scalars().all()
    jobs = []
    for row in rows:
        jobs.append(
            {
                "id": row.id,
                "job_type": row.job_type,
                "payload": json.loads(row.payload) if row.payload else {},
            }
        )
    return jobs


def update_job_status(
    job_id: int,
    status: str,
    result: Optional[Any] = None,
    error: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    with _session() as session:
        job = session.get(Job, job_id)
        if job is None:
            return
        job.status = status
        job.result = json.dumps(result) if result is not None else None
        job.error = error
        session.execute(
            sa_text("UPDATE jobs SET updated_at = CURRENT_TIMESTAMP WHERE id = :jid")
            .bindparams(jid=job_id)
        ) if _backend_name == "postgres" else None
        session.commit()


def get_job(job_id: int) -> Optional[dict[str, Any]]:
    with _session() as session:
        job = session.get(Job, job_id)
        if job is None:
            return None
        return {
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "payload": json.loads(job.payload) if job.payload else {},
            "result": json.loads(job.result) if job.result else None,
            "error": job.error,
        }


# ---------------------------------------------------------------------------
# Memories (long-term agent memory)
# ---------------------------------------------------------------------------

def store_memory(
    agent_id: str,
    content: str,
    kind: str = "fact",
    tags: Optional[str] = None,
) -> int:
    with _session() as session:
        mem = Memory(agent_id=agent_id, kind=kind, content=content, tags=tags)
        session.add(mem)
        session.commit()
        return int(mem.id)


def recall_memories(agent_id: str, query: str = "", limit: int = 10) -> list[dict[str, Any]]:
    stmt = select(Memory).where(Memory.agent_id == agent_id)
    if query:
        pattern = f"%{query}%"
        words = [w for w in query.split() if len(w) > 3][:5]
        conditions = [Memory.content.ilike(pattern)]
        conditions += [Memory.tags.ilike(f"%{w}%") for w in words]
        stmt = stmt.where(or_(*conditions))
    stmt = stmt.order_by(Memory.id.desc()).limit(min(limit, 50))
    with _session() as session:
        rows = session.execute(stmt).scalars().all()
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "content": r.content,
            "tags": json.loads(r.tags) if r.tags else [],
            "created_at": str(r.created_at),
        }
        for r in rows
    ]


def get_recent_memories(agent_id: str, limit: int = 10) -> list[dict[str, Any]]:
    return recall_memories(agent_id, query="", limit=limit)


def delete_memory(memory_id: int) -> bool:
    with _session() as session:
        mem = session.get(Memory, memory_id)
        if mem is None:
            return False
        session.delete(mem)
        session.commit()
        return True


def stats() -> dict[str, int]:
    counts: dict[str, int] = {}
    with _session() as session:
        for model, key in ((Conversation, "conversations"), (Job, "jobs"), (Memory, "memories")):
            counts[key] = int(session.execute(select(func.count()).select_from(model)).scalar() or 0)
    return counts
