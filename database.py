from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator


DATABASE_PATH = Path(__file__).with_name("tasks.db")
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"
PASSWORD_ITERATIONS = 260_000
TASK_CATEGORIES = ("Assignment", "Exam", "Project", "Personal")
TASK_PRIORITIES = ("High", "Medium", "Low")
TASK_STATUSES = ("Pending", "In Progress", "Completed")


@contextmanager
def _connection(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )


def init_db(db_path: str | Path = DATABASE_PATH) -> None:
    with _connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 120),
                category TEXT NOT NULL
                    CHECK(category IN ('Assignment', 'Exam', 'Project', 'Personal')),
                priority TEXT NOT NULL CHECK(priority IN ('High', 'Medium', 'Low')),
                due_date TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK(status IN ('Pending', 'In Progress', 'Completed')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS tasks_user_due_date
                ON tasks(user_id, due_date);
            """
        )
        user = connection.execute(
            "SELECT id FROM users WHERE username = ?", (DEFAULT_USERNAME,)
        ).fetchone()
        if user is None:
            salt = secrets.token_bytes(16)
            connection.execute(
                """
                INSERT INTO users (username, password_salt, password_hash)
                VALUES (?, ?, ?)
                """,
                (DEFAULT_USERNAME, salt, _hash_password(DEFAULT_PASSWORD, salt)),
            )


def create_user(
    username: str, password: str, db_path: str | Path = DATABASE_PATH
) -> int:
    normalized_username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,32}", normalized_username):
        raise ValueError("Username must be 3–32 letters, numbers, or underscores.")
    if not 8 <= len(password) <= 128:
        raise ValueError("Password must be between 8 and 128 characters.")

    salt = secrets.token_bytes(16)
    try:
        with _connection(db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (username, password_salt, password_hash)
                VALUES (?, ?, ?)
                """,
                (normalized_username, salt, _hash_password(password, salt)),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        raise ValueError("That username is already taken.") from error


def authenticate(
    username: str, password: str, db_path: str | Path = DATABASE_PATH
) -> dict[str, int | str] | None:
    with _connection(db_path) as connection:
        user = connection.execute(
            """
            SELECT id, username, password_salt, password_hash
            FROM users WHERE username = ?
            """,
            (username.strip(),),
        ).fetchone()
    if user is None:
        return None
    if not hmac.compare_digest(
        _hash_password(password, user["password_salt"]), user["password_hash"]
    ):
        return None
    return {"id": int(user["id"]), "username": str(user["username"])}


def _validated_task(
    name: str,
    category: str,
    priority: str,
    due_date: str | date,
    status: str,
) -> tuple[str, str, str, str, str]:
    normalized_name = name.strip()
    if not normalized_name or len(normalized_name) > 120:
        raise ValueError("Task name must contain 1–120 characters.")
    if category not in TASK_CATEGORIES:
        raise ValueError("Choose a valid task category.")
    if priority not in TASK_PRIORITIES:
        raise ValueError("Choose a valid task priority.")
    if status not in TASK_STATUSES:
        raise ValueError("Choose a valid task status.")

    try:
        parsed_date = (
            due_date if isinstance(due_date, date) else date.fromisoformat(due_date)
        )
    except (TypeError, ValueError) as error:
        raise ValueError("Due date must be a valid calendar date.") from error
    if parsed_date.isoformat() != str(due_date) and not isinstance(due_date, date):
        raise ValueError("Due date must use YYYY-MM-DD format.")

    return normalized_name, category, priority, parsed_date.isoformat(), status


def add_task(
    user_id: int,
    name: str,
    category: str,
    priority: str,
    due_date: str | date,
    status: str = "Pending",
    db_path: str | Path = DATABASE_PATH,
) -> int:
    values = _validated_task(name, category, priority, due_date, status)
    with _connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (user_id, name, category, priority, due_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, *values),
        )
        return int(cursor.lastrowid)


def get_tasks(
    user_id: int, db_path: str | Path = DATABASE_PATH
) -> list[dict[str, object]]:
    with _connection(db_path) as connection:
        tasks = connection.execute(
            """
            SELECT id, name, category, priority, due_date, status
            FROM tasks
            WHERE user_id = ?
            ORDER BY due_date, id
            """,
            (user_id,),
        ).fetchall()
    return [dict(task) for task in tasks]


def update_task(
    user_id: int,
    task_id: int,
    name: str,
    category: str,
    priority: str,
    due_date: str | date,
    status: str,
    db_path: str | Path = DATABASE_PATH,
) -> None:
    values = _validated_task(name, category, priority, due_date, status)
    with _connection(db_path) as connection:
        result = connection.execute(
            """
            UPDATE tasks
            SET name = ?, category = ?, priority = ?, due_date = ?, status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (*values, task_id, user_id),
        )
        if result.rowcount == 0:
            raise LookupError("Task not found.")


def delete_task(
    user_id: int, task_id: int, db_path: str | Path = DATABASE_PATH
) -> None:
    with _connection(db_path) as connection:
        result = connection.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
        )
        if result.rowcount == 0:
            raise LookupError("Task not found.")
