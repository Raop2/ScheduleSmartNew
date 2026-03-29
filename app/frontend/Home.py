import sys
import os
import time
import uuid
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, datetime, timedelta, time as dt_time
from pathlib import Path

# --- Path Setup ---
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar

# --- Backend Imports ---
from app.backend.database import get_connection, init_db, get_streak, mark_task_completed, bulk_update_schedule
from app.backend.motivator import get_greeting, get_hype_message, get_streak_message, get_recovery_message, get_smart_suggestion, get_focus_tip
from app.backend.greedy_scheduler import generate_greedy_schedule
from app.backend.cpsat_scheduler import generate_cpsat_schedule
from app.backend.explanation import generate_schedule_summary, compare_explanations
from app.backend.export_service import generate_ics_file

# --- Page Config & CSS ---
st.set_page_config(page_title="ScheduleSmart V2", page_icon=":material/calendar_month:", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
    html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }
    .stApp { background-color: #F8FAFC; color: #1E293B; }
    
    .metric-card {
        background-color: #FFFFFF; border-radius: 20px; padding: 24px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.03); border: 1px solid #F1F5F9; text-align: center;
        transition: transform 0.2s ease-in-out;
    }
    .metric-card:hover { transform: translateY(-4px); box-shadow: 0 15px 30px rgba(0, 0, 0, 0.05); }
    .metric-value { font-size: 42px; font-weight: 800; color: #0F172A; margin-bottom: 4px; letter-spacing: -1px; }
    .metric-label { font-size: 13px; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 1.5px; }
    
    .streak-banner { background: linear-gradient(135deg, #A78BFA 0%, #C4B5FD 100%); color: #4C1D95; padding: 16px; border-radius: 16px; margin-bottom: 24px; font-weight: 800; text-align: center; text-transform: uppercase; box-shadow: 0 4px 12px rgba(167, 139, 250, 0.2); }
    .recovery-banner { background-color: #FECACA; color: #7F1D1D; padding: 16px; border-radius: 16px; margin-bottom: 24px; font-weight: 700; text-align: center; }
    .suggestion-box { background-color: #FFFFFF; border-left: 4px solid #3B82F6; padding: 20px; border-radius: 12px; margin-top: 24px; color: #334155; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }
    
    div[data-testid="stExpander"] { background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important; border-radius: 12px !important; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
    
    .fc { background-color: #FFFFFF; padding: 24px; border-radius: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.04); border: none; font-family: 'Inter', sans-serif; }
    .fc-theme-standard td, .fc-theme-standard th { border-color: #F1F5F9 !important; }
    .fc-col-header-cell { padding: 12px 0 !important; border-bottom: 2px solid #F1F5F9 !important; }
    .fc-col-header-cell-cushion { color: #475569 !important; font-weight: 600 !important; }
    .fc-timegrid-axis-cushion { color: #94A3B8 !important; font-size: 12px !important; }
    .fc-header-toolbar { margin-bottom: 24px !important; }
    .fc-toolbar-title { color: #0F172A !important; font-weight: 800 !important; font-size: 1.5em !important; }
    
    .fc-button-primary { 
        background-color: #FFFFFF !important; color: #475569 !important; 
        border: 1px solid #E2E8F0 !important; border-radius: 20px !important; 
        text-transform: capitalize !important; font-weight: 600 !important; box-shadow: none !important; 
        padding: 8px 16px !important; transition: all 0.2s !important;
    }
    .fc-button-primary:hover { background-color: #F8FAFC !important; border-color: #CBD5E1 !important; }
    .fc-button-active { background-color: #0F172A !important; color: #FFFFFF !important; border-color: #0F172A !important; }
    
    .fc-event { 
        border-radius: 8px !important; border: none !important; padding: 4px 6px !important; 
        font-weight: 600 !important; font-size: 0.85em !important; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important; cursor: pointer;
        transition: transform 0.1s;
    }
    .fc-event-main {
        white-space: normal !important; 
        word-wrap: break-word !important;
        line-height: 1.2 !important;
    }
    .fc-event:hover { transform: scale(1.02); }
    .fc-timegrid-slot { height: 4.5em !important; } 
    .fc-day-today { background-color: #F8FAFC !important; } 
</style>
""", unsafe_allow_html=True)

def main():
    init_db()

    with st.sidebar:
        logo_path = Path(__file__).parent / "logo.jpg"
        if logo_path.exists(): st.image(str(logo_path), width=180)

        st.markdown("<h3 style='color: #0F172A; font-weight: 800;'>ScheduleSmart V2</h3>", unsafe_allow_html=True)
        st.caption(datetime.now().strftime("%A, %d %B %Y"))

        selected = option_menu(
            menu_title=None,
            options=["Dashboard", "Add Task", "Schedule Generator", "Calendar", "Focus Mode", "Stats", "Settings"],
            icons=["house", "plus-square", "cpu", "calendar-week", "play-circle", "bar-chart", "gear"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#64748B", "font-size": "18px"},
                "nav-link": {"font-size": "15px", "text-align": "left", "margin": "8px", "color": "#475569", "font-weight": "600", "border-radius": "12px"},
                "nav-link-selected": {"background-color": "#EFF6FF", "color": "#2563EB", "font-weight": "800"},
            }
        )

        streak_count = get_streak()
        if streak_count > 0:
            st.markdown("---")
            st.markdown(f"<div style='text-align: center;'><h1 style='color: #8B5CF6; margin: 0; font-size: 48px;'>🔥 {streak_count}</h1><p style='color: #64748B; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;'>Day Streak</p></div>", unsafe_allow_html=True)

    if selected == "Dashboard": render_dashboard()
    elif selected == "Add Task": render_add_task()
    elif selected == "Schedule Generator": render_schedule_generator()
    elif selected == "Calendar": render_calendar()
    elif selected == "Focus Mode": render_focus_mode()
    elif selected == "Stats": render_stats()
    elif selected == "Settings": render_settings()

# ==========================================
# HELPER FUNCTIONS (Moved to top to prevent NameErrors)
# ==========================================
def insert_task(name, mod, prio, dur, dead, pref, fix, st_t, en_t, note):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (id, name, module, priority, duration, deadline, preferred_time, is_fixed, start_time, end_time, completed, notes) VALUES (?,?,?,?,?,?,?,?,?,?,0,?)",
              (str(uuid.uuid4()), name, mod, prio, dur, dead, pref, fix, st_t, en_t, note))
    conn.commit()
    conn.close()

def apply_schedule_with_breaks(scheduled_tasks, break_mins):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE module = 'Break'")

    for task in scheduled_tasks:
        if task.get('start_time'):
            c.execute("UPDATE tasks SET start_time = ?, end_time = ? WHERE id = ?", (task['start_time'], task['end_time'], task['id']))
            if not task.get('is_fixed') and break_mins > 0:
                end_time = datetime.fromisoformat(task['end_time'])
                break_end = end_time + timedelta(minutes=break_mins)
                c.execute("INSERT INTO tasks (id, name, module, priority, duration, is_fixed, start_time, end_time, completed) VALUES (?,?,?,?,?,?,?,?,0)",
                          (str(uuid.uuid4()), "Break", "Break", "Low", break_mins, 1, end_time.isoformat(), break_end.isoformat()))

    conn.commit()
    conn.close()

# ==========================================
# VIEW 1: DASHBOARD
# ==========================================
def render_dashboard():
    st.markdown(f"<h1 style='color: #0F172A;'>{get_greeting()}</h1>", unsafe_allow_html=True)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND module != 'Break'")
    pending_tasks = [dict(row) for row in cursor.fetchall()]

    today_str = date.today().isoformat()
    cursor.execute("SELECT COUNT(*) as count FROM completion_log WHERE completion_date = ?", (today_str,))
    completed_today = cursor.fetchone()['count']
    conn.close()

    streak_count = get_streak()
    if streak_count >= 3:
        st.markdown(f"<div class='streak-banner'>🔥 {get_streak_message(streak_count)}</div>", unsafe_allow_html=True)

    overdue_tasks = [t for t in pending_tasks if t['deadline'] and t['deadline'] < today_str]
    if overdue_tasks:
        st.markdown(f"<div class='recovery-banner'>⚠️ You have {len(overdue_tasks)} overdue tasks. {get_recovery_message()}</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    today_due = len([t for t in pending_tasks if t['deadline'] == today_str or (t['start_time'] and t['start_time'].startswith(today_str))])

    with c1: st.markdown(f"<div class='metric-card'><div class='metric-value'>{today_due}</div><div class='metric-label'>Due Today</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(pending_tasks)}</div><div class='metric-label'>Pending</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><div class='metric-value'>{completed_today}</div><div class='metric-label'>Done Today</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><div class='metric-value'>{streak_count}</div><div class='metric-label'>Day Streak</div></div>", unsafe_allow_html=True)

    st.markdown("<br><h3 style='color: #0F172A;'>Up Next</h3>", unsafe_allow_html=True)
    if not pending_tasks:
        st.success("Your schedule is completely clear. Great job.")
    else:
        sorted_tasks = sorted(pending_tasks, key=lambda x: (x['start_time'] or x['deadline'] or '9999-12-31'))
        for t in sorted_tasks[:5]:
            with st.expander(f"{t['name']} ({t['module']})"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    if t['start_time']: st.caption(f":material/schedule: Scheduled: {t['start_time'][11:16]}")
                    if t['deadline']:
                        uk_deadline = datetime.fromisoformat(t['deadline']).strftime('%d/%m/%Y')
                        st.caption(f":material/event: Deadline: {uk_deadline}")
                    if t['notes']: st.info(t['notes'])
                with col2:
                    if st.button(":material/check_circle: Complete", key=f"d_{t['id']}", use_container_width=True):
                        mark_task_completed(t['id'], t['module'], t['duration'])
                        st.toast(get_hype_message())
                        time.sleep(1)
                        st.rerun()

    st.markdown(f"<div class='suggestion-box'>💡 <strong>Smart Suggestion:</strong> {get_smart_suggestion()}</div>", unsafe_allow_html=True)

# ==========================================
# VIEW 2: ADD TASK
# ==========================================
def render_add_task():
    st.markdown("<h1 style='color: #0F172A;'>Add to Planner</h1>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs([":material/assignment: Assignment", ":material/school: Class", ":material/history_edu: Exam", ":material/directions_run: Personal"])

    with tab1:
        st.subheader("New Assignment / Study Goal")
        mode = st.radio("Scheduling Method", ["Manual Time (Add to Calendar Now)", "Auto-Schedule (Let AI decide)"], horizontal=True)

        with st.form("form_assignment"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Title", placeholder="e.g., Physics Problem Set")
            module = c2.text_input("Module", placeholder="e.g., Physics 101")

            c3, c4 = st.columns(2)
            priority = c3.selectbox("Priority", ["High", "Medium", "Low"])

            if "Manual" in mode:
                d1, d2, d3 = st.columns(3)
                work_date = d1.date_input("Work Date", format="DD/MM/YYYY")
                start_t = d2.time_input("Start Time", value=dt_time(13, 0))
                end_t = d3.time_input("End Time", value=dt_time(14, 0))
            else:
                duration = c4.number_input("Total Duration (mins)", min_value=15, value=120, step=15, help="If >90 mins, AI will automatically split this into multiple blocks!")
                d1, d2 = st.columns(2)
                deadline = d1.date_input("Deadline", format="DD/MM/YYYY")
                pref_time = d2.selectbox("Preferred Time", ["Any", "Morning", "Afternoon", "Evening"])

            notes = st.text_area("Notes")

            if st.form_submit_button("Add to Calendar", type="primary"):
                if "Manual" in mode:
                    dur = int((datetime.combine(date.today(), end_t) - datetime.combine(date.today(), start_t)).total_seconds() / 60)
                    st_str = datetime.combine(work_date, start_t).isoformat()
                    en_str = datetime.combine(work_date, end_t).isoformat()
                    insert_task(name, module, priority, dur, None, "Any", 1, st_str, en_str, notes)
                    st.success("Assignment added to planner.")
                else:
                    if duration > 90:
                        chunks = duration // 60
                        rem = duration % 60
                        for i in range(chunks):
                            insert_task(f"{name} (Pt {i+1})", module, priority, 60, deadline.isoformat(), pref_time, 0, None, None, notes)
                        if rem > 0:
                            insert_task(f"{name} (Pt {chunks+1})", module, priority, rem, deadline.isoformat(), pref_time, 0, None, None, notes)
                        st.success(f"Task automatically split into {chunks + (1 if rem>0 else 0)} blocks for optimal AI spaced-scheduling.")
                    else:
                        insert_task(name, module, priority, duration, deadline.isoformat(), pref_time, 0, None, None, notes)
                        st.success("Assignment saved for AI scheduling.")

    with tab2:
        with st.form("form_class"):
            st.subheader("Fixed Class")
            c1, c2 = st.columns(2)
            module = c1.text_input("Module Name")
            room = c2.text_input("Room")
            d1, d2, d3 = st.columns(3)
            class_date = d1.date_input("Date", format="DD/MM/YYYY")
            start_t = d2.time_input("Start Time", value=dt_time(13, 0))
            end_t = d3.time_input("End Time", value=dt_time(14, 0))
            repeat = st.checkbox("Repeat weekly for 4 weeks")
            if st.form_submit_button("Add to Calendar", type="primary"):
                dur = int((datetime.combine(date.today(), end_t) - datetime.combine(date.today(), start_t)).total_seconds() / 60)
                for w in range(4 if repeat else 1):
                    act_date = class_date + timedelta(weeks=w)
                    st_str = datetime.combine(act_date, start_t).isoformat()
                    en_str = datetime.combine(act_date, end_t).isoformat()
                    insert_task(f"Class: {module}", module, "High", dur, None, "Any", 1, st_str, en_str, room)
                st.success("Class saved.")

    with tab3:
        with st.form("form_exam"):
            st.subheader("Exam Entry")
            c1, c2 = st.columns(2)
            module = c1.text_input("Subject")
            seat = c2.text_input("Seat")
            d1, d2, d3 = st.columns(3)
            ex_date = d1.date_input("Date", format="DD/MM/YYYY")
            start_t = d2.time_input("Start Time", value=dt_time(13, 0))
            end_t = d3.time_input("End Time", value=dt_time(14, 0))
            if st.form_submit_button("Add to Calendar", type="primary"):
                dur = int((datetime.combine(date.today(), end_t) - datetime.combine(date.today(), start_t)).total_seconds() / 60)
                st_str = datetime.combine(ex_date, start_t).isoformat()
                en_str = datetime.combine(ex_date, end_t).isoformat()
                insert_task(f"EXAM: {module}", module, "High", dur, ex_date.isoformat(), "Any", 1, st_str, en_str, seat)
                st.success("Exam saved.")

    with tab4:
        with st.form("form_personal"):
            st.subheader("Personal Activity")
            name = st.text_input("Activity")
            c1, c2 = st.columns(2)
            duration = c1.number_input("Duration", value=60)
            is_fixed = c2.checkbox("Fixed Time?")
            if is_fixed:
                d1, d2, d3 = st.columns(3)
                p_date = d1.date_input("Date", format="DD/MM/YYYY")
                start_t = d2.time_input("Start Time", value=dt_time(13, 0))
                end_t = d3.time_input("End Time", value=dt_time(14, 0))
                pref_time = "Any"
            else:
                pref_time = st.selectbox("Preferred Time", ["Any", "Morning", "Afternoon", "Evening"])
            if st.form_submit_button("Add to Calendar", type="primary"):
                if is_fixed:
                    st_str = datetime.combine(p_date, start_t).isoformat()
                    en_str = datetime.combine(p_date, end_t).isoformat()
                    insert_task(name, "Personal", "Low", duration, None, "Any", 1, st_str, en_str, "")
                else:
                    insert_task(name, "Personal", "Low", duration, None, pref_time, 0, None, None, "")
                st.success("Activity saved.")

# ==========================================
# VIEW 3: SCHEDULE GENERATOR
# ==========================================
def render_schedule_generator():
    st.markdown("<h1 style='color: #0F172A;'>AI Schedule Engine</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; font-size: 16px; margin-bottom: 20px;'>What do you want to learn? Type a goal and the AI will build a daily habit schedule.</p>", unsafe_allow_html=True)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_preferences")
    prefs = {row['key']: int(row['value']) for row in cursor.fetchall()}
    conn.close()

    day_start = prefs.get('day_start', 8)
    day_end = prefs.get('day_end', 22)
    max_hrs = prefs.get('max_hours', 6)
    b_mins = prefs.get('break_mins', 15)

    goal_input = st.text_input("Goal", placeholder="e.g. Master Python, Calculus Revision...", label_visibility="collapsed")

    with st.expander(":material/tune: Goal Settings & Engine Parameters", expanded=True):
        st.markdown("**Goal Preferences (If typing above)**")
        c_hrs, c_prio, c_pref = st.columns(3)
        goal_hours = c_hrs.number_input("Hours Per Day", min_value=1, max_value=24, value=2, help="How many hours do you want to dedicate to this task EACH day?")
        goal_prio = c_prio.selectbox("Priority", ["High", "Medium", "Low"], key="g_prio")
        goal_pref = c_pref.selectbox("Preferred Time", ["Any", "Morning", "Afternoon", "Evening"], key="g_pref")

        st.divider()
        st.markdown("**Engine Parameters**")
        c1, c2, c3 = st.columns(3)
        engine = c1.selectbox("Algorithm", ["Greedy (Fast, Sequential)", "CP-SAT (Global Optimization)", "Compare Both"])
        start_date = c2.date_input("Week Start", value=date.today(), format="DD/MM/YYYY")
        days_out = c3.slider("Days to Schedule", 1, 14, 7)

    if st.button(":material/auto_awesome: Generate Schedule", type="primary", use_container_width=True):
        with st.spinner("Calculating optimal routing and applying to calendar..."):

            if goal_input:
                duration_mins = int(goal_hours * 60)
                chunks_per_day = duration_mins // 60
                rem = duration_mins % 60
                part_num = 1

                for day_offset in range(days_out):
                    target_date = start_date + timedelta(days=day_offset)
                    for i in range(chunks_per_day):
                        insert_task(f"{goal_input} (Pt {part_num})", "Self-Study", goal_prio, 60, target_date.isoformat(), goal_pref, 0, None, None, "AI Generated Habit")
                        part_num += 1
                    if rem > 0:
                        insert_task(f"{goal_input} (Pt {part_num})", "Self-Study", goal_prio, rem, target_date.isoformat(), goal_pref, 0, None, None, "AI Generated Habit")
                        part_num += 1

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND module != 'Break'")
            all_tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()

            if "Greedy" in engine or "Compare" in engine:
                greedy_result = generate_greedy_schedule([dict(t) for t in all_tasks], start_date, days_out, day_start, day_end, max_hrs, b_mins)
                st.session_state.greedy_res = greedy_result
            if "CP-SAT" in engine or "Compare" in engine:
                cpsat_result = generate_cpsat_schedule([dict(t) for t in all_tasks], start_date, days_out, day_start, day_end, max_hrs, b_mins)
                st.session_state.cpsat_res = cpsat_result
            st.session_state.show_results = engine

            if "Compare Both" in engine:
                apply_schedule_with_breaks(st.session_state.cpsat_res, b_mins)
            elif "Greedy" in engine:
                apply_schedule_with_breaks(st.session_state.greedy_res, b_mins)
            else:
                apply_schedule_with_breaks(st.session_state.cpsat_res, b_mins)

            st.success("Calendar updated automatically! Head to the Calendar tab to see your schedule.")

    if st.session_state.get('show_results'):
        engine_mode = st.session_state.show_results
        st.markdown("### What was scheduled:")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND module != 'Break'")
        current_tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if engine_mode == "Compare Both":
            c_g, c_c = st.columns(2)
            with c_g:
                st.subheader("Greedy Results")
                summ_g = generate_schedule_summary(st.session_state.greedy_res, len(current_tasks))
                st.metric("Tasks Placed", f"{summ_g['placed']}/{summ_g['placed']+summ_g['unplaced']}")
            with c_c:
                st.subheader("CP-SAT Results (Applied)")
                summ_c = generate_schedule_summary(st.session_state.cpsat_res, len(current_tasks))
                st.metric("Tasks Placed", f"{summ_c['placed']}/{summ_c['placed']+summ_c['unplaced']}")

            with st.expander("See Engine Decision Breakdown"):
                for t in [x for x in current_tasks if not x['is_fixed']]:
                    g_match = next((x for x in st.session_state.greedy_res if x['id'] == t['id']), {})
                    c_match = next((x for x in st.session_state.cpsat_res if x['id'] == t['id']), {})
                    st.info(f"**{t['name']}**: {compare_explanations(g_match, c_match)}")

        else:
            res = st.session_state.greedy_res if "Greedy" in engine_mode else st.session_state.cpsat_res
            summ = generate_schedule_summary(res, len(current_tasks))
            st.metric("Placement Success", f"{summ['success_rate']}% ({summ['placed']} placed)")

            with st.expander("See Placement Reasoning"):
                for t in [x for x in res if x.get('start_time')]:
                    st.caption(f"**{t['name']}**: {t.get('explanation', 'Fixed Event')}")

# ==========================================
# VIEW 4: CALENDAR
# ==========================================
def render_calendar():
    st.markdown("<h1 style='color: #0F172A;'>My Schedule</h1>", unsafe_allow_html=True)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND start_time IS NOT NULL")
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()

    events = []

    for t in tasks:
        mod = t.get('module', 'Other')
        name_lower = t['name'].lower()

        bg_color, text_color = "#F1F5F9", "#334155"

        if mod == 'Break':
            bg_color, text_color = "#E2E8F0", "#475569"
        elif "exam" in name_lower or "test" in name_lower:
            bg_color, text_color = "#FECACA", "#7F1D1D"
        elif "class" in name_lower or t.get('is_fixed'):
            bg_color, text_color = "#BAE6FD", "#0C4A6E"
        elif t['priority'] == 'High':
            bg_color, text_color = "#C4B5FD", "#4C1D95"
        else:
            bg_color, text_color = "#D9F99D", "#14532D"

        events.append({
            "id": t['id'],
            "title": t['name'],
            "start": t['start_time'],
            "end": t['end_time'],
            "backgroundColor": bg_color,
            "textColor": text_color,
            "borderColor": "transparent"
        })

    cal_options = {
        "editable": True,
        "locale": "en-gb",
        "headerToolbar": {"left": "today prev,next", "center": "title", "right": "timeGridDay,timeGridWeek,dayGridMonth"},
        "initialView": "timeGridWeek",
        "slotMinTime": "06:00:00",
        "slotMaxTime": "23:00:00",
        "height": 750,
        "allDaySlot": False,
        "nowIndicator": True
    }

    cal_data = calendar(events=events, options=cal_options, callbacks=['eventClick', 'eventDrop'])

    if cal_data:
        if "eventDrop" in cal_data:
            ev = cal_data["eventDrop"]["event"]
            conn = get_connection()
            c = conn.cursor()
            c.execute("UPDATE tasks SET start_time = ?, end_time = ? WHERE id = ?", (ev["start"], ev["end"], ev["id"]))
            conn.commit()
            conn.close()
            st.rerun()

        if "eventClick" in cal_data:
            ev_id = cal_data["eventClick"]["event"]["id"]
            t_match = next((t for t in tasks if t['id'] == ev_id), None)
            if t_match:
                edit_dialog(t_match)

@st.dialog("Manage Event")
def edit_dialog(task):
    st.write(f"**{task['name']}**")
    c1, c2 = st.columns(2)
    if c1.button(":material/check_circle: Complete", type="primary"):
        mark_task_completed(task['id'], task['module'], task['duration'])
        st.rerun()
    if c2.button(":material/delete: Delete"):
        conn = get_connection()
        conn.cursor().execute("DELETE FROM tasks WHERE id = ?", (task['id'],))
        conn.commit()
        conn.close()
        st.rerun()

# ==========================================
# VIEW 5: FOCUS MODE
# ==========================================
def render_focus_mode():
    st.markdown("<h1 style='color: #0F172A;'>Focus Mode</h1>", unsafe_allow_html=True)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND module != 'Break'")
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not tasks:
        st.info("No tasks available to focus on.")
        return

    task_options = {f"{t['name']} ({t['duration']} mins)": t for t in tasks}
    selected_task_name = st.selectbox("Select Task", list(task_options.keys()))
    selected_task = task_options[selected_task_name]

    if st.button(":material/play_circle: Start Session", type="primary"):
        my_bar = st.progress(0, text="Locking in...")
        ph = st.empty()

        for percent_complete in range(100):
            time.sleep(0.05)
            my_bar.progress(percent_complete + 1, text=f"Focusing: {selected_task['name']}")
            if percent_complete % 25 == 0:
                ph.info(f"Coach: {get_focus_tip()}")

        st.balloons()
        ph.empty()
        st.success(get_hype_message())
        mark_task_completed(selected_task['id'], selected_task['module'], selected_task['duration'])
        time.sleep(2)
        st.rerun()

# ==========================================
# VIEW 6: STATS
# ==========================================
def render_stats():
    st.markdown("<h1 style='color: #0F172A;'>Analytics</h1>", unsafe_allow_html=True)

    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM completion_log", conn)
    conn.close()

    if df.empty:
        st.info("Complete some tasks to unlock your analytics.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Tasks Crushed", len(df))
    c2.metric("Hours Logged", round(df['duration'].sum() / 60, 1))
    c3.metric("Current Streak", get_streak())

    st.divider()
    c_chart1, c_chart2 = st.columns(2)

    with c_chart1:
        st.markdown("### Days Active")
        daily_counts = df.groupby('completion_date').size()
        st.bar_chart(daily_counts, color="#8B5CF6")

    with c_chart2:
        st.markdown("### Module Breakdown")
        mod_hours = df.groupby('module')['duration'].sum() / 60
        fig, ax = plt.subplots(figsize=(4,3))
        fig.patch.set_alpha(0)
        mod_hours.plot.pie(ax=ax, autopct='%1.0f%%', colors=['#C4B5FD', '#BAE6FD', '#FECACA', '#D9F99D'], textprops={'color':"#0F172A", 'weight': 'bold'})
        ax.set_ylabel('')
        st.pyplot(fig)

# ==========================================
# VIEW 7: SETTINGS
# ==========================================
def render_settings():
    st.markdown("<h1 style='color: #0F172A;'>System Settings</h1>", unsafe_allow_html=True)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_preferences")
    prefs = {row['key']: int(row['value']) for row in cursor.fetchall()}

    with st.form("settings_form"):
        st.subheader("Scheduling Defaults")
        c1, c2 = st.columns(2)
        day_start = c1.number_input("Day Start Hour", min_value=0, max_value=23, value=prefs.get('day_start', 8))
        day_end = c2.number_input("Day End Hour", min_value=0, max_value=23, value=prefs.get('day_end', 22))
        c3, c4 = st.columns(2)
        max_hours = c3.number_input("Max Study Hours/Day", min_value=1, max_value=12, value=prefs.get('max_hours', 6))
        break_mins = c4.number_input("Default Break (mins)", min_value=0, max_value=60, value=prefs.get('break_mins', 15))

        if st.form_submit_button("Save Preferences", type="primary"):
            new_prefs = {"day_start": str(day_start), "day_end": str(day_end), "max_hours": str(max_hours), "break_mins": str(break_mins)}
            for k, v in new_prefs.items():
                cursor.execute("INSERT OR REPLACE INTO user_preferences (key, value) VALUES (?, ?)", (k, v))
            conn.commit()
            st.success("Settings saved.")

    if st.button(":material/warning: Reset Database"):
        cursor.execute("DELETE FROM tasks")
        cursor.execute("DELETE FROM completion_log")
        conn.commit()
        st.rerun()
    conn.close()

if __name__ == "__main__":
    main()