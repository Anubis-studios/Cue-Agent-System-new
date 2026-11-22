import sqlite3
import os
import json

def get_connection(db_path=None):
    if db_path is None:
        db_path = os.getenv("DATABASE_PATH", "cue.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    if db_path is None:
        db_path = os.getenv("DATABASE_PATH", "cue.db")
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        agent_id TEXT NOT NULL, 
        user_message TEXT NOT NULL, 
        assistant_reply TEXT NOT NULL, 
        provider TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        job_type TEXT NOT NULL, 
        status TEXT DEFAULT 'pending', 
        payload TEXT, 
        result TEXT, 
        error TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_agent ON conversations(agent_id, created_at)")
    conn.commit()
    conn.close()

def save_conversation(agent_id, user_message, assistant_reply, provider, db_path=None):
    conn = get_connection(db_path)
    conn.execute("INSERT INTO conversations (agent_id, user_message, assistant_reply, provider) VALUES (?, ?, ?, ?)", 
                 (agent_id, user_message, assistant_reply, provider))
    conn.commit()
    conn.close()

def get_pending_jobs(job_type=None, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if job_type:
        cursor.execute("SELECT id, job_type, payload FROM jobs WHERE status='pending' AND job_type=? ORDER BY created_at ASC", (job_type,))
    else:
        cursor.execute("SELECT id, job_type, payload FROM jobs WHERE status='pending' ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    jobs = []
    for row in rows:
        job = dict(row)
        job['payload'] = json.loads(job['payload'])
        jobs.append(job)
    return jobs

def update_job_status(job_id, status, result=None, error=None, db_path=None):
    conn = get_connection(db_path)
    conn.execute("UPDATE jobs SET status=?, result=?, error=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", 
                 (status, json.dumps(result) if result else None, error, job_id))
    conn.commit()
    conn.close()
