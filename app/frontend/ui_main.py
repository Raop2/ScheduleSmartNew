import sys
import os
from pathlib import Path

# --- MAGIC PATH FIX ---
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

import streamlit as st
from datetime import datetime, date, time

# --- DIRECT IMPORTS ---
from app.backend.scheduler import ScheduleEngine
from app.backend.models import Task, UserPreferences, TaskPriority

st.set_page_config(page_title="ScheduleSmart", page_icon="📅", layout="wide")

def clear_schedule():
    """Reset the schedule when user changes settings"""
    if "schedule_result" in st.session_state:
        del st.session_state["schedule_result"]

def main():
    st.title("📅 ScheduleSmart")
    # FIX 1: Removed "Dissertation Edition"
    st.markdown("### Intelligent Study Planner")
    st.markdown("---")

    # --- SIDEBAR CONFIGURATION ---
    with st.sidebar:
        st.header("⚙️ Configuration")

        st.subheader("Scheduling Engine")
        # FIX 2: Added on_change=clear_schedule to wipe old results when switching
        strategy = st.selectbox(
            "Optimization Strategy",
            ("greedy", "cpsat"),
            format_func=lambda x: "⚡ Greedy (Instant)" if x == "greedy" else "🧠 CP-SAT (AI Optimized)",
            on_change=clear_schedule
        )

        st.divider()

        st.subheader("Preferences")
        start_time = st.slider("Start Day At", 0, 23, 9, on_change=clear_schedule)
        end_time = st.slider("End Day At", 0, 23, 17, on_change=clear_schedule)
        include_weekends = st.checkbox("Include Weekends?", value=False, on_change=clear_schedule)

    col1, col2 = st.columns([1, 2])

    # --- ADD TASK FORM ---
    with col1:
        st.subheader("📝 Add New Task")
        with st.form("task_form"):
            task_name = st.text_input("Task Name")
            duration = st.number_input("Duration (minutes)", min_value=15, step=15, value=60)
            priority = st.selectbox("Priority", ["high", "medium", "low"])
            deadline_date = st.date_input("Deadline", min_value=date.today())

            submitted = st.form_submit_button("Add Task")

        if submitted and task_name:
            add_task_to_session(task_name, duration, priority, deadline_date)
            st.toast(f"Task Added: {task_name}", icon="✅")

    # --- TASK QUEUE & GENERATION ---
    with col2:
        st.subheader("📋 Your Task Queue")
        if "tasks" not in st.session_state:
            st.session_state.tasks = []

        if st.session_state.tasks:
            for i, t in enumerate(st.session_state.tasks):
                st.text(f"{i+1}. {t['name']} ({t['duration_minutes']}m) - {t['priority'].upper()}")

            if st.button("🚀 Generate Schedule"):
                with st.spinner("Running Optimization Engine..."):
                    try:
                        result = run_schedule_logic(start_time, end_time, include_weekends, strategy)
                        st.session_state.schedule_result = result

                        # FIX 3: Balloons ONLY happen here (inside the button click)
                        if result['status'] != "failed" and len(result['scheduled_tasks']) > 0:
                            st.balloons()

                    except Exception as e:
                        st.error(f"Optimization Failed: {e}")
        else:
            st.info("No tasks added yet.")

    # --- DISPLAY RESULTS ---
    if "schedule_result" in st.session_state:
        st.markdown("---")
        st.subheader("✨ Your Optimized Schedule")

        result = st.session_state.schedule_result

        if result['status'] == "failed":
            st.error("Could not find a valid schedule. Try extending deadlines or enabling weekends.")
        else:
            m1, m2 = st.columns(2)
            m1.metric("Total Study Hours", f"{result['total_hours']:.1f} hrs")
            m2.metric("Tasks Scheduled", len(result['scheduled_tasks']))

            st.success("Optimization Successful! Here is your plan:")

            for task in result['scheduled_tasks']:
                with st.expander(f"✅ {task['start_time'].strftime('%H:%M')} - {task['name']}", expanded=True):
                    st.write(f"**Time:** {task['start_time'].strftime('%A, %d %b %Y %H:%M')} to {task['end_time'].strftime('%H:%M')}")
                    st.write(f"**Reasoning:** *{task['reason']}*")

def add_task_to_session(name, duration, priority, deadline):
    if "tasks" not in st.session_state:
        st.session_state.tasks = []

    new_task = {
        "id": str(len(st.session_state.tasks) + 1),
        "name": name,
        "duration_minutes": duration,
        "priority": priority,
        "deadline": deadline,
        "fixed_slot": None
    }
    st.session_state.tasks.append(new_task)

def run_schedule_logic(start, end, weekends, strategy):
    # Convert Session Data to Pydantic Models
    task_objects = []
    for t in st.session_state.tasks:
        dt_deadline = datetime.combine(t['deadline'], time(23, 59))
        prio_map = {"high": TaskPriority.HIGH, "medium": TaskPriority.MEDIUM, "low": TaskPriority.LOW}

        task_objects.append(Task(
            id=t['id'],
            name=t['name'],
            duration_minutes=t['duration_minutes'],
            priority=prio_map[t['priority']],
            deadline=dt_deadline
        ))

    prefs = UserPreferences(
        start_time_hour=start,
        end_time_hour=end,
        include_weekends=weekends
    )

    engine = ScheduleEngine()
    result = engine.generate_schedule(task_objects, prefs, method=strategy)

    total_minutes = sum([t.duration_minutes for t in task_objects])

    return {
        "scheduled_tasks": result["scheduled"],
        "unscheduled_tasks": result["unscheduled"],
        "total_hours": total_minutes / 60.0,
        "status": result["status"]
    }

if __name__ == "__main__":
    main()