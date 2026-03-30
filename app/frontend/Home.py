import sys
import os
import time
import uuid
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date, datetime, timedelta, time as dt_time
from pathlib import Path
from collections import Counter

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar

from app.backend.database import get_connection, init_db, get_streak, mark_task_completed, bulk_update_schedule
from app.backend.motivator import get_greeting, get_hype_message, get_streak_message, get_recovery_message, get_smart_suggestion, get_focus_tip
from app.backend.greedy_scheduler import generate_greedy_schedule
from app.backend.cpsat_scheduler import generate_cpsat_schedule
from app.backend.explanation import generate_schedule_summary, compare_explanations
from app.backend.export_service import generate_ics_file

st.set_page_config(page_title="ScheduleSmart V2", page_icon=":material/calendar_month:", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
    html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }
    .stApp { background-color: #F8FAFC; color: #1E293B; }
    
    .metric-card {
        background-color: #FFFFFF; border-radius: 20px; padding: 24px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.03); border: 1px solid #F1F5F9; text-align: center;
        transition: transform 0.2s ease-in-out; border-top: 3px solid transparent;
    }
    .metric-card:hover { transform: translateY(-4px); box-shadow: 0 15px 30px rgba(0, 0, 0, 0.05); }
    .metric-card-due { border-top-color: #E37400; }
    .metric-card-pending { border-top-color: #1A73E8; }
    .metric-card-done { border-top-color: #0B8043; }
    .metric-card-streak { border-top-color: #8430CE; }
    .metric-value { font-size: 42px; font-weight: 800; color: #0F172A; margin-bottom: 4px; letter-spacing: -1px; }
    .metric-label { font-size: 13px; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 1.5px; }
    
    .streak-banner { background: linear-gradient(135deg, #A78BFA 0%, #C4B5FD 100%); color: #4C1D95; padding: 16px; border-radius: 16px; margin-bottom: 24px; font-weight: 800; text-align: center; text-transform: uppercase; box-shadow: 0 4px 12px rgba(167, 139, 250, 0.2); }
    .recovery-banner { background-color: #FECACA; color: #7F1D1D; padding: 16px; border-radius: 16px; margin-bottom: 24px; font-weight: 700; text-align: center; }
    
    .suggestion-box { 
        background: linear-gradient(135deg, #EFF6FF 0%, #F0F9FF 100%); 
        border-left: 4px solid #1A73E8; padding: 20px 24px; border-radius: 12px; margin-top: 24px; 
        color: #1E293B; box-shadow: 0 4px 12px rgba(26, 115, 232, 0.08);
    }
    .suggestion-box strong { color: #1A73E8; }
    
    .progress-container { 
        background-color: #FFFFFF; border-radius: 16px; padding: 20px 24px; margin: 24px 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03); border: 1px solid #F1F5F9;
    }
    .progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .progress-title { font-weight: 700; color: #0F172A; font-size: 15px; }
    .progress-count { font-weight: 800; color: #1A73E8; font-size: 15px; }
    .progress-bar-bg { background-color: #F1F5F9; border-radius: 8px; height: 10px; overflow: hidden; }
    .progress-bar-fill { height: 100%; border-radius: 8px; transition: width 0.5s ease; }

    .priority-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
    .priority-high { background-color: #8430CE; }
    .priority-medium { background-color: #0B8043; }
    .priority-low { background-color: #E37400; }
    
    div[data-testid="stExpander"] { background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important; border-radius: 12px !important; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }

    .cal-legend { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
    .cal-legend-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #5F6368; font-weight: 500; }
    .cal-legend-dot { width: 12px; height: 12px; border-radius: 3px; }

    .tip-box {
        background-color: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 12px;
        padding: 14px 20px; margin-bottom: 24px; color: #0C4A6E; font-size: 14px;
    }
    .tip-box strong { color: #0369A1; }

    .form-section-label {
        font-size: 12px; font-weight: 700; color: #94A3B8; text-transform: uppercase;
        letter-spacing: 1.2px; margin-bottom: 8px; margin-top: 4px;
    }

    .colour-preview {
        display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px;
        background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;
        font-size: 13px; color: #64748B; font-weight: 500; margin-bottom: 8px;
    }
    .colour-preview-dot { width: 14px; height: 14px; border-radius: 4px; }

    .split-preview {
        background-color: #F5F3FF; border: 1px solid #DDD6FE; border-radius: 10px;
        padding: 12px 16px; color: #5B21B6; font-size: 13px; font-weight: 600; margin-top: 8px;
    }

    .focus-card {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px;
        padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-bottom: 20px;
    }

    .quality-score {
        text-align: center; padding: 20px; border-radius: 16px; margin: 8px 0;
    }
    .quality-score-value { font-size: 48px; font-weight: 800; letter-spacing: -2px; }
    .quality-score-label { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }

    .weekly-report {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px;
        padding: 24px; margin-top: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .weekly-report p { margin: 6px 0; color: #334155; font-size: 14px; line-height: 1.6; }

    .settings-summary {
        background: linear-gradient(135deg, #EFF6FF 0%, #F0F9FF 100%);
        border: 1px solid #BFDBFE; border-radius: 12px; padding: 16px 20px;
        margin-bottom: 24px; color: #1E40AF; font-size: 14px; font-weight: 500;
    }

    .stat-card {
        background: #FFFFFF; border-radius: 16px; padding: 20px; text-align: center;
        border: 1px solid #F1F5F9; box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        border-top: 3px solid transparent;
    }
    .stat-card-value { font-size: 32px; font-weight: 800; color: #0F172A; }
    .stat-card-label { font-size: 12px; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

CALENDAR_CSS = """
    .fc { background-color: #FFFFFF; padding: 20px; border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid #E5E7EB; font-family: 'Inter', 'Segoe UI', sans-serif; }
    .fc-theme-standard td, .fc-theme-standard th { border-color: #F3F4F6 !important; }
    .fc-theme-standard .fc-scrollgrid { border-color: #E5E7EB !important; }
    .fc-col-header-cell { padding: 10px 0 !important; background-color: transparent !important; border-bottom: 1px solid #E5E7EB !important; }
    .fc-col-header-cell-cushion { color: #70757A !important; font-weight: 500 !important; font-size: 0.75em !important; text-transform: uppercase !important; letter-spacing: 0.5px !important; text-decoration: none !important; }
    .fc-timegrid-axis-cushion { color: #70757A !important; font-size: 10px !important; font-weight: 400 !important; }
    .fc-timegrid-slot { height: 3.5em !important; border-color: #F3F4F6 !important; }
    .fc-timegrid-slot-minor { border-top-style: none !important; }
    .fc-timegrid-slot-label { vertical-align: top !important; padding-top: 2px !important; }
    .fc-header-toolbar { margin-bottom: 12px !important; padding: 4px 0 !important; }
    .fc-toolbar-title { color: #3C4043 !important; font-weight: 400 !important; font-size: 1.4em !important; }
    .fc-button-primary { background-color: transparent !important; color: #3C4043 !important; border: 1px solid #DADCE0 !important; border-radius: 4px !important; text-transform: capitalize !important; font-weight: 500 !important; box-shadow: none !important; padding: 6px 16px !important; font-size: 0.85em !important; }
    .fc-button-primary:hover { background-color: #F1F3F4 !important; }
    .fc-button-primary:focus { box-shadow: none !important; }
    .fc-button-active { background-color: #E8F0FE !important; color: #1A73E8 !important; border-color: #D2E3FC !important; }
    .fc-today-button { background-color: transparent !important; border: 1px solid #DADCE0 !important; color: #3C4043 !important; border-radius: 4px !important; font-weight: 500 !important; font-size: 0.85em !important; padding: 6px 16px !important; }
    .fc-today-button:hover { background-color: #F1F3F4 !important; }
    .fc-today-button:disabled { opacity: 0.6 !important; background-color: transparent !important; }
    .fc-prev-button, .fc-next-button { border: none !important; color: #5F6368 !important; padding: 6px 8px !important; border-radius: 50% !important; background-color: transparent !important; }
    .fc-prev-button:hover, .fc-next-button:hover { background-color: #F1F3F4 !important; }
    .fc-button-group .fc-button { border-radius: 0 !important; margin-left: -1px !important; }
    .fc-button-group .fc-button:first-child { border-radius: 4px 0 0 4px !important; }
    .fc-button-group .fc-button:last-child { border-radius: 0 4px 4px 0 !important; }
    .fc-event { border-radius: 4px !important; border: none !important; border-left: 4px solid currentColor !important; padding: 1px 6px !important; font-weight: 500 !important; font-size: 0.8em !important; box-shadow: none !important; cursor: pointer; overflow: hidden !important; }
    .fc-event-main { white-space: normal !important; word-wrap: break-word !important; line-height: 1.3 !important; }
    .fc-event:hover { opacity: 0.8; }
    .fc-day-today { background-color: #EFF6FF !important; }
    .fc-timegrid-now-indicator-line { border-color: #EA4335 !important; border-width: 2px !important; }
    .fc-daygrid-event { border-radius: 4px !important; padding: 1px 6px !important; border-left: 4px solid currentColor !important; border-top: none !important; border-right: none !important; border-bottom: none !important; }
    .fc-daygrid-day-number { color: #70757A !important; font-weight: 500 !important; font-size: 0.85em !important; padding: 8px !important; text-decoration: none !important; }
    .fc-daygrid-day.fc-day-today .fc-daygrid-day-number { background-color: #1A73E8 !important; color: #FFFFFF !important; border-radius: 50% !important; width: 28px !important; height: 28px !important; display: flex !important; align-items: center !important; justify-content: center !important; }
    .fc-daygrid-day.fc-day-today { background-color: transparent !important; }
"""

def main():
    init_db()
    with st.sidebar:
        logo_path = Path(__file__).parent / "logo.jpg"
        if logo_path.exists(): st.image(str(logo_path), width=180)
        st.markdown("<h3 style='color: #0F172A; font-weight: 800;'>ScheduleSmart V2</h3>", unsafe_allow_html=True)
        st.caption(datetime.now().strftime("%A, %d %B %Y"))
        selected = option_menu(menu_title=None, options=["Dashboard", "Add Task", "Schedule Generator", "Calendar", "Focus Mode", "Stats", "Settings"], icons=["house", "plus-square", "cpu", "calendar-week", "play-circle", "bar-chart", "gear"], default_index=0, styles={"container": {"padding": "0!important", "background-color": "transparent"}, "icon": {"color": "#64748B", "font-size": "18px"}, "nav-link": {"font-size": "15px", "text-align": "left", "margin": "8px", "color": "#475569", "font-weight": "600", "border-radius": "12px"}, "nav-link-selected": {"background-color": "#EFF6FF", "color": "#2563EB", "font-weight": "800"}})
        streak_count = get_streak()
        if streak_count > 0:
            st.markdown("---")
            st.markdown(f"<div style='text-align: center;'><h1 style='color: #8B5CF6; margin: 0; font-size: 48px;'>{streak_count}</h1><p style='color: #64748B; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;'>Day Streak</p></div>", unsafe_allow_html=True)

    if selected == "Dashboard": render_dashboard()
    elif selected == "Add Task": render_add_task()
    elif selected == "Schedule Generator": render_schedule_generator()
    elif selected == "Calendar": render_calendar()
    elif selected == "Focus Mode": render_focus_mode()
    elif selected == "Stats": render_stats()
    elif selected == "Settings": render_settings()

def insert_task(name, mod, prio, dur, dead, pref, fix, st_t, en_t, note):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (id, name, module, priority, duration, deadline, preferred_time, is_fixed, start_time, end_time, completed, notes) VALUES (?,?,?,?,?,?,?,?,?,?,0,?)", (str(uuid.uuid4()), name, mod, prio, dur, dead, pref, fix, st_t, en_t, note))
    conn.commit(); conn.close()

def apply_schedule_with_breaks(scheduled_tasks, break_mins):
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE module = 'Break'")
    for task in scheduled_tasks:
        if task.get('start_time'):
            c.execute("UPDATE tasks SET start_time = ?, end_time = ? WHERE id = ?", (task['start_time'], task['end_time'], task['id']))
            if not task.get('is_fixed') and break_mins > 0:
                end_time = datetime.fromisoformat(task['end_time'])
                break_end = end_time + timedelta(minutes=break_mins)
                c.execute("INSERT INTO tasks (id, name, module, priority, duration, is_fixed, start_time, end_time, completed) VALUES (?,?,?,?,?,?,?,?,0)", (str(uuid.uuid4()), "Break", "Break", "Low", break_mins, 1, end_time.isoformat(), break_end.isoformat()))
    conn.commit(); conn.close()

def get_event_color(task):
    mod = task.get('module', 'Other'); name_lower = task['name'].lower(); priority = task.get('priority', 'Medium')
    if mod == 'Break': return "#DADCE0", "#F1F3F4", "#80868B"
    elif "exam" in name_lower or "test" in name_lower: return "#D93025", "#FCEAE9", "#A50E0E"
    elif "class" in name_lower or task.get('is_fixed'): return "#1A73E8", "#D2E3FC", "#174EA6"
    elif priority == 'High': return "#8430CE", "#E9D5FF", "#5B21B6"
    elif priority == 'Medium': return "#0B8043", "#CEEAD6", "#0D652D"
    else: return "#E37400", "#FEF3C7", "#92400E"

def get_priority_dot(priority):
    css_class = {"High": "priority-high", "Medium": "priority-medium", "Low": "priority-low"}.get(priority, "priority-medium")
    return f"<span class='priority-dot {css_class}'></span>"

def calculate_quality_score(scheduled_tasks, days_to_schedule):
    if not scheduled_tasks: return 0
    placed = [t for t in scheduled_tasks if t.get('start_time') and not t.get('is_fixed')]
    if not placed: return 0

    score = 100
    deadline_met = sum(1 for t in placed if not t.get('deadline') or (t.get('start_time', '9999') <= t['deadline']))
    if placed: score -= max(0, (len(placed) - deadline_met) * 15)

    daily_hours = {}
    for t in placed:
        try:
            day = datetime.fromisoformat(t['start_time']).date().isoformat()
            daily_hours[day] = daily_hours.get(day, 0) + t.get('duration', 0) / 60
        except (ValueError, TypeError):
            pass

    if len(daily_hours) > 1:
        hours_list = list(daily_hours.values())
        spread = max(hours_list) - min(hours_list)
        score -= min(30, int(spread * 8))

    pref_met = sum(1 for t in placed if t.get('preferred_time') == 'Any' or not t.get('preferred_time'))
    non_any = [t for t in placed if t.get('preferred_time') and t.get('preferred_time') != 'Any']
    for t in non_any:
        try:
            hour = datetime.fromisoformat(t['start_time']).hour
            pref = t['preferred_time']
            if pref == 'Morning' and 6 <= hour < 12: pref_met += 1
            elif pref == 'Afternoon' and 12 <= hour < 17: pref_met += 1
            elif pref == 'Evening' and 17 <= hour < 23: pref_met += 1
        except (ValueError, TypeError):
            pass

    return max(0, min(100, score))

def generate_weekly_report():
    conn = get_connection(); cursor = conn.cursor()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    cursor.execute("SELECT * FROM completion_log WHERE completion_date >= ?", (week_ago,))
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND module != 'Break'")
    pending = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return None

    total_tasks = len(rows)
    total_hours = round(sum(r['duration'] for r in rows) / 60, 1)
    modules = Counter(r['module'] for r in rows)
    top_module = modules.most_common(1)[0][0] if modules else "N/A"

    days = Counter(r['completion_date'] for r in rows)
    best_day_str = days.most_common(1)[0][0] if days else None
    best_day_name = datetime.fromisoformat(best_day_str).strftime('%A') if best_day_str else "N/A"

    overdue = [t for t in pending if t.get('deadline') and t['deadline'] < date.today().isoformat()]

    lines = []
    lines.append(f"This week you completed <strong>{total_tasks} tasks</strong> across <strong>{len(modules)} modules</strong>, logging <strong>{total_hours} hours</strong> of study.")
    lines.append(f"Your most focused day was <strong>{best_day_name}</strong> and your top module was <strong>{top_module}</strong>.")
    if overdue:
        modules_behind = set(t.get('module', 'Unknown') for t in overdue)
        lines.append(f"You have <strong>{len(overdue)} overdue tasks</strong> in {', '.join(modules_behind)} — consider prioritising those this week.")
    else:
        lines.append("You have no overdue tasks. Strong work — keep the momentum going.")

    return "<br>".join(lines)

def render_dashboard():
    st.markdown(f"<h1 style='color: #0F172A;'>{get_greeting()}</h1>", unsafe_allow_html=True)
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND module != 'Break'")
    pending_tasks = [dict(row) for row in cursor.fetchall()]
    today_str = date.today().isoformat()
    cursor.execute("SELECT COUNT(*) as count FROM completion_log WHERE completion_date = ?", (today_str,))
    completed_today = cursor.fetchone()['count']; conn.close()

    streak_count = get_streak()
    if streak_count >= 3:
        st.markdown(f"<div class='streak-banner'>{get_streak_message(streak_count)}</div>", unsafe_allow_html=True)
    overdue_tasks = [t for t in pending_tasks if t['deadline'] and t['deadline'] < today_str]
    if overdue_tasks:
        st.markdown(f"<div class='recovery-banner'>You have {len(overdue_tasks)} overdue tasks. {get_recovery_message()}</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    today_due = len([t for t in pending_tasks if t['deadline'] == today_str or (t['start_time'] and t['start_time'].startswith(today_str))])
    due_accent = "metric-card-due" if today_due > 0 else ""
    done_accent = "metric-card-done" if completed_today > 0 else ""
    streak_accent = "metric-card-streak" if streak_count > 0 else ""
    with c1: st.markdown(f"<div class='metric-card {due_accent}'><div class='metric-value'>{today_due}</div><div class='metric-label'>Due Today</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card metric-card-pending'><div class='metric-value'>{len(pending_tasks)}</div><div class='metric-label'>Pending</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card {done_accent}'><div class='metric-value'>{completed_today}</div><div class='metric-label'>Done Today</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card {streak_accent}'><div class='metric-value'>{streak_count}</div><div class='metric-label'>Day Streak</div></div>", unsafe_allow_html=True)

    total_today = today_due + completed_today
    if total_today > 0:
        pct = int((completed_today / total_today) * 100)
        bar_color = "#0B8043" if pct == 100 else "#1A73E8" if pct >= 50 else "#E37400"
        st.markdown(f"<div class='progress-container'><div class='progress-header'><span class='progress-title'>Today's Progress</span><span class='progress-count'>{completed_today} / {total_today} completed</span></div><div class='progress-bar-bg'><div class='progress-bar-fill' style='width: {pct}%; background-color: {bar_color};'></div></div></div>", unsafe_allow_html=True)

    st.markdown("<br><h3 style='color: #0F172A;'>Up Next</h3>", unsafe_allow_html=True)
    if not pending_tasks:
        st.success("Your schedule is completely clear. Great job.")
    else:
        sorted_tasks = sorted(pending_tasks, key=lambda x: (x['start_time'] or x['deadline'] or '9999-12-31'))
        for t in sorted_tasks[:5]:
            time_label = ""
            if t['start_time']:
                try: time_label = f" · {datetime.fromisoformat(t['start_time']).strftime('%H:%M')}"
                except ValueError: pass
            module_label = f" ({t['module']})" if t.get('module') else ""
            with st.expander(f"{t['name']}{module_label}{time_label}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    prio = t.get('priority', 'Medium')
                    st.markdown(f"{get_priority_dot(prio)} **{prio}** priority · {t.get('duration', 0)} mins", unsafe_allow_html=True)
                    if t['start_time']:
                        try:
                            st_dt = datetime.fromisoformat(t['start_time']); en_dt = datetime.fromisoformat(t['end_time']) if t.get('end_time') else None
                            time_display = f"{st_dt.strftime('%A, %d %B')} · {st_dt.strftime('%H:%M')}"
                            if en_dt: time_display += f" – {en_dt.strftime('%H:%M')}"
                            st.caption(f":material/schedule: {time_display}")
                        except ValueError: pass
                    if t['deadline']:
                        try: st.caption(f":material/event: Deadline: {datetime.fromisoformat(t['deadline']).strftime('%d/%m/%Y')}")
                        except ValueError: pass
                    if t['notes'] and t['notes'] != 'AI Generated Habit': st.caption(f":material/notes: {t['notes']}")
                with col2:
                    if st.button(":material/check_circle: Complete", key=f"d_{t['id']}", use_container_width=True):
                        mark_task_completed(t['id'], t['module'], t['duration']); st.toast(get_hype_message()); time.sleep(1); st.rerun()

    report = generate_weekly_report()
    if report:
        st.markdown(f"<div class='weekly-report'><h4 style='margin: 0 0 12px 0; color: #0F172A;'>Weekly Summary</h4><p>{report}</p></div>", unsafe_allow_html=True)

    st.markdown(f"<div class='suggestion-box'><strong>Smart Suggestion:</strong> {get_smart_suggestion()}</div>", unsafe_allow_html=True)

def render_add_task():
    st.markdown("<h1 style='color: #0F172A;'>Add to Planner</h1>", unsafe_allow_html=True)
    st.markdown("<div class='tip-box'><strong>Tip:</strong> Use <strong>Auto-Schedule</strong> to let the AI find the best slot, or <strong>Manual Time</strong> to pick your own. Classes and exams are always fixed to a specific time.</div>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs([":material/assignment: Assignment", ":material/school: Class", ":material/history_edu: Exam", ":material/directions_run: Personal"])

    with tab1:
        st.subheader("New Assignment / Study Goal")
        st.caption("Schedule a study session or coursework block. Auto-schedule lets the AI place it optimally.")
        st.markdown("<div class='colour-preview'><div class='colour-preview-dot' style='background:#8430CE;'></div> Will appear as a study block on your calendar</div>", unsafe_allow_html=True)
        mode = st.radio("Scheduling Method", ["Manual Time (Add to Calendar Now)", "Auto-Schedule (Let AI decide)"], horizontal=True)
        with st.form("form_assignment"):
            st.markdown("<div class='form-section-label'>Task Details</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            name = c1.text_input("Title", placeholder="e.g., Physics Problem Set"); module = c2.text_input("Module", placeholder="e.g., Physics 101")
            c3, c4 = st.columns(2); priority = c3.selectbox("Priority", ["High", "Medium", "Low"])
            st.markdown("---")
            if "Manual" in mode:
                st.markdown("<div class='form-section-label'>Time Slot</div>", unsafe_allow_html=True)
                d1, d2, d3 = st.columns(3); work_date = d1.date_input("Work Date", format="DD/MM/YYYY"); start_t = d2.time_input("Start Time", value=dt_time(13, 0)); end_t = d3.time_input("End Time", value=dt_time(14, 0))
            else:
                st.markdown("<div class='form-section-label'>Scheduling Preferences</div>", unsafe_allow_html=True)
                dur_presets = st.columns(4)
                with dur_presets[0]:
                    if st.form_submit_button("30 min", use_container_width=True): st.session_state['dur_preset'] = 30
                with dur_presets[1]:
                    if st.form_submit_button("1 hour", use_container_width=True): st.session_state['dur_preset'] = 60
                with dur_presets[2]:
                    if st.form_submit_button("2 hours", use_container_width=True): st.session_state['dur_preset'] = 120
                with dur_presets[3]:
                    if st.form_submit_button("3 hours", use_container_width=True): st.session_state['dur_preset'] = 180
                preset_val = st.session_state.get('dur_preset', 120)
                duration = c4.number_input("Total Duration (mins)", min_value=15, value=preset_val, step=15)
                d1, d2 = st.columns(2); deadline = d1.date_input("Deadline", format="DD/MM/YYYY"); pref_time = d2.selectbox("Preferred Time", ["Any", "Morning", "Afternoon", "Evening"])
                if duration > 90:
                    chunks = duration // 60; rem = duration % 60; total_blocks = chunks + (1 if rem > 0 else 0)
                    block_desc = f"{chunks} x 60 min" + (f" + 1 x {rem} min" if rem > 0 else "")
                    st.markdown(f"<div class='split-preview'>This will be split into {total_blocks} blocks: {block_desc}</div>", unsafe_allow_html=True)
            notes = st.text_area("Notes", placeholder="Any extra details about the task...")
            if st.form_submit_button("Add to Calendar", type="primary", use_container_width=True):
                if not name: st.error("Please enter a title for the task.")
                elif "Manual" in mode:
                    dur = int((datetime.combine(date.today(), end_t) - datetime.combine(date.today(), start_t)).total_seconds() / 60)
                    insert_task(name, module, priority, dur, None, "Any", 1, datetime.combine(work_date, start_t).isoformat(), datetime.combine(work_date, end_t).isoformat(), notes)
                    st.success(f"Added to planner — {name} on {work_date.strftime('%d/%m/%Y')} at {start_t.strftime('%H:%M')} – {end_t.strftime('%H:%M')}")
                else:
                    if duration > 90:
                        chunks = duration // 60; rem = duration % 60
                        for i in range(chunks): insert_task(f"{name} (Pt {i+1})", module, priority, 60, deadline.isoformat(), pref_time, 0, None, None, notes)
                        if rem > 0: insert_task(f"{name} (Pt {chunks+1})", module, priority, rem, deadline.isoformat(), pref_time, 0, None, None, notes)
                        st.success(f"Saved for AI scheduling — {name} split into {chunks + (1 if rem>0 else 0)} blocks, deadline {deadline.strftime('%d/%m/%Y')}")
                    else:
                        insert_task(name, module, priority, duration, deadline.isoformat(), pref_time, 0, None, None, notes)
                        st.success(f"Saved for AI scheduling — {name} ({duration} mins), deadline {deadline.strftime('%d/%m/%Y')}")

    with tab2:
        st.subheader("Fixed Class"); st.caption("Add a recurring lecture, seminar, or lab session. These are locked to a specific day and time.")
        st.markdown("<div class='colour-preview'><div class='colour-preview-dot' style='background:#1A73E8;'></div> Will appear as a fixed blue block on your calendar</div>", unsafe_allow_html=True)
        with st.form("form_class"):
            st.markdown("<div class='form-section-label'>Class Details</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2); module = c1.text_input("Module Name", placeholder="e.g., CS4001 Software Engineering"); room = c2.text_input("Room", placeholder="e.g., T-101")
            st.markdown("---"); st.markdown("<div class='form-section-label'>Time Slot</div>", unsafe_allow_html=True)
            d1, d2, d3 = st.columns(3); class_date = d1.date_input("Date", format="DD/MM/YYYY"); start_t = d2.time_input("Start Time", value=dt_time(13, 0)); end_t = d3.time_input("End Time", value=dt_time(14, 0))
            repeat = st.checkbox("Repeat weekly for 4 weeks")
            if st.form_submit_button("Add to Calendar", type="primary", use_container_width=True):
                if not module: st.error("Please enter a module name.")
                else:
                    dur = int((datetime.combine(date.today(), end_t) - datetime.combine(date.today(), start_t)).total_seconds() / 60)
                    for w in range(4 if repeat else 1):
                        act_date = class_date + timedelta(weeks=w)
                        insert_task(f"Class: {module}", module, "High", dur, None, "Any", 1, datetime.combine(act_date, start_t).isoformat(), datetime.combine(act_date, end_t).isoformat(), room)
                    st.success(f"Added — {module} {'repeating 4 weeks from' if repeat else 'on'} {class_date.strftime('%d/%m/%Y')} at {start_t.strftime('%H:%M')}")

    with tab3:
        st.subheader("Exam Entry"); st.caption("Log an upcoming exam. These are marked as high priority and appear in red on your calendar.")
        st.markdown("<div class='colour-preview'><div class='colour-preview-dot' style='background:#D93025;'></div> Will appear as a red exam block on your calendar</div>", unsafe_allow_html=True)
        with st.form("form_exam"):
            st.markdown("<div class='form-section-label'>Exam Details</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2); module = c1.text_input("Subject", placeholder="e.g., Data Structures & Algorithms"); seat = c2.text_input("Seat", placeholder="e.g., Row C, Seat 14")
            st.markdown("---"); st.markdown("<div class='form-section-label'>Date & Time</div>", unsafe_allow_html=True)
            d1, d2, d3 = st.columns(3); ex_date = d1.date_input("Date", format="DD/MM/YYYY"); start_t = d2.time_input("Start Time", value=dt_time(13, 0)); end_t = d3.time_input("End Time", value=dt_time(14, 0))
            if st.form_submit_button("Add to Calendar", type="primary", use_container_width=True):
                if not module: st.error("Please enter a subject name.")
                else:
                    dur = int((datetime.combine(date.today(), end_t) - datetime.combine(date.today(), start_t)).total_seconds() / 60)
                    insert_task(f"EXAM: {module}", module, "High", dur, ex_date.isoformat(), "Any", 1, datetime.combine(ex_date, start_t).isoformat(), datetime.combine(ex_date, end_t).isoformat(), seat)
                    st.success(f"Exam saved — {module} on {ex_date.strftime('%d/%m/%Y')} at {start_t.strftime('%H:%M')} – {end_t.strftime('%H:%M')}")

    with tab4:
        st.subheader("Personal Activity"); st.caption("Add gym sessions, meal prep, commute blocks, or anything outside of academics.")
        st.markdown("<div class='colour-preview'><div class='colour-preview-dot' style='background:#E37400;'></div> Will appear as an amber block on your calendar</div>", unsafe_allow_html=True)
        with st.form("form_personal"):
            st.markdown("<div class='form-section-label'>Activity Details</div>", unsafe_allow_html=True)
            name = st.text_input("Activity", placeholder="e.g., Gym, Meal Prep, Commute")
            c1, c2 = st.columns(2); duration = c1.number_input("Duration (mins)", value=60, min_value=15, step=15); is_fixed = c2.checkbox("Fixed Time?", help="Tick this if the activity happens at a specific time.")
            st.markdown("---")
            if is_fixed:
                st.markdown("<div class='form-section-label'>Time Slot</div>", unsafe_allow_html=True)
                d1, d2, d3 = st.columns(3); p_date = d1.date_input("Date", format="DD/MM/YYYY"); start_t = d2.time_input("Start Time", value=dt_time(13, 0)); end_t = d3.time_input("End Time", value=dt_time(14, 0)); pref_time = "Any"
            else:
                st.markdown("<div class='form-section-label'>Scheduling Preference</div>", unsafe_allow_html=True)
                pref_time = st.selectbox("Preferred Time", ["Any", "Morning", "Afternoon", "Evening"])
            if st.form_submit_button("Add to Calendar", type="primary", use_container_width=True):
                if not name: st.error("Please enter an activity name.")
                elif is_fixed:
                    insert_task(name, "Personal", "Low", duration, None, "Any", 1, datetime.combine(p_date, start_t).isoformat(), datetime.combine(p_date, end_t).isoformat(), "")
                    st.success(f"Added — {name} on {p_date.strftime('%d/%m/%Y')} at {start_t.strftime('%H:%M')} – {end_t.strftime('%H:%M')}")
                else:
                    insert_task(name, "Personal", "Low", duration, None, pref_time, 0, None, None, "")
                    st.success(f"Saved for AI scheduling — {name} ({duration} mins), preferred time: {pref_time}")

def render_schedule_generator():
    st.markdown("<h1 style='color: #0F172A;'>AI Schedule Engine</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; font-size: 16px; margin-bottom: 20px;'>What do you want to learn? Type a goal and the AI will build a daily habit schedule.</p>", unsafe_allow_html=True)
    conn = get_connection(); cursor = conn.cursor(); cursor.execute("SELECT * FROM user_preferences"); prefs = {row['key']: int(row['value']) for row in cursor.fetchall()}; conn.close()
    day_start = prefs.get('day_start', 8); day_end = prefs.get('day_end', 22); max_hrs = prefs.get('max_hours', 6); b_mins = prefs.get('break_mins', 15)
    goal_input = st.text_input("Goal", placeholder="e.g. Master Python, Calculus Revision...", label_visibility="collapsed")
    with st.expander(":material/tune: Goal Settings & Engine Parameters", expanded=True):
        st.markdown("**Goal Preferences (If typing above)**")
        c_hrs, c_prio, c_pref = st.columns(3); goal_hours = c_hrs.number_input("Hours Per Day", min_value=1, max_value=24, value=2); goal_prio = c_prio.selectbox("Priority", ["High", "Medium", "Low"], key="g_prio"); goal_pref = c_pref.selectbox("Preferred Time", ["Any", "Morning", "Afternoon", "Evening"], key="g_pref")
        st.divider(); st.markdown("**Engine Parameters**")
        c1, c2, c3 = st.columns(3); engine = c1.selectbox("Algorithm", ["Greedy (Fast, Sequential)", "CP-SAT (Global Optimization)", "Compare Both"]); start_date = c2.date_input("Week Start", value=date.today(), format="DD/MM/YYYY"); days_out = c3.slider("Days to Schedule", 1, 14, 7)

    if st.button(":material/auto_awesome: Generate Schedule", type="primary", use_container_width=True):
        with st.spinner("Calculating optimal routing and applying to calendar..."):
            if goal_input:
                duration_mins = int(goal_hours * 60); chunks_per_day = duration_mins // 60; rem = duration_mins % 60; part_num = 1
                for day_offset in range(days_out):
                    target_date = start_date + timedelta(days=day_offset)
                    for i in range(chunks_per_day): insert_task(f"{goal_input} (Pt {part_num})", "Self-Study", goal_prio, 60, target_date.isoformat(), goal_pref, 0, None, None, "AI Generated Habit"); part_num += 1
                    if rem > 0: insert_task(f"{goal_input} (Pt {part_num})", "Self-Study", goal_prio, rem, target_date.isoformat(), goal_pref, 0, None, None, "AI Generated Habit"); part_num += 1
            conn = get_connection(); cursor = conn.cursor(); cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND module != 'Break'"); all_tasks = [dict(row) for row in cursor.fetchall()]; conn.close()
            if "Greedy" in engine or "Compare" in engine: st.session_state.greedy_res = generate_greedy_schedule([dict(t) for t in all_tasks], start_date, days_out, day_start, day_end, max_hrs, b_mins)
            if "CP-SAT" in engine or "Compare" in engine: st.session_state.cpsat_res = generate_cpsat_schedule([dict(t) for t in all_tasks], start_date, days_out, day_start, day_end, max_hrs, b_mins)
            st.session_state.show_results = engine; st.session_state.days_out = days_out
            if "Compare Both" in engine: apply_schedule_with_breaks(st.session_state.cpsat_res, b_mins)
            elif "Greedy" in engine: apply_schedule_with_breaks(st.session_state.greedy_res, b_mins)
            else: apply_schedule_with_breaks(st.session_state.cpsat_res, b_mins)
            st.success("Calendar updated automatically! Head to the Calendar tab to see your schedule.")

    if st.session_state.get('show_results'):
        engine_mode = st.session_state.show_results
        st.markdown("### What was scheduled:")
        conn = get_connection(); cursor = conn.cursor(); cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND module != 'Break'"); current_tasks = [dict(row) for row in cursor.fetchall()]; conn.close()
        days_out_val = st.session_state.get('days_out', 7)

        if engine_mode == "Compare Both":
            c_g, c_c = st.columns(2)
            g_score = calculate_quality_score(st.session_state.greedy_res, days_out_val)
            c_score = calculate_quality_score(st.session_state.cpsat_res, days_out_val)
            with c_g:
                st.subheader("Greedy Results")
                summ_g = generate_schedule_summary(st.session_state.greedy_res, len(current_tasks))
                st.metric("Tasks Placed", f"{summ_g['placed']}/{summ_g['placed']+summ_g['unplaced']}")
                g_color = "#0B8043" if g_score >= 80 else "#E37400" if g_score >= 50 else "#D93025"
                st.markdown(f"<div class='quality-score' style='background: #F8FAFC; border: 2px solid {g_color};'><div class='quality-score-value' style='color: {g_color};'>{g_score}</div><div class='quality-score-label' style='color: {g_color};'>Quality Score</div></div>", unsafe_allow_html=True)
            with c_c:
                st.subheader("CP-SAT Results (Applied)")
                summ_c = generate_schedule_summary(st.session_state.cpsat_res, len(current_tasks))
                st.metric("Tasks Placed", f"{summ_c['placed']}/{summ_c['placed']+summ_c['unplaced']}")
                c_color = "#0B8043" if c_score >= 80 else "#E37400" if c_score >= 50 else "#D93025"
                st.markdown(f"<div class='quality-score' style='background: #F8FAFC; border: 2px solid {c_color};'><div class='quality-score-value' style='color: {c_color};'>{c_score}</div><div class='quality-score-label' style='color: {c_color};'>Quality Score</div></div>", unsafe_allow_html=True)

            with st.expander("Workload Balance Comparison"):
                for label, res in [("Greedy", st.session_state.greedy_res), ("CP-SAT", st.session_state.cpsat_res)]:
                    daily = {}
                    for t in res:
                        if t.get('start_time') and not t.get('is_fixed'):
                            try:
                                d = datetime.fromisoformat(t['start_time']).strftime('%a %d/%m')
                                daily[d] = daily.get(d, 0) + t.get('duration', 0) / 60
                            except (ValueError, TypeError): pass
                    if daily:
                        st.markdown(f"**{label} — Hours per Day:**")
                        chart_df = pd.DataFrame({"Day": list(daily.keys()), "Hours": list(daily.values())}).set_index("Day")
                        st.bar_chart(chart_df, color="#8430CE" if label == "Greedy" else "#1A73E8")

            with st.expander("See Engine Decision Breakdown", expanded=True):
                comparison_rows = []
                for t in [x for x in current_tasks if not x['is_fixed']]:
                    g_match = next((x for x in st.session_state.greedy_res if x['id'] == t['id']), {})
                    c_match = next((x for x in st.session_state.cpsat_res if x['id'] == t['id']), {})
                    g_time = g_match.get('start_time', ''); c_time = c_match.get('start_time', '')
                    try: g_display = datetime.fromisoformat(g_time).strftime("%a %H:%M") if g_time else "—"
                    except ValueError: g_display = "—"
                    try: c_display = datetime.fromisoformat(c_time).strftime("%a %H:%M") if c_time else "—"
                    except ValueError: c_display = "—"
                    comparison_rows.append({"Task": t['name'], "Greedy Slot": g_display, "CP-SAT Slot": c_display, "Same?": "Yes" if g_time == c_time else "No"})
                st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)
                st.markdown("---"); st.markdown("**Detailed Reasoning:**")
                for t in [x for x in current_tasks if not x['is_fixed']]:
                    g_match = next((x for x in st.session_state.greedy_res if x['id'] == t['id']), {}); c_match = next((x for x in st.session_state.cpsat_res if x['id'] == t['id']), {})
                    st.info(f"**{t['name']}**: {compare_explanations(g_match, c_match)}")
        else:
            res = st.session_state.greedy_res if "Greedy" in engine_mode else st.session_state.cpsat_res
            summ = generate_schedule_summary(res, len(current_tasks))
            q_score = calculate_quality_score(res, days_out_val)
            col_m, col_q = st.columns([2, 1])
            with col_m: st.metric("Placement Success", f"{summ['success_rate']}% ({summ['placed']} placed)")
            with col_q:
                q_color = "#0B8043" if q_score >= 80 else "#E37400" if q_score >= 50 else "#D93025"
                st.markdown(f"<div class='quality-score' style='background: #F8FAFC; border: 2px solid {q_color};'><div class='quality-score-value' style='color: {q_color};'>{q_score}</div><div class='quality-score-label' style='color: {q_color};'>Quality Score</div></div>", unsafe_allow_html=True)

            with st.expander("Workload Balance"):
                daily = {}
                for t in res:
                    if t.get('start_time') and not t.get('is_fixed'):
                        try:
                            d = datetime.fromisoformat(t['start_time']).strftime('%a %d/%m')
                            daily[d] = daily.get(d, 0) + t.get('duration', 0) / 60
                        except (ValueError, TypeError): pass
                if daily:
                    chart_df = pd.DataFrame({"Day": list(daily.keys()), "Hours": list(daily.values())}).set_index("Day")
                    st.bar_chart(chart_df, color="#1A73E8")

            with st.expander("See Placement Reasoning"):
                for t in [x for x in res if x.get('start_time')]:
                    st.caption(f"**{t['name']}**: {t.get('explanation', 'Fixed Event')}")

def render_calendar():
    st.markdown("<h1 style='color: #0F172A;'>My Schedule</h1>", unsafe_allow_html=True)
    conn = get_connection(); cursor = conn.cursor(); cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND start_time IS NOT NULL"); tasks = [dict(row) for row in cursor.fetchall()]; conn.close()
    col_header, col_export = st.columns([3, 1])
    with col_export:
        if tasks:
            ics_data = generate_ics_file(tasks)
            st.download_button(label=":material/download: Export .ics", data=ics_data, file_name="schedulesmart.ics", mime="text/calendar", use_container_width=True)
    st.markdown("""<div class='cal-legend'><div class='cal-legend-item'><div class='cal-legend-dot' style='background:#8430CE;'></div> High Priority</div><div class='cal-legend-item'><div class='cal-legend-dot' style='background:#0B8043;'></div> Medium Priority</div><div class='cal-legend-item'><div class='cal-legend-dot' style='background:#E37400;'></div> Low Priority</div><div class='cal-legend-item'><div class='cal-legend-dot' style='background:#1A73E8;'></div> Fixed / Class</div><div class='cal-legend-item'><div class='cal-legend-dot' style='background:#D93025;'></div> Exam</div><div class='cal-legend-item'><div class='cal-legend-dot' style='background:#DADCE0;'></div> Break</div></div>""", unsafe_allow_html=True)
    events = []
    for t in tasks:
        border_color, bg_color, text_color = get_event_color(t)
        events.append({"id": t['id'], "title": t['name'], "start": t['start_time'], "end": t['end_time'], "backgroundColor": bg_color, "textColor": text_color, "borderColor": border_color})
    cal_options = {"editable": True, "locale": "en-gb", "headerToolbar": {"left": "today prev,next", "center": "title", "right": "timeGridDay,timeGridWeek,dayGridMonth"}, "initialView": "timeGridWeek", "slotMinTime": "06:00:00", "slotMaxTime": "23:00:00", "height": 700, "allDaySlot": False, "nowIndicator": True, "dayMaxEventRows": 4, "eventTimeFormat": {"hour": "2-digit", "minute": "2-digit", "hour12": False}}
    cal_data = calendar(events=events, options=cal_options, custom_css=CALENDAR_CSS, callbacks=['eventClick', 'eventDrop'])
    if cal_data:
        if "eventDrop" in cal_data:
            ev = cal_data["eventDrop"]["event"]; conn = get_connection(); c = conn.cursor(); c.execute("UPDATE tasks SET start_time = ?, end_time = ? WHERE id = ?", (ev["start"], ev["end"], ev["id"])); conn.commit(); conn.close(); st.rerun()
        if "eventClick" in cal_data:
            ev_id = cal_data["eventClick"]["event"]["id"]; t_match = next((t for t in tasks if t['id'] == ev_id), None)
            if t_match: edit_dialog(t_match)

@st.dialog("Event Details")
def edit_dialog(task):
    border_color, bg_color, text_color = get_event_color(task)
    st.markdown(f"<div style='border-left: 5px solid {border_color}; padding: 12px 16px; background: {bg_color}; border-radius: 8px; margin-bottom: 16px;'><h3 style='margin: 0; color: {text_color};'>{task['name']}</h3></div>", unsafe_allow_html=True)
    if task.get('start_time') and task.get('end_time'):
        try:
            st_dt = datetime.fromisoformat(task['start_time']); en_dt = datetime.fromisoformat(task['end_time'])
            st.markdown(f":material/schedule: **{st_dt.strftime('%A, %d %B')}** · {st_dt.strftime('%H:%M')} – {en_dt.strftime('%H:%M')}")
        except ValueError: pass
    detail_cols = st.columns(3)
    with detail_cols[0]:
        if task.get('module') and task['module'] != 'Break': st.markdown(f":material/school: **Module:** {task['module']}")
    with detail_cols[1]:
        if task.get('priority'): st.markdown(f":material/flag: **Priority:** {task['priority']}")
    with detail_cols[2]:
        if task.get('duration'): st.markdown(f":material/timer: **Duration:** {task['duration']} mins")
    if task.get('deadline'):
        try: st.markdown(f":material/event: **Deadline:** {datetime.fromisoformat(task['deadline']).strftime('%d/%m/%Y')}")
        except ValueError: pass
    if task.get('notes') and task['notes'] != 'AI Generated Habit': st.markdown(f":material/notes: **Notes:** {task['notes']}")
    if task.get('explanation'): st.markdown("---"); st.markdown(f":material/lightbulb: **Why here?** {task['explanation']}")
    st.markdown("---")
    c1, c2 = st.columns(2)
    if c1.button(":material/check_circle: Complete", type="primary", use_container_width=True): mark_task_completed(task['id'], task['module'], task['duration']); st.toast(get_hype_message()); time.sleep(1.5); st.rerun()
    if c2.button(":material/delete: Delete", use_container_width=True): conn = get_connection(); conn.cursor().execute("DELETE FROM tasks WHERE id = ?", (task['id'],)); conn.commit(); conn.close(); st.rerun()

def render_focus_mode():
    st.markdown("<h1 style='color: #0F172A;'>Focus Mode</h1>", unsafe_allow_html=True)
    st.caption("Lock in and complete a study session. You'll receive coaching tips as you progress.")

    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND module != 'Break'")
    tasks = [dict(row) for row in cursor.fetchall()]; conn.close()

    if not tasks:
        st.info("No tasks available to focus on. Add some tasks first.")
        return

    st.markdown(f"<div class='tip-box'><strong>Focus Tip:</strong> {get_focus_tip()}</div>", unsafe_allow_html=True)

    task_options = {f"{t['name']} ({t['duration']} mins)": t for t in tasks}
    selected_task_name = st.selectbox("Select Task", list(task_options.keys()))
    selected_task = task_options[selected_task_name]

    border_color, bg_color, text_color = get_event_color(selected_task)
    st.markdown(f"""
        <div class='focus-card'>
            <div style='border-left: 4px solid {border_color}; padding-left: 16px; margin-bottom: 12px;'>
                <h3 style='margin: 0; color: #0F172A;'>{selected_task['name']}</h3>
            </div>
            <div style='display: flex; gap: 24px; color: #64748B; font-size: 14px;'>
                <span><strong>Module:</strong> {selected_task.get('module', 'N/A')}</span>
                <span><strong>Priority:</strong> {selected_task.get('priority', 'Medium')}</span>
                <span><strong>Duration:</strong> {selected_task.get('duration', 0)} mins</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if selected_task.get('start_time'):
        try:
            st_dt = datetime.fromisoformat(selected_task['start_time']); en_dt = datetime.fromisoformat(selected_task['end_time']) if selected_task.get('end_time') else None
            time_str = f"{st_dt.strftime('%A, %d %B')} · {st_dt.strftime('%H:%M')}"
            if en_dt: time_str += f" – {en_dt.strftime('%H:%M')}"
            st.caption(f":material/schedule: Scheduled: {time_str}")
        except ValueError: pass

    if st.button(":material/play_circle: Start Session", type="primary", use_container_width=True):
        my_bar = st.progress(0, text="Locking in...")
        ph = st.empty()
        for percent_complete in range(100):
            time.sleep(0.05)
            my_bar.progress(percent_complete + 1, text=f"Focusing: {selected_task['name']} — {percent_complete + 1}%")
            if percent_complete % 25 == 0:
                ph.info(f"Coach: {get_focus_tip()}")
        my_bar.progress(100, text="Session complete!")
        ph.empty()
        st.balloons()

        st.markdown(f"""
            <div class='focus-card' style='border-top: 3px solid #0B8043; text-align: center;'>
                <h3 style='color: #0B8043; margin: 0 0 8px 0;'>{get_hype_message()}</h3>
                <p style='color: #64748B; margin: 0;'>{selected_task['name']} · {selected_task.get('duration', 0)} mins completed</p>
            </div>
        """, unsafe_allow_html=True)

        mark_task_completed(selected_task['id'], selected_task['module'], selected_task['duration'])
        time.sleep(3)
        st.rerun()

def render_stats():
    st.markdown("<h1 style='color: #0F172A;'>Analytics</h1>", unsafe_allow_html=True)
    st.caption("Track your study habits, streaks, and progress over time.")

    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM completion_log", conn); conn.close()

    if df.empty:
        st.info("Complete some tasks to unlock your analytics.")
        return

    total_tasks = len(df)
    total_hours = round(df['duration'].sum() / 60, 1)
    current_streak = get_streak()

    days_active = df['completion_date'].nunique()
    avg_daily = round(total_hours / max(days_active, 1), 1)

    day_counts = df['completion_date'].value_counts()
    best_day_str = day_counts.idxmax() if not day_counts.empty else None
    best_day_name = datetime.fromisoformat(best_day_str).strftime('%A') if best_day_str else "N/A"
    best_day_count = day_counts.max() if not day_counts.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(f"<div class='stat-card' style='border-top-color: #1A73E8;'><div class='stat-card-value'>{total_tasks}</div><div class='stat-card-label'>Tasks Completed</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='stat-card' style='border-top-color: #0B8043;'><div class='stat-card-value'>{total_hours}h</div><div class='stat-card-label'>Hours Logged</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='stat-card' style='border-top-color: #8430CE;'><div class='stat-card-value'>{current_streak}</div><div class='stat-card-label'>Day Streak</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='stat-card' style='border-top-color: #E37400;'><div class='stat-card-value'>{avg_daily}h</div><div class='stat-card-label'>Daily Average</div></div>", unsafe_allow_html=True)
    with c5: st.markdown(f"<div class='stat-card' style='border-top-color: #D93025;'><div class='stat-card-value'>{best_day_name[:3]}</div><div class='stat-card-label'>Best Day ({best_day_count} tasks)</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        st.markdown("### Completion Heatmap")
        today = date.today()
        weeks_back = 8
        start = today - timedelta(days=today.weekday() + (weeks_back * 7))
        date_counts = df.groupby('completion_date').size().to_dict()

        fig, ax = plt.subplots(figsize=(6, 2.5))
        fig.patch.set_facecolor('#F8FAFC')
        ax.set_facecolor('#F8FAFC')

        for week in range(weeks_back + 1):
            for dow in range(7):
                d = start + timedelta(days=week * 7 + dow)
                if d > today: continue
                count = date_counts.get(d.isoformat(), 0)
                if count == 0: color = '#EBEDF0'
                elif count <= 1: color = '#9BE9A8'
                elif count <= 3: color = '#40C463'
                elif count <= 5: color = '#30A14E'
                else: color = '#216E39'
                ax.add_patch(plt.Rectangle((week, 6 - dow), 0.9, 0.9, facecolor=color, edgecolor='white', linewidth=1))

        ax.set_xlim(-0.5, weeks_back + 1.5)
        ax.set_ylim(-0.5, 7.5)
        ax.set_yticks([6, 5, 4, 3, 2, 1, 0])
        ax.set_yticklabels(['M', 'T', 'W', 'T', 'F', 'S', 'S'], fontsize=8, color='#70757A')
        ax.set_xticks([])
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False); ax.spines['left'].set_visible(False)
        ax.tick_params(left=False)
        st.pyplot(fig)

    with c_chart2:
        st.markdown("### Module Breakdown")
        mod_hours = df.groupby('module')['duration'].sum() / 60
        fig2, ax2 = plt.subplots(figsize=(4, 2.5))
        fig2.patch.set_facecolor('#F8FAFC')
        colors = ['#8430CE', '#1A73E8', '#D93025', '#0B8043', '#E37400', '#DADCE0']
        mod_hours.plot.pie(ax=ax2, autopct='%1.0f%%', colors=colors[:len(mod_hours)], textprops={'color': "#0F172A", 'weight': 'bold', 'fontsize': 9})
        ax2.set_ylabel('')
        st.pyplot(fig2)

    st.markdown("### Daily Activity")
    daily_counts = df.groupby('completion_date').size()
    daily_df = pd.DataFrame({"Tasks": daily_counts})
    daily_df.index = [datetime.fromisoformat(d).strftime('%a %d/%m') for d in daily_df.index]
    st.bar_chart(daily_df, color="#1A73E8")

def render_settings():
    st.markdown("<h1 style='color: #0F172A;'>System Settings</h1>", unsafe_allow_html=True)
    st.caption("Configure your scheduling preferences and system defaults.")

    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_preferences"); prefs = {row['key']: row['value'] for row in cursor.fetchall()}

    ds = int(prefs.get('day_start', 8)); de = int(prefs.get('day_end', 22))
    mh = int(prefs.get('max_hours', 6)); bm = int(prefs.get('break_mins', 15))
    inc_weekends = prefs.get('include_weekends', '0') == '1'
    study_style = prefs.get('study_style', 'Balanced')

    st.markdown(f"<div class='settings-summary'>Your schedule runs <strong>{ds:02d}:00 – {de:02d}:00</strong>, max <strong>{mh} hours/day</strong>, <strong>{bm} min</strong> breaks between sessions. Weekends: <strong>{'Included' if inc_weekends else 'Excluded'}</strong>. Style: <strong>{study_style}</strong>.</div>", unsafe_allow_html=True)

    with st.form("settings_form"):
        st.subheader("Scheduling Defaults")

        st.markdown("<div class='form-section-label'>Working Hours</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        day_start = c1.number_input("Day Start Hour", min_value=0, max_value=23, value=ds, help="The earliest hour the AI will schedule tasks.")
        day_end = c2.number_input("Day End Hour", min_value=0, max_value=23, value=de, help="The latest hour the AI will schedule tasks.")

        st.markdown("<div class='form-section-label'>Session Limits</div>", unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        max_hours = c3.number_input("Max Study Hours/Day", min_value=1, max_value=12, value=mh, help="Maximum total study hours the AI will schedule in a single day.")
        break_mins = c4.number_input("Default Break (mins)", min_value=0, max_value=60, value=bm, help="Break time inserted between study sessions.")

        st.markdown("<div class='form-section-label'>Preferences</div>", unsafe_allow_html=True)
        c5, c6 = st.columns(2)
        include_weekends = c5.checkbox("Include Weekends", value=inc_weekends, help="Allow the AI to schedule tasks on Saturday and Sunday.")
        study_style_val = c6.selectbox("Study Style", ["Balanced", "Short Bursts (30-45 min)", "Deep Work (90+ min)"], index=["Balanced", "Short Bursts (30-45 min)", "Deep Work (90+ min)"].index(study_style) if study_style in ["Balanced", "Short Bursts (30-45 min)", "Deep Work (90+ min)"] else 0, help="Tells the scheduler how you prefer to work.")

        if st.form_submit_button("Save Preferences", type="primary", use_container_width=True):
            new_prefs = {"day_start": str(day_start), "day_end": str(day_end), "max_hours": str(max_hours), "break_mins": str(break_mins), "include_weekends": "1" if include_weekends else "0", "study_style": study_style_val}
            for k, v in new_prefs.items():
                cursor.execute("INSERT OR REPLACE INTO user_preferences (key, value) VALUES (?, ?)", (k, v))
            conn.commit()
            st.success("Settings saved.")

    st.markdown("---")
    st.markdown("### Danger Zone")
    st.caption("This will permanently delete all your tasks, progress, and completion history. This cannot be undone.")

    if 'confirm_reset' not in st.session_state:
        st.session_state.confirm_reset = False

    if not st.session_state.confirm_reset:
        if st.button(":material/warning: Reset Database"):
            st.session_state.confirm_reset = True
            st.rerun()
    else:
        st.warning("Are you sure? Type **RESET** below to confirm.")
        confirm_text = st.text_input("Type RESET to confirm", key="reset_confirm_input")
        col1, col2 = st.columns(2)
        if col1.button("Confirm Reset", type="primary"):
            if confirm_text == "RESET":
                cursor.execute("DELETE FROM tasks"); cursor.execute("DELETE FROM completion_log"); conn.commit()
                st.session_state.confirm_reset = False
                st.rerun()
            else:
                st.error("Type RESET exactly to confirm.")
        if col2.button("Cancel"):
            st.session_state.confirm_reset = False
            st.rerun()

    conn.close()

if __name__ == "__main__":
    main()