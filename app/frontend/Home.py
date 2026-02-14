import sys
import time
from pathlib import Path
from datetime import date, datetime, time as dt_time, timedelta

# Fix path
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar

# Backend Imports
from app.backend.data_service import load_tasks, save_tasks
from app.backend.scheduler import ScheduleEngine
from app.backend.models import Task, UserPreferences, TaskPriority
from app.backend.export_service import generate_ics_file

# --- PAGE CONFIG ---
st.set_page_config(page_title="ScheduleSmart Pro", page_icon="🎓", layout="wide")

# --- PROFESSIONAL CSS (Cards & Shadow) ---
st.markdown("""
<style>
    /* Hide default sidebar nav */
    [data-testid="stSidebarNav"] {display: none;}
    
    /* Card Styling */
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    .metric-value {
        font-size: 32px;
        font-weight: 700;
        color: #1f77b4;
        margin: 0;
    }
    .metric-label {
        font-size: 14px;
        color: #666;
        margin-top: 5px;
    }
    
    /* Clean Headers */
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; }
    
    /* Task Card Styling */
    .stContainer { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

def main():
    # 1. Load Data
    if "tasks" not in st.session_state:
        st.session_state.tasks = load_tasks()

    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.title("🎓 ScheduleSmart")
        st.caption("Intelligent Study Planner")

        selected = option_menu(
            menu_title=None,
            options=["Dashboard", "Add Task", "Calendar", "AI Engine"],
            icons=["house", "plus-circle", "calendar-event", "cpu"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#f8f9fa"},
                "nav-link": {"font-size": "14px", "text-align": "left", "margin": "5px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#FF4B4B"},
            }
        )
        st.divider()
        st.info("💡 **Pro Tip:** Use 'Exam Cram' mode during finals week.")

    # --- ROUTING ---
    if selected == "Dashboard":
        render_dashboard()
    elif selected == "Add Task":
        render_add_task()
    elif selected == "Calendar":
        render_calendar()
    elif selected == "AI Engine":
        render_engine()

# ==========================================
# 🏠 VIEW 1: THE DASHBOARD (Metric Cards)
# ==========================================
def render_dashboard():
    st.header("👋 My Dashboard")

    # Calculate Metrics
    active_tasks = [t for t in st.session_state.tasks if not t.get('completed')]
    overdue = [t for t in active_tasks if t['deadline'] < date.today()]
    completed_count = len([t for t in st.session_state.tasks if t.get('completed')])

    # METRIC CARDS ROW
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(active_tasks)}</div>
            <div class="metric-label">👁️ Pending Tasks</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        color = "#ff4b4b" if overdue else "#1f77b4"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {color};">{len(overdue)}</div>
            <div class="metric-label">⚠️ Overdue</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #28a745;">{completed_count}</div>
            <div class="metric-label">✅ Tasks Completed</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📝 Your Task Queue")

    if not active_tasks:
        st.info("You're all caught up! Go to 'Add Task' to create new work.")
    else:
        for t in active_tasks:
            render_task_card(t)

# ==========================================
# ➕ VIEW 2: ADD TASK (Dedicated Page)
# ==========================================
def render_task_card(t):
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([0.5, 3, 1.5, 1])

        # Priority Icon
        icon = "🔴" if t['priority'] == 'high' else "🟡" if t['priority'] == 'medium' else "🟢"
        c1.markdown(f"## {icon}")

        # Details
        c2.markdown(f"**{t['name']}**")
        if t.get('notes'): c2.caption(t['notes'])

        # Meta
        c3.caption(f"⏱️ {t['duration_minutes']} min")
        c3.caption(f"📅 Due: {t['deadline'].strftime('%d %b')}")

        # SUPERVISOR FEATURE: Fast Forward Focus
        if c4.button("▶️ Focus", key=f"focus_{t['id']}"):
            run_focus_mode(t['name'])

        if c4.button("Done", key=f"done_{t['id']}"):
            mark_complete(t)

def run_focus_mode(task_name):
    """Simulates 1 hour of work in 10 seconds with motivational quotes."""
    progress_text = "Starting Focus Session..."
    my_bar = st.progress(0, text=progress_text)

    quotes = [
        "🔒 Locking in...",
        "🚀 You are making progress!",
        "🧠 Deep work mode activated...",
        "🔥 Don't stop now!",
        "✨ Almost there..."
    ]

    for percent_complete in range(100):
        time.sleep(0.05) # Speed of simulation
        my_bar.progress(percent_complete + 1, text=f"Focusing on: {task_name}")

        if percent_complete % 20 == 0:
            quote_idx = (percent_complete // 20) % len(quotes)
            st.toast(quotes[quote_idx], icon="💪")

    st.balloons()
    st.success(f"✅ Focus Session Complete: {task_name}")
    time.sleep(2)
    st.rerun()

def mark_complete(task):
    if 'completed' not in task: task['completed'] = True
    else: task['completed'] = True
    save_tasks(st.session_state.tasks)
    st.rerun()

def render_add_task():
    st.header("➕ Add New Assignment")
    st.caption("Break down your workload into manageable chunks.")

    with st.container(border=True):
        with st.form("add_task_form"):
            name = st.text_input("Task Name", placeholder="e.g. Write Literature Review")

            c1, c2 = st.columns(2)
            prio = c1.selectbox("Priority Level", ["High", "Medium", "Low"])
            module = c2.text_input("Module / Subject", placeholder="e.g. CS101")

            c3, c4 = st.columns(2)
            duration = c3.number_input("Est. Duration (mins)", 15, 300, 60, step=15)
            due = c4.date_input("Deadline", min_value=date.today())

            notes = st.text_area("Notes & Resources", placeholder="Paste links or requirements here...", height=100)

            if st.form_submit_button("Add to Queue", type="primary"):
                new_task = {
                    "id": str(int(time.time())), # Unique ID based on time
                    "name": name,
                    "duration_minutes": duration,
                    "priority": prio.lower(),
                    "deadline": due,
                    "notes": notes,
                    "module": module,
                    "completed": False,
                    "fixed_slot": None,
                    "start_time": None
                }
                st.session_state.tasks.append(new_task)
                save_tasks(st.session_state.tasks)
                st.success(f"Added '{name}' to your dashboard!")
                time.sleep(1)
                st.rerun()

# ==========================================
# 📅 VIEW 3: CALENDAR (With Export)
# ==========================================
def render_calendar():
    st.header("📅 Study Schedule")

    scheduled_tasks = [t for t in st.session_state.tasks if t.get('start_time') and not t.get('completed')]

    if not scheduled_tasks:
        st.warning("⚠️ No schedule generated yet. Go to 'AI Engine' to build your plan!")
        return

    # EXPORT BUTTON
    c1, c2 = st.columns([3, 1])
    with c2:
        ics_data = generate_ics_file(scheduled_tasks)
        st.download_button(
            label="📥 Export to Outlook (.ics)",
            data=ics_data,
            file_name="schedulesmart_plan.ics",
            mime="text/calendar",
            use_container_width=True
        )

    # CALENDAR RENDER
    calendar_events = []
    for t in scheduled_tasks:
        color = "#FF4B4B" if t['priority'] == 'high' else "#FFA500" if t['priority'] == 'medium' else "#3DD56D"

        # Safe conversion
        start_t = t['start_time']
        if isinstance(start_t, str): start_t = datetime.fromisoformat(start_t)

        end_t = t['end_time']
        if isinstance(end_t, str): end_t = datetime.fromisoformat(end_t)

        calendar_events.append({
            "title": t['name'],
            "start": start_t.isoformat(),
            "end": end_t.isoformat(),
            "backgroundColor": color,
            "borderColor": color
        })

    calendar_options = {
        "editable": False,
        "headerToolbar": {"left": "today prev,next", "center": "title", "right": "timeGridDay,timeGridWeek"},
        "initialView": "timeGridDay",
        "slotMinTime": "06:00:00",
        "slotMaxTime": "24:00:00",
        "height": 650,
    }
    calendar(events=calendar_events, options=calendar_options)

# ==========================================
# ⚙️ VIEW 4: AI ENGINE (Professional Modes)
# ==========================================
def render_engine():
    st.header("⚙️ Optimization Engine")

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown("### 1. Strategy")
        with st.container(border=True):
            # PROFESSIONAL MODES
            mode = st.selectbox(
                "Select Strategy",
                ["Balanced Revision ⚖️", "Exam Cram 📚", "Deadline Critical 🚨"]
            )

            if mode == "Exam Cram 📚":
                st.caption("⚠️ Compresses breaks, extends day to 10 PM.")
                def_start, def_end = 8, 22
            elif mode == "Deadline Critical 🚨":
                st.caption("⚠️ Prioritizes soonest deadlines over everything.")
                def_start, def_end = 9, 20
            else:
                st.caption("✅ Standard study hours with breaks.")
                def_start, def_end = 9, 17

            st.divider()

            start_h = st.slider("Start Day", 6, 12, def_start)
            end_h = st.slider("End Day", 14, 23, def_end)
            weekends = st.checkbox("Include Weekends", value=(mode == "Exam Cram 📚"))

    with c2:
        st.markdown("### 2. Execute")
        with st.container(border=True):
            st.info(f"Ready to generate schedule using **{mode}** logic.")

            if st.button("✨ Generate Optimized Schedule", type="primary", use_container_width=True):
                with st.spinner("Analyzing constraints & priorities..."):
                    # PREPARE DATA
                    task_objects = []
                    active_tasks = [t for t in st.session_state.tasks if not t.get('completed')]

                    for t in active_tasks:
                        prio_map = {"high": TaskPriority.HIGH, "medium": TaskPriority.MEDIUM, "low": TaskPriority.LOW}
                        dt_deadline = datetime.combine(t['deadline'], dt_time(23, 59))
                        task_objects.append(Task(
                            id=t['id'], name=t['name'], duration_minutes=t['duration_minutes'],
                            priority=prio_map[t['priority']], deadline=dt_deadline
                        ))

                    # RUN ENGINE
                    prefs = UserPreferences(start_time_hour=start_h, end_time_hour=end_h, include_weekends=weekends)
                    engine = ScheduleEngine()
                    result = engine.generate_schedule(task_objects, prefs)

                    # SAVE RESULTS
                    if result['status'] == 'success':
                        for scheduled_t in result['scheduled']:
                            for original_t in st.session_state.tasks:
                                if original_t['id'] == scheduled_t['id']:
                                    original_t['start_time'] = scheduled_t['start_time'].isoformat()
                                    original_t['end_time'] = scheduled_t['end_time'].isoformat()
                        save_tasks(st.session_state.tasks)
                        st.success("Optimization Complete! View the Calendar tab.")
                        st.balloons()
                    else:
                        st.error("Optimization Failed. Try extending your work hours.")

if __name__ == "__main__":
    main()