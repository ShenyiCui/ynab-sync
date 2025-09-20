# Fetch Trading212 portfolio value, compare to YNAB account balance, and create a YNAB transaction
# Assumes Trading212 "total" is in GBP. If it's a different currency, convert before creating the transaction.
# Requirements: python-dotenv, requests, ynab-sdk, pytz
#
# .env must contain:
#   TRADING_ACCESS_TOKEN=<your trading212 bearer token>
#   PAT=<your YNAB personal access token>

import os
from dotenv import load_dotenv
import requests
import ynab
from ynab.models.post_transactions_wrapper import PostTransactionsWrapper
from datetime import datetime, date
import pytz
import logging


# --------------------------
# Config / constants
# --------------------------
MAIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # root dir
LOG_FILE = os.path.join(MAIN_DIR, "logs/212-trading.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

load_dotenv()
TRADING_ACCESS_TOKEN = os.getenv("TRADING_ACCESS_TOKEN")
YNAB_TOKEN = os.getenv("YNAB_ACCESS_TOKEN")

# YNAB
BUDGET_ID = os.getenv("BUDGET_ID")
TRADING_212_ACCOUNT_ID = os.getenv("TRADING_212_ID")

# Trading212 API endpoint (from your snippet)
T212_URL = "https://live.trading212.com/api/v0/equity/account/cash"

# Tolerance threshold (GBP)
MIN_GBP = 0.01

# UK timezone for memo
UK_TZ = pytz.timezone("Europe/London")

# --------------------------
# Helper
# --------------------------
def log_print(*args, **kwargs):
    """Print to console and log to file."""
    msg = " ".join(str(a) for a in args)
    print(msg, **kwargs)
    logging.info(msg)

def get_trading212_total(url: str, token: str):
    if not token:
        raise RuntimeError("Trading212 access token not set in TRADING_ACCESS_TOKEN")
    headers = {"Authorization": token}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    j = r.json()
    # assume j["total"] exists and is numeric
    return float(j["total"])

def get_ynab_account_balance_gbp(api_client, budget_id: str, account_id: str) -> float:
    accounts_api = ynab.AccountsApi(api_client)
    resp = accounts_api.get_account_by_id(budget_id, account_id)
    # YNAB returns balance in milliunits (e.g., 1 GBP == 1000)
    return resp.data.account.balance / 1000.0

def create_ynab_transaction(api_client, budget_id: str, account_id: str, amount_gbp: float, memo_str: str):
    # YNAB expects amounts in milliunits as integers
    milli = int(round(amount_gbp * 1000))
    txn = {
        "account_id": account_id,
        "date": date.today().isoformat(),
        "amount": milli,
        "payee_name": "Stock",
        "memo": memo_str
    }
    wrapper = PostTransactionsWrapper(transactions=[txn])
    tx_api = ynab.TransactionsApi(api_client)
    return tx_api.create_transaction(budget_id, wrapper)

# --------------------------
# Main flow
# --------------------------
def main():
    # fetch trading212 portfolio total
    try:
        t212_total_gbp = get_trading212_total(T212_URL, TRADING_ACCESS_TOKEN)
    except Exception as e:
        log_print("Error fetching Trading212 total:", e)
        return

    # prepare timestamp for memo (UK time)
    now_uk = datetime.now(pytz.UTC).astimezone(UK_TZ)
    memo = now_uk.strftime("%d/%m/%Y %H:%M")

    # open YNAB client
    if not YNAB_TOKEN:
        log_print("YNAB token not found in .env under YNAB_ACCESS_TOKEN")
        return

    configuration = ynab.Configuration(access_token=YNAB_TOKEN)
    try:
        with ynab.ApiClient(configuration) as api_client:
            # get current YNAB account balance for Trading212 account (GBP)
            try:
                ynab_balance_gbp = get_ynab_account_balance_gbp(api_client, BUDGET_ID, TRADING_212_ACCOUNT_ID)
            except Exception as e:
                print("Error fetching YNAB account balance:", e)
                return

            # compute difference: how much portfolio value differs from YNAB
            diff_gbp = t212_total_gbp - ynab_balance_gbp

            # Print a quick summary (sanity check)
            log_print("------------------Trading212 sync start------------------")
            log_print("Trading212 total (GBP):", f"{t212_total_gbp:.2f}")
            log_print("YNAB recorded balance (GBP):", f"{ynab_balance_gbp:.2f}")
            log_print("Difference (Trading212 - YNAB) GBP:", f"{diff_gbp:.5f}")

            # Only create a transaction if difference exceeds threshold
            if abs(diff_gbp) < MIN_GBP:
                log_print("Difference below threshold. No transaction created.")
                log_print("------------------Trading212 sync end------------------")
                return

            # Create a single transaction to reflect the difference (payee "Stock", memo = UK datetime)
            try:
                response = create_ynab_transaction(api_client, BUDGET_ID, TRADING_212_ACCOUNT_ID, diff_gbp, memo)
                log_print("YNAB transaction created. Response:")
                log_print(response)
                log_print("------------------Trading212 sync end------------------")
            except Exception as e:
                log_print("Error creating YNAB transaction:", e)
                log_print("------------------Trading212 sync end------------------")
                return                

    except Exception as e:
        log_print("YNAB API client error:", e)
        return

if __name__ == "__main__":
    main()
