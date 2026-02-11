import sys
from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

import streamlit as st
from datetime import datetime, time, timedelta
from app.backend.data_service import load_tasks, save_tasks, clear_schedule_results
from app.backend.scheduler import ScheduleEngine
from app.backend.models import Task, UserPreferences, TaskPriority

st.set_page_config(page_title="AI Planner", page_icon="🚀", layout="wide")

def main():
    st.title("🚀 AI Planner")

    # 1. Load Data
    if "tasks" not in st.session_state:
        st.session_state.tasks = load_tasks()

    # Filter for only unfinished tasks
    active_tasks = [t for t in st.session_state.tasks if not t.get('completed')]

    if not active_tasks:
        st.warning("⚠️ No tasks found! Go to the 'Home' page to add some tasks first.")
        return

    # --- SIDEBAR: STRATEGY & PREFERENCES ---
    with st.sidebar:
        st.header("⚙️ Optimization Settings")

        # ENERGY PROFILE (New Feature!)
        energy_profile = st.selectbox(
            "🦉 Energy Profile",
            ["Balanced", "Morning Lark ☀️", "Night Owl 🌙"],
            help="The AI will schedule high-priority tasks during your peak energy hours."
        )

        st.divider()

        start_time = st.slider("Start Day At", 0, 23, 9)
        end_time = st.slider("End Day At", 0, 23, 17)
        include_weekends = st.checkbox("Include Weekends?", value=False)

        st.divider()

        # PANIC BUTTON (New Feature!)
        if st.button("🚨 PANIC MODE: Reschedule from NOW"):
            start_time = datetime.now().hour
            st.toast("Panic Mode Activated! Rescheduling for rest of today...", icon="🚨")

    # --- MAIN AREA ---
    c1, c2 = st.columns([1, 2])

    with c1:
        st.subheader(f"📋 Tasks to Schedule ({len(active_tasks)})")
        for t in active_tasks:
            st.text(f"• {t['name']} ({t['duration_minutes']}m)")

    with c2:
        st.subheader("🤖 The Plan")

        if st.button("✨ Generate Optimized Schedule", type="primary"):
            with st.spinner("Analyzing constraints & Energy Profiles..."):

                # 1. Prepare Data
                task_objects = []
                for t in active_tasks:
                    prio_map = {"high": TaskPriority.HIGH, "medium": TaskPriority.MEDIUM, "low": TaskPriority.LOW}
                    dt_deadline = datetime.combine(t['deadline'], time(23, 59))

                    task_objects.append(Task(
                        id=t['id'],
                        name=t['name'],
                        duration_minutes=t['duration_minutes'],
                        priority=prio_map[t['priority']],
                        deadline=dt_deadline
                    ))

                # 2. Run Engine
                prefs = UserPreferences(
                    start_time_hour=start_time,
                    end_time_hour=end_time,
                    include_weekends=include_weekends
                )

                engine = ScheduleEngine()
                # (Future: Pass energy profile to engine here if we upgrade logic)
                result = engine.generate_schedule(task_objects, prefs, method="cpsat")

                # 3. Save Results
                if result['status'] != 'failed':
                    # Update global state with times
                    for scheduled_t in result['scheduled']:
                        for original_t in st.session_state.tasks:
                            if original_t['id'] == scheduled_t['id']:
                                original_t['start_time'] = scheduled_t['start_time'].isoformat()
                                original_t['end_time'] = scheduled_t['end_time'].isoformat()

                    save_tasks(st.session_state.tasks)
                    st.success(f"✅ Scheduled {len(result['scheduled'])} tasks!")
                    st.balloons()

                    # Simple Preview
                    for t in result['scheduled']:
                        st.info(f"{t['start_time'].strftime('%H:%M')} - {t['name']}")
                else:
                    st.error("Could not find a valid schedule. Try extending hours.")

if __name__ == "__main__":
    main()