import json
import os
from datetime import date, datetime

# Define the path to the JSON file
DATA_FILE = os.path.join(os.path.dirname(__file__), "../frontend/data/tasks.json")

def load_tasks():
    """Loads tasks from the JSON file and converts dates back to objects."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            # Convert date strings back to Python date objects
            for t in data:
                if t.get('deadline') and isinstance(t['deadline'], str):
                    try:
                        t['deadline'] = date.fromisoformat(t['deadline'])
                    except ValueError:
                        pass # Keep as string if format fails
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_tasks(tasks):
    """Converts dates to strings and saves tasks to the JSON file."""
    tasks_to_save = []

    for t in tasks:
        # Create a copy so we don't mess up the live session_state
        t_copy = t.copy()

        # safely convert deadline if it exists
        if t_copy.get('deadline') and isinstance(t_copy['deadline'], (date, datetime)):
            t_copy['deadline'] = t_copy['deadline'].isoformat()

        tasks_to_save.append(t_copy)

    # Ensure directory exists
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    with open(DATA_FILE, "w") as f:
        json.dump(tasks_to_save, f, indent=4)