import sys
import os
from pathlib import Path

if getattr(sys, 'frozen', False):
    base_dir = Path(sys._MEIPASS)
else:
    base_dir = Path(__file__).parent

os.chdir(str(base_dir))
sys.path.insert(0, str(base_dir))

from streamlit.web import cli as stcli

if __name__ == "__main__":
    home_path = str(base_dir / "app" / "frontend" / "Home.py")
    sys.argv = [
        "streamlit", "run", home_path,
        "--global.developmentMode=false",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--theme.primaryColor=#1A73E8",
        "--theme.backgroundColor=#F8FAFC",
        "--theme.secondaryBackgroundColor=#FFFFFF",
        "--theme.textColor=#1E293B",
    ]
    stcli.main()