import json
import os
from datetime import datetime, date

DATA_FILE = "app/frontend/data/tasks.json"

def load_tasks():
    """Load tasks from JSON. Converts strings back to Date objects."""
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            for t in data:
                # Convert date string to object
                t['deadline'] = datetime.strptime(t['deadline'], "%Y-%m-%d").date()
                # Ensure notes field exists
                if 'notes' not in t:
                    t['notes'] = ""
                # Convert datetimes if they exist
                if t.get('start_time'):
                    t['start_time'] = datetime.fromisoformat(t['start_time'])
                if t.get('end_time'):
                    t['end_time'] = datetime.fromisoformat(t['end_time'])
            return data
    except Exception as e:
        print(f"Error loading tasks: {e}")
        return []

def save_tasks(tasks):
    """Save tasks to JSON. Converts Date objects to strings."""
    serializable_tasks = []
    for t in tasks:
        task_dict = t.copy()
        # Convert date to string
        if isinstance(task_dict['deadline'], date):
            task_dict['deadline'] = task_dict['deadline'].strftime("%Y-%m-%d")
        # Convert datetimes to strings
        if task_dict.get('start_time') and isinstance(task_dict['start_time'], datetime):
            task_dict['start_time'] = task_dict['start_time'].isoformat()
        if task_dict.get('end_time') and isinstance(task_dict['end_time'], datetime):
            task_dict['end_time'] = task_dict['end_time'].isoformat()
        serializable_tasks.append(task_dict)

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(serializable_tasks, f, indent=4)

def clear_schedule_results(tasks):
    """Reset the 'scheduled' times for all tasks (used when re-optimizing)."""
    for t in tasks:
        t['start_time'] = None
        t['end_time'] = None
    save_tasks(tasks)