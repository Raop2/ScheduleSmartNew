"""
build.py — PyInstaller Build Script
Bundles the entire application into a standalone Windows executable.
Configures hidden imports for Streamlit, OR-Tools, and Pydantic that
PyInstaller cannot detect automatically. Output: dist/ScheduleSmart/
"""
import subprocess
import sys

build_command = [
    sys.executable, "-m", "PyInstaller",
    "launcher.py",
    "--name=ScheduleSmart",
    "--onedir",
    "--windowed",
    "--icon=app/frontend/logo.jpg",
    "--collect-all=streamlit",
    "--collect-all=streamlit_option_menu",
    "--collect-all=streamlit_calendar",
    "--collect-all=altair",
    "--collect-all=ortools",
    "--collect-all=pydantic",
    "--copy-metadata=streamlit",
    "--copy-metadata=streamlit_option_menu",
    "--copy-metadata=streamlit_calendar",
    "--add-data=app;app",
    "--add-data=.streamlit;.streamlit",
    "--hidden-import=streamlit.runtime.scriptrunner.magic_funcs",
    "--hidden-import=streamlit.runtime.caching",
    "--hidden-import=streamlit_calendar",
    "--hidden-import=streamlit_option_menu",
    "--hidden-import=ortools",
    "--hidden-import=google.protobuf",
    "--hidden-import=icalendar",
    "--hidden-import=pandas",
    "--hidden-import=matplotlib",
    "--hidden-import=sqlite3",
]

print("Building ScheduleSmart desktop application...")
print("This may take several minutes...")
print()
print("Command:", " ".join(build_command))
print()

result = subprocess.run(build_command)

if result.returncode == 0:
    print()
    print("Build successful!")
    print("Your executable is in: dist/ScheduleSmart/")
    print("Run: dist/ScheduleSmart/ScheduleSmart.exe")
else:
    print()
    print("Build failed. Check the errors above.")