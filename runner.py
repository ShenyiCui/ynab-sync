import schedule
import time
from datetime import datetime
import pytz
import subprocess
import os
import logging
from flask import Flask, jsonify
import threading

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

# --- Timezone & paths ---
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

# --- Schedule jobs (UK time) ---
schedule.every().day.at("23:59").do(run_s27)
schedule.every().day.at("23:59").do(run_212_trading)

# --- Flask web service ---
app = Flask(__name__)

@app.route("/")
def health():
    return jsonify({"status": "running", "message": "Scheduler active"}), 200

@app.route("/run_s27")
def trigger_s27():
    threading.Thread(target=run_s27).start()
    return jsonify({"status": "ok", "message": "S27 triggered"}), 200

@app.route("/run_212")
def trigger_212():
    threading.Thread(target=run_212_trading).start()
    return jsonify({"status": "ok", "message": "212 trading triggered"}), 200

@app.route("/run_all")
def trigger_all():
    threading.Thread(target=run_both).start()
    return jsonify({"status": "ok", "message": "Both scripts triggered"}), 200

# --- Scheduler runner in background ---
def run_scheduler():
    log_print("Scheduler started...")
    while True:
        schedule.run_pending()
        time.sleep(30)

threading.Thread(target=run_scheduler, daemon=True).start()

# --- Start Flask server ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render sets $PORT
    app.run(host="0.0.0.0", port=port)
