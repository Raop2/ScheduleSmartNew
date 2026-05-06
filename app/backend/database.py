"""
database.py — SQLite Database and Authentication
Handles schema creation, user auth (SHA-256 hashing), task CRUD,
completion logging, preferences, and streaks. All tables scoped
by user_id for data isolation. Implements FR-14, FR-15, NFR-06, NFR-07.
"""
import sqlite3
import os
import hashlib
import uuid
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "../frontend/data/schedulesmart.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS users (
                                                        id TEXT PRIMARY KEY,
                                                        username TEXT UNIQUE NOT NULL,
                                                        password_hash TEXT NOT NULL,
                                                        created_at TEXT NOT NULL
                   )
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS tasks (
                                                        id TEXT PRIMARY KEY,
                                                        user_id TEXT DEFAULT 'legacy',
                                                        name TEXT,
                                                        module TEXT,
                                                        priority TEXT,
                                                        duration INTEGER,
                                                        deadline TEXT,
                                                        preferred_time TEXT,
                                                        is_fixed BOOLEAN,
                                                        start_time TEXT,
                                                        end_time TEXT,
                                                        completed BOOLEAN,
                                                        notes TEXT
                   )
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS completion_log (
                                                                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                 user_id TEXT DEFAULT 'legacy',
                                                                 task_id TEXT,
                                                                 completion_date TEXT,
                                                                 module TEXT,
                                                                 duration INTEGER
                   )
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS user_preferences (
                                                                   key TEXT,
                                                                   user_id TEXT DEFAULT 'legacy',
                                                                   value TEXT,
                                                                   PRIMARY KEY (key, user_id)
                       )
                   """)

    # Migration: add user_id columns if they don't exist yet
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN user_id TEXT DEFAULT 'legacy'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE completion_log ADD COLUMN user_id TEXT DEFAULT 'legacy'")
    except sqlite3.OperationalError:
        pass

    # For user_preferences, check if user_id column exists
    cursor.execute("PRAGMA table_info(user_preferences)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'user_id' not in columns:
        cursor.execute("DROP TABLE user_preferences")
        cursor.execute("""
                       CREATE TABLE user_preferences (
                                                         key TEXT,
                                                         user_id TEXT DEFAULT 'legacy',
                                                         value TEXT,
                                                         PRIMARY KEY (key, user_id)
                       )
                       """)

    conn.commit()
    conn.close()


def hash_password(password):
    salt = "schedulesmart_salt_2026"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def create_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    user_id = str(uuid.uuid4())
    try:
        cursor.execute(
            "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username.lower().strip(), hash_password(password), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def authenticate_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE username = ? AND password_hash = ?",
        (username.lower().strip(), hash_password(password))
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['id']
    return None


def username_exists(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username.lower().strip(),))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def get_streak(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT completion_date FROM completion_log WHERE user_id = ? ORDER BY completion_date DESC",
        (user_id,)
    )
    dates = [row['completion_date'] for row in cursor.fetchall()]
    conn.close()

    if not dates:
        return 0

    streak = 0
    current_date = date.today()

    if dates[0] != current_date.isoformat() and dates[0] != (current_date - timedelta(days=1)).isoformat():
        return 0

    check_date = date.fromisoformat(dates[0])
    for d_str in dates:
        if d_str == check_date.isoformat():
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    return streak


def mark_task_completed(task_id, module, duration, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    today_str = date.today().isoformat()

    cursor.execute("UPDATE tasks SET completed = 1 WHERE id = ? AND user_id = ?", (task_id, user_id))
    cursor.execute(
        "INSERT INTO completion_log (task_id, completion_date, module, duration, user_id) VALUES (?, ?, ?, ?, ?)",
        (task_id, today_str, module, duration, user_id)
    )

    conn.commit()
    conn.close()


def bulk_update_schedule(scheduled_tasks):
    conn = get_connection()
    cursor = conn.cursor()

    for task in scheduled_tasks:
        cursor.execute(
            "UPDATE tasks SET start_time = ?, end_time = ? WHERE id = ?",
            (task['start_time'], task['end_time'], task['id'])
        )

    conn.commit()
    conn.close()


def clear_scheduled_times(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET start_time = NULL, end_time = NULL WHERE is_fixed = 0 AND user_id = ?", (user_id,))
    conn.commit()
    conn.close()