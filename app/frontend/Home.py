import sys
import time
import random
from pathlib import Path
from datetime import date, datetime, time as dt_time, timedelta

# --- MAGIC PATH FIX ---
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar

# Backend Imports
from app.backend.data_service import load_tasks, save_tasks
from app.backend.export_service import generate_ics_file

# --- PAGE CONFIG ---
st.set_page_config(page_title="ScheduleSmart Pro", page_icon="🎓", layout="wide")

# --- PROFESSIONAL CSS ---
st.markdown("""
<style>
    /* Hide default sidebar nav */
    [data-testid="stSidebarNav"] {display: none;}
    
    /* SaaS Gradient Background */
    .stApp {
        background: linear-gradient(180deg, #F0F2F6 0%, #FFFFFF 100%);
    }

    /* Metric Card Styling */
    .metric-card {
        background-color: rgba(255, 255, 255, 0.9);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid #eee;
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
    
    /* Clean Fonts */
    h1, h2, h3 { font-family: 'Inter', 'Helvetica Neue', sans-serif; }
    
    /* Card Container */
    .stContainer { border-radius: 12px; border: 1px solid #f0f0f0; }
    
    /* Bold Expander Text */
    div[data-testid="stExpander"] details summary p {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # 1. Load Data
    if "tasks" not in st.session_state:
        st.session_state.tasks = load_tasks()

    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.title("🎓 ScheduleSmart")
        st.caption("v3.1 | Intelligent Planner")

        selected = option_menu(
            menu_title=None,
            options=["Dashboard", "Add Task", "Calendar", "Study Plan AI"],
            icons=["house", "plus-circle", "calendar-event", "robot"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "nav-link": {"font-size": "14px", "text-align": "left", "margin": "5px", "--hover-color": "#e0e0e0"},
                "nav-link-selected": {"background-color": "#FF4B4B"},
            }
        )
        st.divider()

    # --- ROUTING ---
    if selected == "Dashboard":
        render_dashboard()
    elif selected == "Add Task":
        render_add_task()
    elif selected == "Calendar":
        render_calendar()
    elif selected == "Study Plan AI":
        render_study_ai()

# ==========================================
# 🏠 VIEW 1: THE DASHBOARD
# ==========================================
def render_dashboard():
    st.header("👋 My Dashboard")

    active_tasks = [t for t in st.session_state.tasks if not t.get('completed')]
    today_tasks = [t for t in active_tasks if t['deadline'] == date.today()]

    # Daily Momentum Bar
    if today_tasks:
        completed_today = len([t for t in st.session_state.tasks if t.get('completed') and t['deadline'] == date.today()])
        total_today = len(today_tasks) + completed_today
        progress = completed_today / total_today if total_today > 0 else 0
        st.progress(progress, text=f"Daily Momentum: {int(progress*100)}%")
    else:
        st.info("No deadlines for today. You are free! 🎉")

    # Metrics
    c1, c2, c3 = st.columns(3)

    overdue = [t for t in active_tasks if t['deadline'] < date.today()]
    completed_all = len([t for t in st.session_state.tasks if t.get('completed')])

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
            <div class="metric-value" style="color: #28a745;">{completed_all}</div>
            <div class="metric-label">✅ Lifetime Completed</div>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("📝 Your Queue")

    if not active_tasks:
        st.success("All caught up! Go to 'Add Task' or 'Study Plan AI'.")
    else:
        for t in active_tasks:
            render_task_card(t)

# ==========================================
# 🧩 HELPER: TASK CARD
# ==========================================
def render_task_card(t):
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([0.5, 3, 1.5, 1])

        # Priority Icon
        icon = "🔴" if t['priority'] == 'high' else "🟡" if t['priority'] == 'medium' else "🟢"
        c1.markdown(f"## {icon}")

        # Details
        c2.markdown(f"**{t['name']}**")
        if t.get('module'):
            c2.caption(f"📘 {t['module']}")

        # Meta
        c3.caption(f"⏱️ {t['duration_minutes']} min")
        c3.caption(f"📅 Due: {t['deadline'].strftime('%d %b')}")

        # Focus Button
        if c4.button("▶️ Focus", key=f"focus_{t['id']}"):
            run_focus_mode(t['name'])

        # Done Button
        if c4.button("Done", key=f"done_{t['id']}"):
            mark_complete(t)

# ==========================================
# 🧘 HELPER: FOCUS MODE
# ==========================================
def run_focus_mode(task_name):
    progress_text = "Entering Flow State..."
    my_bar = st.progress(0, text=progress_text)

    quotes = [
        "💧 Hydration Check! Take a sip of water.",
        "🪑 Posture Check! Sit up straight.",
        "🧠 Locking in...",
        "🚀 You are crushing this!",
        "👀 Eyes on the prize.",
        "🔥 Keep the momentum going.",
        "✨ One step at a time.",
        "🛑 Put the phone away.",
        "💪 You got this!",
        "🌬️ Take a deep breath.",
        "📚 Knowledge is power.",
        "⚡ Laser focus activated."
    ]

    for percent_complete in range(100):
        time.sleep(0.05)
        my_bar.progress(percent_complete + 1, text=f"Focusing on: {task_name}")

        if percent_complete % 15 == 0:
            st.toast(random.choice(quotes), icon=random.choice(["💧", "🪑", "🚀", "🔥", "✨", "💪"]))

    st.balloons()
    st.success(f"✅ Session Complete: {task_name}")
    time.sleep(2)
    st.rerun()

def mark_complete(task):
    task['completed'] = True
    save_tasks(st.session_state.tasks)
    st.rerun()

# ==========================================
# ➕ VIEW 2: ADD TASK (With Future Scheduling)
# ==========================================
def render_add_task():
    st.header("➕ Add New Assignment")

    with st.container(border=True):
        with st.form("add_task_form"):
            name = st.text_input("Task Name", placeholder="e.g. Write Literature Review")

            c1, c2 = st.columns(2)
            prio = c1.selectbox("Priority Level", ["High", "Medium", "Low"])
            module = c2.text_input("Module / Subject", placeholder="e.g. Computer Science")

            c3, c4 = st.columns(2)
            duration = c3.number_input("Est. Duration (mins)", 15, 300, 60, step=15)
            due = c4.date_input("Deadline", min_value=date.today())

            st.markdown("---")
            st.markdown("**Optional: Schedule It Now**")

            c_date, c_start, c_end = st.columns(3)
            sched_date = c_date.date_input("Scheduled Date", value=date.today())
            manual_start = c_start.time_input("Start Time (Optional)", value=None)
            manual_end = c_end.time_input("End Time (Optional)", value=None)

            notes = st.text_area("Notes", placeholder="Requirements...", height=100)

            if st.form_submit_button("Add to Queue", type="primary"):
                final_start = None
                final_end = None

                # Logic: If times are picked, create the ISO strings
                if manual_start and manual_end:
                    final_start = datetime.combine(sched_date, manual_start).isoformat()
                    final_end = datetime.combine(sched_date, manual_end).isoformat()

                    # Basic Conflict Check
                    for t in st.session_state.tasks:
                        if t.get('start_time') and not t.get('completed'):
                            # Safely handle string vs datetime
                            existing_start = t['start_time']
                            if isinstance(existing_start, str): existing_start = datetime.fromisoformat(existing_start)

                            existing_end = t['end_time']
                            if isinstance(existing_end, str): existing_end = datetime.fromisoformat(existing_end)

                            new_s = datetime.fromisoformat(final_start)

                            if existing_start <= new_s < existing_end:
                                st.warning(f"⚠️ Warning: Overlaps with '{t['name']}'")

                new_task = {
                    "id": str(int(time.time())),
                    "name": name,
                    "duration_minutes": duration,
                    "priority": prio.lower(),
                    "deadline": due,
                    "notes": notes,
                    "module": module,
                    "completed": False,
                    "start_time": final_start,
                    "end_time": final_end
                }
                st.session_state.tasks.append(new_task)
                save_tasks(st.session_state.tasks)
                st.success(f"Added '{name}' successfully!")
                time.sleep(1)
                st.rerun()

# ==========================================
# 📅 VIEW 3: CALENDAR (FIXED!)
# ==========================================
def render_calendar():
    st.header("📅 Study Schedule")

    scheduled_tasks = [t for t in st.session_state.tasks if t.get('start_time') and not t.get('completed')]

    if not scheduled_tasks:
        st.warning("⚠️ No schedule generated yet.")
        return

    # Export Button
    c1, c2 = st.columns([3, 1])
    with c2:
        ics_data = generate_ics_file(scheduled_tasks)
        st.download_button(
            label="📥 Export to Outlook",
            data=ics_data,
            file_name="plan.ics",
            mime="text/calendar",
            use_container_width=True
        )

    # Color Map
    module_colors = {
        "Math": "#3788d8", "CS": "#7b1fa2", "History": "#d84315",
        "Biology": "#2e7d32", "Break": "#607d8b", "General": "#1f77b4"
    }

    calendar_events = []
    for t in scheduled_tasks:
        mod = t.get('module', 'General')
        color = module_colors.get(mod, "#1f77b4")
        if t['name'] == "☕ Smart Break": color = "#9e9e9e"

        # --- FIX IS HERE: Robust Date Handling ---
        # Checks if it's ALREADY a datetime object. If so, uses it. If string, converts it.
        start_raw = t['start_time']
        if isinstance(start_raw, str):
            start_t = datetime.fromisoformat(start_raw)
        else:
            start_t = start_raw

        end_raw = t['end_time']
        if isinstance(end_raw, str):
            end_t = datetime.fromisoformat(end_raw)
        else:
            end_t = end_raw
        # -----------------------------------------

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
# 🤖 VIEW 4: AI STUDY PLANNER (With Date Ranges)
# ==========================================
def render_study_ai():
    st.header("🤖 AI Study Plan Generator")

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown("### 1. Define Goal")
        with st.container(border=True):
            goal = st.text_input("What do you want to learn?", placeholder="e.g. Python Basics")

            d1, d2 = st.columns(2)
            start_d = d1.date_input("Start Date", value=date.today())
            end_d = d2.date_input("End Date", value=date.today() + timedelta(days=5))

            rhythm = st.selectbox("Study Rhythm", ["9-to-5 Mode 🏢", "Night Owl 🌙", "All Day Grind 🔥"])
            smart_breaks = st.checkbox("Add Smart Breaks? ☕", value=True)

    with c2:
        st.markdown("### 2. Generate Plan")
        with st.container(border=True):
            if st.button("✨ Generate Study Plan", type="primary", use_container_width=True):
                if not goal:
                    st.error("Please enter a learning goal first.")
                else:
                    with st.spinner(f"Breaking down '{goal}' into a { (end_d - start_d).days + 1 } day plan..."):
                        generate_ai_plan(goal, start_d, end_d, rhythm, smart_breaks)
                        st.balloons()
                        st.success("Plan Generated! Check the Calendar.")

def generate_ai_plan(goal, start_date, end_date, rhythm, smart_breaks):
    total_days = (end_date - start_date).days + 1
    if total_days < 1: total_days = 1

    base_tasks = [
        f"Review {goal} Syllabus", f"Watch {goal} Intro", f"Read Chapter 1",
        f"Practice Set A", f"Read Chapter 2", f"Practice Set B",
        f"Mid-Topic Review", f"Solve Past Papers", f"Final Mock Exam"
    ]

    start_hour = 9
    if "Night Owl" in rhythm: start_hour = 18
    if "All Day" in rhythm: start_hour = 8

    # Distribute tasks across days
    tasks_per_day = max(1, len(base_tasks) // total_days)

    task_idx = 0
    for day_offset in range(total_days):
        current_date = start_date + timedelta(days=day_offset)
        current_time = datetime.combine(current_date, dt_time(start_hour, 0))

        # Schedule tasks for this day
        for _ in range(tasks_per_day):
            if task_idx >= len(base_tasks): break

            task_name = base_tasks[task_idx]
            end_time = current_time + timedelta(minutes=60)

            new_task = {
                "id": str(int(time.time()) + task_idx),
                "name": task_name,
                "duration_minutes": 60,
                "priority": "high" if task_idx % 2 == 0 else "medium",
                "deadline": end_date,
                "notes": "Generated by AI",
                "module": goal,
                "completed": False,
                "start_time": current_time.isoformat(),
                "end_time": end_time.isoformat()
            }
            st.session_state.tasks.append(new_task)
            current_time = end_time
            task_idx += 1

            if smart_breaks:
                break_end = current_time + timedelta(minutes=15)
                break_task = {
                    "id": str(int(time.time()) + 500 + task_idx),
                    "name": "☕ Smart Break",
                    "duration_minutes": 15,
                    "priority": "low",
                    "deadline": end_date,
                    "module": "Break",
                    "completed": False,
                    "start_time": current_time.isoformat(),
                    "end_time": break_end.isoformat()
                }
                st.session_state.tasks.append(break_task)
                current_time = break_end

    save_tasks(st.session_state.tasks)

if __name__ == "__main__":
    main()