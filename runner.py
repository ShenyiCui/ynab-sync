import schedule
import time
from datetime import datetime
import pytz
import subprocess
import os
import logging

LOG_FILE = "logs/runner.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def log_print(*args, **kwargs):
    """Print to console and log to file."""
    msg = " ".join(str(a) for a in args)
    print(msg, **kwargs)
    logging.info(msg)


UK_TZ = pytz.timezone("Europe/London")

# Paths to scripts
BASE_DIR = os.path.dirname(__file__)
S27_MAIN = os.path.join(BASE_DIR, "s27", "main.py")
T212_MAIN = os.path.join(BASE_DIR, "212-trading", "main.py")

def run_s27():
    now_str = datetime.now(UK_TZ).isoformat()
    log_print(f"[S27] Running main.py at {now_str}")
    subprocess.run(["python", S27_MAIN], check=True)

def run_212_trading():
    now_str = datetime.now(UK_TZ).isoformat()
    log_print(f"[212 Trading] Running main.py at {now_str}")
    subprocess.run(["python", T212_MAIN], check=True)

# Schedule both jobs at 23:59 UK time daily
schedule.every().day.at("12:48").do(run_s27)
schedule.every().day.at("12:48").do(run_212_trading)

log_print("Scheduler started...")
while True:
    schedule.run_pending()
    time.sleep(30)  # check every 30 seconds
