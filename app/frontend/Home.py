import sys
from pathlib import Path

# --- MAGIC PATH FIX ---
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

import streamlit as st
from datetime import date
from app.backend.data_service import load_tasks, save_tasks

st.set_page_config(page_title="Task Hub", page_icon="🏠", layout="wide")

def main():
    st.title("🏠 Task Hub")
    st.markdown("### 📌 Capture & Manage Tasks")

    # 1. Load Data
    if "tasks" not in st.session_state:
        st.session_state.tasks = load_tasks()

    # 2. Add Task Form
    with st.expander("➕ Add New Task", expanded=True):
        with st.form("add_task_form"):
            c1, c2 = st.columns([2, 1])
            name = c1.text_input("Task Name", placeholder="e.g. Write Dissertation Abstract")
            priority = c2.selectbox("Priority", ["High", "Medium", "Low"])

            c3, c4 = st.columns([1, 1])
            duration = c3.number_input("Duration (mins)", min_value=15, step=15, value=60)
            deadline = c4.date_input("Deadline", min_value=date.today(), format="DD/MM/YYYY")

            # --- NEW: Notes Field ---
            notes = st.text_area("Notes / Details", placeholder="Add links, reminders, or sub-tasks here...", height=80)

            if st.form_submit_button("Add to List"):
                new_task = {
                    "id": str(len(st.session_state.tasks) + 1),
                    "name": name,
                    "duration_minutes": duration,
                    "priority": priority.lower(),
                    "deadline": deadline,
                    "notes": notes,
                    "fixed_slot": None
                }
                st.session_state.tasks.append(new_task)
                save_tasks(st.session_state.tasks)
                st.rerun()

    # 3. Task List
    st.markdown("---")
    st.subheader(f"📋 Your Inbox ({len(st.session_state.tasks)})")

    if not st.session_state.tasks:
        st.info("No tasks yet. Add one above!")
    else:
        tasks_to_keep = []
        for t in st.session_state.tasks:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
                c1.markdown(f"**{t['name']}**")
                c2.caption(f"⏳ {t['duration_minutes']}m")
                p_icon = "🔴" if t['priority'] == "high" else "🟡" if t['priority'] == "medium" else "🟢"
                c3.caption(f"{p_icon} {t['priority'].title()}")

                if c4.button("🗑️", key=f"del_{t['id']}"):
                    pass
                else:
                    tasks_to_keep.append(t)

                if t.get('notes'):
                    with st.expander("📝 View Notes"):
                        st.write(t['notes'])

        if len(tasks_to_keep) != len(st.session_state.tasks):
            st.session_state.tasks = tasks_to_keep
            save_tasks(tasks_to_keep)
            st.rerun()

if __name__ == "__main__":
    main()