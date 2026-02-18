import sys
import time
import random
import pandas as pd
import matplotlib.pyplot as plt
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

# --- CSS STYLING ---
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
    html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }
    .stApp { background: linear-gradient(180deg, #F4F7FC 0%, #FFFFFF 100%); }
    
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        border: 1px solid #eef2f6;
        text-align: center;
    }
    .metric-value { font-size: 32px; font-weight: 700; color: #2D3748; }
    .metric-label { font-size: 13px; font-weight: 500; color: #718096; text-transform: uppercase; }
    
    .urgency-banner {
        background-color: #FED7D7; border: 1px solid #F56565; color: #C53030;
        padding: 10px; border-radius: 8px; margin-bottom: 20px; font-weight: 600; text-align: center;
    }
</style>
""", unsafe_allow_html=True)

def main():
    if "tasks" not in st.session_state:
        st.session_state.tasks = load_tasks()

    with st.sidebar:
        # --- LOGO LOGIC (Updated for .jpg) ---
        logo_path = Path(__file__).parent / "logo.jpg"
        if logo_path.exists():
            st.image(str(logo_path), width=180) # Your custom logo!
        else:
            st.warning("Logo not found. Make sure it is named 'logo.jpg'")
            st.image("https://cdn-icons-png.flaticon.com/512/3652/3652191.png", width=50) # Fallback

        st.markdown("### ScheduleSmart")
        st.caption("v4.5 | Professional Edition")

        selected = option_menu(
            menu_title=None,
            options=["Dashboard", "Add Task", "Calendar", "Study Plan AI"],
            icons=["house", "plus-square", "calendar-week", "cpu"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "nav-link": {"font-size": "15px", "text-align": "left", "margin": "8px"},
                "nav-link-selected": {"background-color": "#3182CE", "color": "white"},
            }
        )
        st.divider()

        # Pie Chart
        st.caption("📊 Work Breakdown")
        active_tasks = [t for t in st.session_state.tasks if not t.get('completed')]
        if active_tasks:
            df = pd.DataFrame(active_tasks)
            if 'module' in df.columns:
                fig, ax = plt.subplots(figsize=(2, 2))
                colors = ['#3182CE', '#805AD5', '#E53E3E', '#48BB78', '#ED8936']
                df['module'].value_counts().plot.pie(autopct='%1.0f%%', colors=colors, ax=ax, textprops={'fontsize': 8})
                ax.set_ylabel('')
                fig.patch.set_alpha(0)
                st.pyplot(fig, use_container_width=False)

    if selected == "Dashboard":
        render_dashboard()
    elif selected == "Add Task":
        render_add_task()
    elif selected == "Calendar":
        render_calendar()
    elif selected == "Study Plan AI":
        render_study_ai()

# ==========================================
# 🏠 VIEW 1: DASHBOARD
# ==========================================
def render_dashboard():
    st.title("👋 Welcome back")

    active_tasks = [t for t in st.session_state.tasks if not t.get('completed')]

    urgent_exams = [t for t in active_tasks if t.get('module') == 'Exam']
    if urgent_exams:
        st.markdown(f"""<div class="urgency-banner">🔥 HEADS UP: You have {len(urgent_exams)} upcoming Exam(s)!</div>""", unsafe_allow_html=True)

    if not st.session_state.tasks:
        st.info("Your schedule is empty.")
        if st.button("🚀 Load Sample Data (Demo)"):
            load_sample_data()
            st.rerun()
        return

    c1, c2, c3 = st.columns(3)
    today_str = date.today().isoformat()
    today_count = len([t for t in active_tasks if t['start_time'].startswith(today_str)])
    completed_count = len([t for t in st.session_state.tasks if t.get('completed')])

    with c1: st.markdown(f"""<div class="metric-card"><div class="metric-value">{today_count}</div><div class="metric-label">📅 Tasks Today</div></div>""", unsafe_allow_html=True)
    with c2: st.markdown(f"""<div class="metric-card"><div class="metric-value">{len(active_tasks)}</div><div class="metric-label">📂 Total Pending</div></div>""", unsafe_allow_html=True)
    with c3: st.markdown(f"""<div class="metric-card"><div class="metric-value" style="color: #48BB78;">{completed_count}</div><div class="metric-label">✅ Completed</div></div>""", unsafe_allow_html=True)

    st.markdown("### 📝 Up Next")
    sorted_tasks = sorted(active_tasks, key=lambda x: x['start_time'])
    for t in sorted_tasks:
        render_task_card(t)

def render_task_card(t):
    with st.expander(f"**{t['name']}** ({t.get('module', 'General')})"):
        st.caption(f"🕒 {t['start_time'][11:16]} - {t['end_time'][11:16]}")
        if t.get('notes'):
            st.info(f"📋 {t['notes']}")
        c1, c2 = st.columns([1, 4])
        if t['module'] not in ['Break', 'Gym']:
            if c1.button("▶️ Focus", key=f"f_{t['id']}"): run_focus_mode(t['name'])
        if c2.button("✅ Done", key=f"d_{t['id']}"): mark_complete(t)

def run_focus_mode(task_name):
    progress_text = "Entering Flow State..."
    my_bar = st.progress(0, text=progress_text)

    # --- UPGRADED COACH LOGIC ---
    messages = [
        "💧 Hydration Check! Have a sip of water.",
        "🪑 Posture Check! Sit up straight.",
        "🧠 Try to recall the key points without looking.",
        "↺ If you're stuck, go back over it one more time.",
        "🌬️ Take a deep breath. You got this.",
        "📝 Quick: Summarize what you just read.",
        "👀 Rest your eyes for 5 seconds.",
        "🚀 You are crushing this!",
        "🔥 Keep this momentum going.",
        "📵 Phone down, grades up.",
        "✨ One step at a time.",
        "💪 Knowledge is power."
    ]
    random.shuffle(messages)

    for percent_complete in range(100):
        time.sleep(0.04)
        my_bar.progress(percent_complete + 1, text=f"Focusing on: {task_name}")

        # Pop unique message every 15%
        if percent_complete % 15 == 0 and messages:
            msg = messages.pop()
            st.toast(msg, icon="💡")

    st.balloons()
    st.success(f"✅ Session Complete: {task_name}")
    time.sleep(1)

def mark_complete(task):
    task['completed'] = True
    save_tasks(st.session_state.tasks)
    st.rerun()

# ==========================================
# ➕ VIEW 2: ADD TASK
# ==========================================
def render_add_task():
    st.title("➕ Add to Calendar")

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Task", "🏫 Class", "🚨 Exam", "🏃 Personal"])

    # 1. TASK FORM
    with tab1:
        with st.form("form_task"):
            st.subheader("New Task / Assignment")
            c1, c2 = st.columns(2)
            name = c1.text_input("Title", placeholder="e.g. Essay Draft")
            subject = c2.text_input("Subject", placeholder="e.g. English")

            c3, c4 = st.columns(2)
            due_date = c3.date_input("Due Date")
            prio = c4.selectbox("Priority", ["High", "Medium", "Low"])

            st.markdown("**Do it when?**")
            d1, d2, d3 = st.columns(3)
            sched_date = d1.date_input("Work Date", value=date.today())
            start_t = d2.time_input("Start", value=dt_time(14,0))
            end_t = d3.time_input("End", value=dt_time(15,0))

            notes = st.text_area("Notes", placeholder="Requirements...", height=80)

            if st.form_submit_button("Add Task", type="primary"):
                create_task(name, "Self-Study", subject, sched_date, start_t, end_t, notes)

    # 2. CLASS FORM
    with tab2:
        with st.form("form_class"):
            st.subheader("New Class")
            c1, c2 = st.columns(2)
            subject = c1.text_input("Module Name", placeholder="e.g. CompSci 101")
            room = c2.text_input("Room / Building", placeholder="e.g. Room 304")
            teacher = st.text_input("Teacher", placeholder="e.g. Dr. Smith")

            d1, d2, d3 = st.columns(3)
            class_date = d1.date_input("First Date", value=date.today())
            start_t = d2.time_input("Start Time", value=dt_time(9,0))
            end_t = d3.time_input("End Time", value=dt_time(10,0))

            notes = st.text_area("Notes", placeholder="Class details...", height=80)
            repeat = st.checkbox("Repeat for 4 Weeks?")

            if st.form_submit_button("Add Class", type="primary"):
                n_str = f"Room: {room} | {notes}"
                weeks = 4 if repeat else 1
                for w in range(weeks):
                    actual_date = class_date + timedelta(weeks=w)
                    create_task(f"Class: {subject}", "Lecture", subject, actual_date, start_t, end_t, n_str)
                st.rerun()

    # 3. EXAM FORM
    with tab3:
        with st.form("form_exam"):
            st.subheader("Exam Entry")
            c1, c2 = st.columns(2)
            subject = c1.text_input("Exam Subject")
            seat = c2.text_input("Seat Number")

            d1, d2, d3 = st.columns(3)
            ex_date = d1.date_input("Exam Date")
            start_t = d2.time_input("Start", value=dt_time(9,0))
            end_t = d3.time_input("End", value=dt_time(11,0))

            notes = st.text_area("Notes", placeholder="Equipment list...", height=80)

            if st.form_submit_button("Add Exam", type="primary"):
                create_task(f"EXAM: {subject}", "Exam", subject, ex_date, start_t, end_t, f"Seat: {seat} | {notes}")

    # 4. PERSONAL FORM
    with tab4:
        with st.form("form_personal"):
            st.subheader("Personal Activity")
            name = st.text_input("Activity", placeholder="e.g. Gym")
            cat = st.selectbox("Type", ["Gym", "Break", "Other"])

            d1, d2, d3 = st.columns(3)
            p_date = d1.date_input("Date", value=date.today())
            start_t = d2.time_input("Start", value=dt_time(18,0))
            end_t = d3.time_input("End", value=dt_time(19,0))

            notes = st.text_area("Notes", placeholder="Details...", height=80)

            if st.form_submit_button("Add Activity", type="primary"):
                create_task(name, cat, "Personal", p_date, start_t, end_t, notes)

def create_task(name, module, cat_tag, day, t_start, t_end, notes):
    start_dt = datetime.combine(day, t_start)
    end_dt = datetime.combine(day, t_end)
    new_task = {
        "id": str(int(time.time()) + random.randint(1,1000)),
        "name": name,
        "priority": "medium",
        "module": module,
        "completed": False,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "notes": notes
    }
    st.session_state.tasks.append(new_task)
    save_tasks(st.session_state.tasks)
    st.success("Added to Calendar!")
    time.sleep(0.5)

# ==========================================
# 📅 VIEW 3: CALENDAR
# ==========================================
def render_calendar():
    st.title("📅 My Schedule")

    tasks = [t for t in st.session_state.tasks if not t.get('completed')]
    if tasks:
        ics = generate_ics_file(tasks)
        st.download_button("📥 Sync Outlook", ics, "cal.ics", "text/calendar")

    cat_colors = {
        "Lecture": "#3182CE", "Self-Study": "#805AD5", "Exam": "#E53E3E",
        "Gym": "#48BB78", "Break": "#A0AEC0", "Other": "#DD6B20"
    }

    events = []
    for t in tasks:
        try:
            cat = t.get('module', 'Other')
            color = cat_colors.get(cat, "#3182CE")
            events.append({
                "id": t['id'],
                "title": t['name'],
                "start": t['start_time'],
                "end": t['end_time'],
                "backgroundColor": color,
                "borderColor": color,
                "extendedProps": {"notes": t.get('notes', '')}
            })
        except: pass

    calendar_options = {
        "editable": True,
        "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,timeGridWeek"},
        "initialView": "timeGridWeek",
        "slotMinTime": "06:00:00",
        "slotMaxTime": "23:00:00",
        "height": 700,
    }

    cal_data = calendar(events=events, options=calendar_options, callbacks=['eventClick'])

    if cal_data and "eventClick" in cal_data:
        event_id = cal_data["eventClick"]["event"]["id"]
        task_to_edit = next((t for t in st.session_state.tasks if t['id'] == event_id), None)
        if task_to_edit:
            edit_dialog(task_to_edit)

@st.dialog("✏️ Edit Event")
def edit_dialog(task):
    st.caption("Change details or remove this event.")
    with st.form("edit_calendar_form"):
        new_name = st.text_input("Name", value=task['name'])
        new_notes = st.text_area("Notes", value=task.get('notes', ''))

        try:
            s_dt = datetime.fromisoformat(task['start_time'])
            e_dt = datetime.fromisoformat(task['end_time'])
        except:
            s_dt = datetime.now()
            e_dt = datetime.now() + timedelta(hours=1)

        c1, c2 = st.columns(2)
        new_start = c1.time_input("Start", value=s_dt.time())
        new_end = c2.time_input("End", value=e_dt.time())

        c3, c4 = st.columns(2)
        if c3.form_submit_button("💾 Save Changes", type="primary"):
            task['name'] = new_name
            task['notes'] = new_notes
            task['start_time'] = datetime.combine(s_dt.date(), new_start).isoformat()
            task['end_time'] = datetime.combine(s_dt.date(), new_end).isoformat()
            save_tasks(st.session_state.tasks)
            st.rerun()

        if c4.form_submit_button("🗑️ Delete Event", type="secondary"):
            st.session_state.tasks.remove(task)
            save_tasks(st.session_state.tasks)
            st.rerun()

# ==========================================
# 🤖 VIEW 4: AI PLANNER
# ==========================================
def render_study_ai():
    st.title("🤖 Intelligent Planner")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.container(border=True):
            goal = st.text_input("Goal", placeholder="e.g. Master Calculus")
            d1, d2 = st.columns(2)
            start_d = d1.date_input("Start", value=date.today())
            end_d = d2.date_input("End", value=date.today() + timedelta(days=5))
            intensity = st.select_slider("Intensity", ["Light", "Balanced", "Intense"])
            rhythm = st.selectbox("Rhythm", ["Morning Lark 🐦", "Balanced ⚖️", "Night Owl 🦉"])

    with c2:
        if st.button("✨ Generate Plan", type="primary", use_container_width=True):
            if goal:
                with st.spinner("Simulating..."):
                    generate_stochastic_plan(goal, start_d, end_d, intensity, rhythm)
                    st.success("Plan generated!")
                    st.balloons()

def generate_stochastic_plan(goal, start_d, end_d, intensity, rhythm):
    verbs = ["📖 Read", "✍️ Practice", "📺 Watch", "⚡ Quiz"]
    if intensity == "Light": hrs = [1, 2]
    elif intensity == "Balanced": hrs = [2, 3, 4]
    else: hrs = [4, 5, 6]

    if "Morning" in rhythm: start_r = [7, 8, 9]
    elif "Night" in rhythm: start_r = [14, 15, 16]
    else: start_r = [9, 10, 11]

    curr = start_d
    while curr <= end_d:
        s_hr = random.choice(start_r)
        curr_t = datetime.combine(curr, dt_time(s_hr, 0))
        d_hrs = random.choice(hrs)
        for i in range(d_hrs):
            verb = random.choice(verbs)
            name = f"{verb}: {goal}"
            end_t = curr_t + timedelta(minutes=50)
            st.session_state.tasks.append({
                "id": str(int(time.time()) + random.randint(1,9999)),
                "name": name, "module": "Self-Study", "priority": "high", "completed": False,
                "start_time": curr_t.isoformat(), "end_time": end_t.isoformat(), "notes": "AI Gen"
            })
            curr_t = end_t + timedelta(minutes=10)
        curr += timedelta(days=1)
    save_tasks(st.session_state.tasks)

def load_sample_data():
    today = date.today()
    sample = [
        {"name": "🏃‍♂️ Morning Run", "cat": "Gym", "s": "07:00", "e": "08:00"},
        {"name": "📘 CS101 Lecture", "cat": "Lecture", "s": "09:00", "e": "11:00"},
        {"name": "🥗 Lunch", "cat": "Break", "s": "12:00", "e": "13:00"},
        {"name": "💻 Python Lab", "cat": "Self-Study", "s": "14:00", "e": "16:00"},
    ]
    for s in sample:
        s_dt = datetime.combine(today, datetime.strptime(s['s'], "%H:%M").time())
        e_dt = datetime.combine(today, datetime.strptime(s['e'], "%H:%M").time())
        st.session_state.tasks.append({
            "id": str(int(time.time()) + random.randint(1,999)),
            "name": s['name'], "module": s['cat'], "completed": False,
            "start_time": s_dt.isoformat(), "end_time": e_dt.isoformat(), "notes": "Demo"
        })
    save_tasks(st.session_state.tasks)

if __name__ == "__main__":
    main()