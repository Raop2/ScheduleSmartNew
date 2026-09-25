ScheduleSmart

An intelligent, cross-platform study scheduling system that turns a student's tasks, classes, exams and study goals into a balanced weekly timetable. Built entirely in Python.

ScheduleSmart was developed as my final-year BSc Computer Science project at London South Bank University, where it was awarded a first-class mark (70).

Overview

Most study planners just store a to-do list. ScheduleSmart actually builds the schedule for you. You add what you need to do and when it's due, and the app generates a timetable using one of two scheduling engines, checks it for clashes, scores its quality, and lets you refine it. It runs as a web app and as a standalone Windows program.

Key features
Two scheduling engines. A fast greedy heuristic and a CP-SAT constraint optimiser (Google OR-Tools), with a side-by-side comparison so you can see how each one lays out your week.
Quality scoring. Every generated schedule is scored from 0 to 100 on deadline compliance and workload balance, with suggestions for improving it.
Conflict detection and resolution. Overlapping tasks are detected automatically and can be re-solved into the nearest free slot with one click.
Curriculum engine. Recognises a wide range of academic subjects and generates structured study plans with topics in a sensible learning order.
Visual calendar. A weekly calendar view with colour-coded priorities, overdue detection and inline editing.
Focus mode and analytics. Guided study sessions plus a dashboard showing completion trends, activity and streaks.
Accounts and guest mode. Sign-up and sign-in with hashed passwords, or jump straight in as a guest.
Calendar export. Export any schedule to Google Calendar, Apple Calendar or Outlook via .ics.
Offline desktop build. Ships as a standalone Windows .exe that runs without Python installed.
Tech stack
Layer	Technology
Frontend	Python, Streamlit, streamlit-calendar, streamlit-option-menu
Backend	Python, FastAPI
Scheduling	Google OR-Tools (CP-SAT), custom greedy algorithm
Database	SQLite
Authentication	SHA-256 password hashing
Export	iCalendar (.ics)
Testing	pytest (95 tests across 16 test classes)
Desktop build	PyInstaller
Deployment	Streamlit Cloud
How it works

The two engines solve the same problem in different ways:

Greedy engine. Places tasks one at a time into the best available slot. It's fast and predictable, and works well when the week isn't heavily loaded.
CP-SAT engine. Models the whole week as a constraint-satisfaction problem and searches for a globally balanced solution. When slots are scarce, it spreads work more intelligently than the greedy approach.

Running both on the same input and comparing the quality scores is the clearest way to see the difference the optimiser makes.

Getting started
Prerequisites
Python 3.11 or newer
pip
Installation
bash
# Clone the repository
git clone https://github.com/Raop2/ScheduleSmartNew.git
cd ScheduleSmartNew

# Create and activate a virtual environment
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
Running the app
bash
streamlit run app/frontend/Home.py

The app opens at http://localhost:8501.

Testing

The project includes 95 unit tests across 16 test classes, covering the scheduling engines, conflict detection, quality scoring and the curriculum engine.

bash
pytest
Author

Raphael McCully — BSc (Hons) Computer Science, London South Bank University (2026). Supervised by Francis Babayemi.

Licence

This project was produced as academic coursework. Please contact me before reusing it.
