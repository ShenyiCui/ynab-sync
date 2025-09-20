from datetime import datetime
import pytz
import subprocess
import os
import logging

# --- Logging setup ---
LOG_FILE = "logs/runner.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def log_print(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    print(msg, **kwargs)
    logging.info(msg)

UK_TZ = pytz.timezone("Europe/London")
BASE_DIR = os.path.dirname(__file__)
S27_MAIN = os.path.join(BASE_DIR, "s27", "main.py")
T212_MAIN = os.path.join(BASE_DIR, "212-trading", "main.py")

# --- Scheduled tasks ---
def run_s27():
    now_str = datetime.now(UK_TZ).isoformat()
    log_print(f"[S27] Running main.py at {now_str}")
    subprocess.run(["python", S27_MAIN], check=True)

def run_212_trading():
    now_str = datetime.now(UK_TZ).isoformat()
    log_print(f"[212 Trading] Running main.py at {now_str}")
    subprocess.run(["python", T212_MAIN], check=True)

def run_both():
    run_s27()
    run_212_trading()

if __name__ == "__main__":
  run_both()