"""
Database module — SQLite storage for jobs, applications, and generated materials.
"""

import sqlite3
import json
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "data/jobs.db")


@contextmanager
def get_db():
    """Context manager for database connections."""
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialize database tables."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                description TEXT,
                url TEXT,
                source TEXT,
                job_type TEXT,
                salary_min REAL,
                salary_max REAL,
                salary_currency TEXT DEFAULT 'USD',
                posted_date TEXT,
                deadline TEXT,
                remote BOOLEAN DEFAULT 0,
                visa_sponsorship TEXT,
                match_score REAL DEFAULT 0,
                match_reasoning TEXT,
                status TEXT DEFAULT 'new',
                tags TEXT DEFAULT '[]',
                raw_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                status TEXT DEFAULT 'draft',
                cover_letter TEXT,
                resume_version TEXT,
                applied_at TEXT,
                follow_up_date TEXT,
                notes TEXT,
                response TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            );

            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                source TEXT,
                results_count INTEGER,
                searched_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(match_score DESC);
            CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
            CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
        """)


def upsert_job(job: dict) -> int:
    """Insert or update a job. Returns job id."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM jobs WHERE external_id = ?", (job.get("external_id"),)
        ).fetchone()

        if existing:
            conn.execute("""
                UPDATE jobs SET
                    title=?, company=?, location=?, description=?, url=?,
                    source=?, job_type=?, salary_min=?, salary_max=?,
                    posted_date=?, deadline=?, remote=?, visa_sponsorship=?,
                    raw_data=?, updated_at=?
                WHERE id=?
            """, (
                job.get("title"), job.get("company"), job.get("location"),
                job.get("description"), job.get("url"), job.get("source"),
                job.get("job_type"), job.get("salary_min"), job.get("salary_max"),
                job.get("posted_date"), job.get("deadline"), job.get("remote"),
                job.get("visa_sponsorship"), json.dumps(job.get("raw_data", {})),
                datetime.utcnow().isoformat(), existing["id"]
            ))
            return existing["id"]
        else:
            cursor = conn.execute("""
                INSERT INTO jobs (
                    external_id, title, company, location, description, url,
                    source, job_type, salary_min, salary_max, posted_date,
                    deadline, remote, visa_sponsorship, tags, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.get("external_id"), job.get("title"), job.get("company"),
                job.get("location"), job.get("description"), job.get("url"),
                job.get("source"), job.get("job_type"), job.get("salary_min"),
                job.get("salary_max"), job.get("posted_date"), job.get("deadline"),
                job.get("remote", False), job.get("visa_sponsorship"),
                json.dumps(job.get("tags", [])), json.dumps(job.get("raw_data", {}))
            ))
            return cursor.lastrowid


def update_job_score(job_id: int, score: float, reasoning: str):
    """Update AI match score for a job."""
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET match_score=?, match_reasoning=?, updated_at=? WHERE id=?",
            (score, reasoning, datetime.utcnow().isoformat(), job_id)
        )


def update_job_status(job_id: int, status: str):
    """Update job status (new, interested, applied, rejected, interviewing, offer)."""
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET status=?, updated_at=? WHERE id=?",
            (status, datetime.utcnow().isoformat(), job_id)
        )


def get_jobs(status=None, min_score=None, source=None, limit=100, offset=0):
    """Get jobs with optional filters."""
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if min_score is not None:
        query += " AND match_score >= ?"
        params.append(min_score)
    if source:
        query += " AND source = ?"
        params.append(source)

    query += " ORDER BY match_score DESC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_job(job_id: int):
    """Get a single job by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def create_application(job_id: int, cover_letter: str = "", resume_version: str = "default"):
    """Create an application record."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO applications (job_id, cover_letter, resume_version) VALUES (?, ?, ?)",
            (job_id, cover_letter, resume_version)
        )
        return cursor.lastrowid


def update_application(app_id: int, **kwargs):
    """Update application fields."""
    allowed = {"status", "cover_letter", "resume_version", "applied_at", "follow_up_date", "notes", "response"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return

    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [app_id]

    with get_db() as conn:
        conn.execute(f"UPDATE applications SET {set_clause} WHERE id=?", values)


def get_applications(status=None):
    """Get applications with job details."""
    query = """
        SELECT a.*, j.title, j.company, j.url, j.match_score, j.location
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
    """
    params = []
    if status:
        query += " WHERE a.status = ?"
        params.append(status)
    query += " ORDER BY a.created_at DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_stats():
    """Get dashboard statistics."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        new = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='new'").fetchone()[0]
        interested = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='interested'").fetchone()[0]
        applied = conn.execute("SELECT COUNT(*) FROM applications WHERE status='applied'").fetchone()[0]
        interviewing = conn.execute("SELECT COUNT(*) FROM applications WHERE status='interviewing'").fetchone()[0]
        avg_score = conn.execute("SELECT AVG(match_score) FROM jobs WHERE match_score > 0").fetchone()[0]
        top_match = conn.execute("SELECT MAX(match_score) FROM jobs").fetchone()[0]
        sources = conn.execute("SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source ORDER BY cnt DESC").fetchall()

        return {
            "total_jobs": total,
            "new_jobs": new,
            "interested": interested,
            "applied": applied,
            "interviewing": interviewing,
            "avg_score": round(avg_score or 0, 1),
            "top_match": round(top_match or 0, 1),
            "sources": {r["source"]: r["cnt"] for r in sources},
        }


def log_search(query: str, source: str, count: int):
    """Log a search query."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO search_history (query, source, results_count) VALUES (?, ?, ?)",
            (query, source, count)
        )


def get_setting(key: str, default=None):
    """Get a setting value."""
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    """Set a setting value."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
