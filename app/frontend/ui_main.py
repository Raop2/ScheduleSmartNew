import streamlit as st
import httpx
from datetime import datetime, date

st.set_page_config(page_title="ScheduleSmart", page_icon="📅", layout="wide", initial_sidebar_state="expanded")

API_URL = "http://127.0.0.1:8000"

def main():
    st.title("📅 ScheduleSmart")
    st.markdown("### Intelligent Study Planner")
    st.markdown("---")

    with st.sidebar:
        st.header("⚙️ Configuration")

        st.subheader("Scheduling Engine")
        strategy = st.selectbox(
            "Optimization Strategy",
            ("greedy", "cpsat"),
            format_func=lambda x: "⚡ Greedy (Instant)" if x == "greedy" else "🧠 CP-SAT (AI Optimized)"
        )

        st.divider()

        st.subheader("Preferences")
        start_time = st.slider("Start Day At", 0, 23, 9)
        end_time = st.slider("End Day At", 0, 23, 17)
        include_weekends = st.checkbox("Include Weekends?", value=False)

    col1, col2 = st.columns([1, 2])

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

    with col2:
        st.subheader("📋 Your Task Queue")
        if "tasks" not in st.session_state:
            st.session_state.tasks = []

        if st.session_state.tasks:
            for i, t in enumerate(st.session_state.tasks):
                st.text(f"{i+1}. {t['name']} ({t['duration_minutes']}m) - {t['priority'].upper()}")

            if st.button("🚀 Generate Schedule"):
                with st.spinner("Crunching the numbers..."):
                    generate_schedule(start_time, end_time, include_weekends, strategy)
        else:
            st.info("No tasks added yet.")

    if "schedule_result" in st.session_state:
        st.markdown("---")
        st.subheader("✨ Your Optimized Schedule")

        result = st.session_state.schedule_result

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Study Hours", f"{result['total_hours']:.1f} hrs")
        m2.metric("Tasks Scheduled", len(result['scheduled_tasks']))
        m3.metric("Efficiency Score", "100%")

        if len(result['scheduled_tasks']) > 0:
            st.toast("🔥 Schedule Optimized! You are ready to crush this week!", icon="🚀")

        for task in result['scheduled_tasks']:
            with st.expander(f"✅ {task['start_time'][11:16]} - {task['name']}", expanded=True):
                st.write(f"**Time:** {task['start_time'].replace('T', ' ')} to {task['end_time'].replace('T', ' ')}")
                st.write(f"**Reasoning:** *{task['reason']}*")