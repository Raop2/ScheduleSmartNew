import sqlite3
import os
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
                   CREATE TABLE IF NOT EXISTS tasks (
                                                        id TEXT PRIMARY KEY,
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
                                                                 task_id TEXT,
                                                                 completion_date TEXT,
                                                                 module TEXT,
                                                                 duration INTEGER
                   )
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS user_preferences (
                                                                   key TEXT PRIMARY KEY,
                                                                   value TEXT
                   )
                   """)

    conn.commit()
    conn.close()

def get_streak():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT completion_date FROM completion_log ORDER BY completion_date DESC")
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

def mark_task_completed(task_id, module, duration):
    conn = get_connection()
    cursor = conn.cursor()
    today_str = date.today().isoformat()

    cursor.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
    cursor.execute(
        "INSERT INTO completion_log (task_id, completion_date, module, duration) VALUES (?, ?, ?, ?)",
        (task_id, today_str, module, duration)
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

def clear_scheduled_times():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET start_time = NULL, end_time = NULL WHERE is_fixed = 0")
    conn.commit()
    conn.close()