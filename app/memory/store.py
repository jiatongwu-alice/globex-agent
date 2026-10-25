
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager


DB_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "globex.sqlite3"
)


@contextmanager
def db_connection():
    """Manage database connections and transactions."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create persistent memory tables."""

    with db_connection() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS brand_profiles (
                profile_id TEXT PRIMARY KEY,
                profile_json TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)
        conn.execute("""
    CREATE TABLE IF NOT EXISTS personal_skills (
        skill_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        instructions TEXT NOT NULL
            )
        """)


def save_brand_profile(profile_id: str, profile: dict):
    """Save or update a brand's long-term preferences."""

    profile_json = json.dumps(
        profile,
        ensure_ascii=False
    )

    with db_connection() as conn:
        conn.execute("""
            INSERT INTO brand_profiles
                (profile_id, profile_json)
            VALUES (?, ?)
            ON CONFLICT(profile_id)
            DO UPDATE SET
                profile_json = excluded.profile_json
        """, (profile_id, profile_json))


def load_brand_profile(profile_id: str) -> dict:
    """Retrieve a saved brand profile."""

    with db_connection() as conn:
        row = conn.execute(
            "SELECT profile_json FROM brand_profiles "
            "WHERE profile_id = ?",
            (profile_id,)
        ).fetchone()

    return json.loads(row[0]) if row else {}


def save_message(session_id: str, role: str, content: str):
    """Store a conversation message."""

    if role not in {"user", "assistant"}:
        raise ValueError("Invalid message role.")

    with db_connection() as conn:
        conn.execute("""
            INSERT INTO session_messages
                (session_id, role, content)
            VALUES (?, ?, ?)
        """, (session_id, role, content))


def load_recent_messages(
    session_id: str,
    limit: int = 10
) -> list[dict]:
    """Retrieve recent conversation messages."""

    if limit < 1:
        raise ValueError("Limit must be positive.")

    with db_connection() as conn:
        rows = conn.execute("""
            SELECT role, content
            FROM session_messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (session_id, limit)).fetchall()

    return [
        {"role": role, "content": content}
        for role, content in reversed(rows)
    ]


def save_skill(
    skill_id: str,
    title: str,
    instructions: str
):
    """Save or update a reusable research skill."""

    if not all((skill_id.strip(), title.strip(), instructions.strip())):
        raise ValueError("Skill fields cannot be empty.")

    with db_connection() as conn:
        conn.execute("""
            INSERT INTO personal_skills
                (skill_id, title, instructions)
            VALUES (?, ?, ?)
            ON CONFLICT(skill_id) DO UPDATE SET
                title = excluded.title,
                instructions = excluded.instructions
        """, (skill_id, title, instructions))


def load_skill(skill_id: str) -> dict | None:
    """Retrieve a saved skill by ID."""

    with db_connection() as conn:
        row = conn.execute("""
            SELECT skill_id, title, instructions
            FROM personal_skills
            WHERE skill_id = ?
        """, (skill_id,)).fetchone()

    if row is None:
        return None

    return {
        "skill_id": row[0],
        "title": row[1],
        "instructions": row[2]
    }
