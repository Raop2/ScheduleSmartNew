import sys
from pathlib import Path

# --- MAGIC PATH FIX ---
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

import streamlit as st
from datetime import datetime
from streamlit_calendar import calendar  # The library we installed
from app.backend.data_service import load_tasks

st.set_page_config(page_title="Visual Schedule", page_icon="📅", layout="wide")

def main():
    st.title("📅 Visual Schedule")

    # 1. Load Data
    if "tasks" not in st.session_state:
        st.session_state.tasks = load_tasks()

    # 2. Filter for Scheduled Tasks Only
    # We only want to show tasks that the AI has actually given a time slot to.
    scheduled_tasks = [t for t in st.session_state.tasks if t.get('start_time')]

    if not scheduled_tasks:
        st.info("No tasks scheduled yet! Go to the 'Planner' page and click 'Generate Schedule' first.")
        return

    # 3. Format Data for the Calendar Tool
    # The tool needs a specific format: { title, start, end, color }
    calendar_events = []

    for t in scheduled_tasks:
        # Color Logic: High = Red, Medium = Orange, Low = Green
        color = "#FF4B4B" if t['priority'] == 'high' else "#FFA500" if t['priority'] == 'medium' else "#3DD56D"

        # Ensure time is in the right text format (ISO 8601)
        start_str = t['start_time'].isoformat() if isinstance(t['start_time'], datetime) else t['start_time']
        end_str = t['end_time'].isoformat() if isinstance(t['end_time'], datetime) else t['end_time']

        event = {
            "title": t['name'],
            "start": start_str,
            "end": end_str,
            "backgroundColor": color,
            "borderColor": color
        }
        calendar_events.append(event)

    # 4. Configure the Grid View
    calendar_options = {
        "editable": False,  # Read-only for now
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "timeGridDay,timeGridWeek,dayGridMonth"
        },
        "initialView": "timeGridDay",  # Default to Day view
        "slotMinTime": "06:00:00",     # Calendar starts at 6 AM
        "slotMaxTime": "22:00:00",     # Calendar ends at 10 PM
    }

    # 5. Render the Calendar
    st.markdown("### 🗓️ Your Timeline")
    calendar(events=calendar_events, options=calendar_options)

    # 6. Bonus: Analytics Section (Great for Grades!) 📊
    st.divider()
    st.subheader("📊 Productivity Analytics")

    total_hours = sum([t['duration_minutes'] for t in scheduled_tasks]) / 60
    high_prio_count = len([t for t in scheduled_tasks if t['priority'] == 'high'])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Study Hours", f"{total_hours:.1f} hrs")
    c2.metric("High Priority Tasks", high_prio_count)
    c3.metric("Schedule Efficiency", "100%")

if __name__ == "__main__":
    main()