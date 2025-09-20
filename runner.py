import schedule
import time
from datetime import datetime
import pytz
import subprocess
import os

UK_TZ = pytz.timezone("Europe/London")
S27_DIR = os.path.join(os.path.dirname(__file__), "s27")
MAIN_PY = os.path.join(S27_DIR, "main.py")

def run_main():
    print(f"Running main.py at {datetime.now(UK_TZ).isoformat()}")
    subprocess.run(["python", MAIN_PY], check=True)

# Schedule job at 23:59 UK time daily
schedule.every().day.at("23:59").do(run_main)

print("Scheduler started...")
while True:
    schedule.run_pending()
    time.sleep(30)  # check every 30 seconds
