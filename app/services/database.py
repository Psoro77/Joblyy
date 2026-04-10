import aiosqlite
from pathlib import Path

DB_PATH = Path("data/app.db")
USER_ID = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT UNIQUE,
    description TEXT,
    source TEXT,
    match_score REAL,
    status TEXT DEFAULT 'found',
    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    user_id INTEGER REFERENCES users(id),
    applied_at TIMESTAMP,
    method TEXT,
    status TEXT DEFAULT 'submitted',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


def _row_to_dict(cursor: aiosqlite.Cursor, row: tuple) -> dict:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


# ── Jobs ──

async def save_job(
    title: str,
    company: str,
    url: str,
    description: str | None = None,
    source: str | None = None,
    match_score: float | None = None,
) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO jobs (user_id, title, company, url, description, source, match_score)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (USER_ID, title, company, url, description, source, match_score),
        )
        await db.commit()
        job_id = cursor.lastrowid

    return await get_job(job_id)


async def get_job(job_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = _row_to_dict
        cursor = await db.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        )
        return await cursor.fetchone()


async def get_jobs(status: str | None = None, limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = _row_to_dict
        if status:
            cursor = await db.execute(
                "SELECT * FROM jobs WHERE user_id = ? AND status = ? ORDER BY found_at DESC LIMIT ?",
                (USER_ID, status, limit),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM jobs WHERE user_id = ? ORDER BY found_at DESC LIMIT ?",
                (USER_ID, limit),
            )
        return await cursor.fetchall()


async def update_job(job_id: int, **fields) -> dict | None:
    """Update only the provided fields on a job row."""
    if not fields:
        return await get_job(job_id)

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE jobs SET {set_clause} WHERE id = ?", values
        )
        await db.commit()

    return await get_job(job_id)


# ── Applications ──

async def create_application(
    job_id: int,
    method: str = "manual",
    notes: str | None = None,
) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO applications (job_id, user_id, applied_at, method, notes)
               VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)""",
            (job_id, USER_ID, method, notes),
        )
        await db.commit()
        app_id = cursor.lastrowid

        db.row_factory = _row_to_dict
        cursor = await db.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        )
        return await cursor.fetchone()


# ── Conversations ──

async def save_message(role: str, content: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
            (USER_ID, role, content),
        )
        await db.commit()
        msg_id = cursor.lastrowid

        db.row_factory = _row_to_dict
        cursor = await db.execute(
            "SELECT * FROM conversations WHERE id = ?", (msg_id,)
        )
        return await cursor.fetchone()


async def get_conversation_history(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = _row_to_dict
        cursor = await db.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at ASC LIMIT ?",
            (USER_ID, limit),
        )
        return await cursor.fetchall()


# ── Users ──

async def upsert_user_name(name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (id, name) VALUES (?, ?)
               ON CONFLICT(id) DO UPDATE SET name = excluded.name""",
            (USER_ID, name),
        )
        await db.commit()


async def get_applications(job_id: int | None = None) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = _row_to_dict
        if job_id is not None:
            cursor = await db.execute(
                """SELECT a.id, a.job_id, a.applied_at, a.method, a.status, a.notes,
                          j.title, j.company, j.url, j.status AS job_status
                   FROM applications a JOIN jobs j ON a.job_id = j.id
                   WHERE a.user_id = ? AND a.job_id = ?
                   ORDER BY a.applied_at DESC""",
                (USER_ID, job_id),
            )
        else:
            cursor = await db.execute(
                """SELECT a.id, a.job_id, a.applied_at, a.method, a.status, a.notes,
                          j.title, j.company, j.url, j.status AS job_status
                   FROM applications a JOIN jobs j ON a.job_id = j.id
                   WHERE a.user_id = ?
                   ORDER BY a.applied_at DESC""",
                (USER_ID,),
            )
        return await cursor.fetchall()
