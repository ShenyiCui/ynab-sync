import os
from dotenv import load_dotenv
import ynab
from ynab.models.post_transactions_wrapper import PostTransactionsWrapper
import yfinance as yf
from datetime import datetime, timezone, date
import pytz

# --------------------------
# 0) Persistent storage
# --------------------------
PREV_FILE = "prev_values.txt"

def read_prev_values(file_path):
    if not os.path.exists(file_path):
        return None, None
    with open(file_path, "r") as f:
        lines = f.readlines()
        if len(lines) >= 2:
            prev_price = float(lines[0].strip())
            prev_fx = float(lines[1].strip())
            return prev_price, prev_fx
    return None, None

def save_prev_values(file_path, price, fx):
    with open(file_path, "w") as f:
        f.write(f"{price}\n{fx}\n")

# --------------------------
# 1) Load env & config
# --------------------------
load_dotenv()
access_token = os.getenv("PAT")

BUDGET_ID = "ee92cdb7-0081-4dc5-8e04-4f3f2c386d74"
S27_INDEX_ACCOUNT_ID = "8d74bce4-3b5f-41eb-bb9d-976c62ba4a2b"
S27_SHARES_OWN = 54

configuration = ynab.Configuration(access_token=access_token)

# --------------------------
# 2) Fetch market data
# --------------------------
ticker = yf.Ticker("S27.SI")
info = ticker.info
last_price = info.get("regularMarketPrice")  # USD
timestamp = info.get("regularMarketTime")

# Convert to UK timezone
uk_tz = pytz.timezone("Europe/London")
if timestamp:
    date_fetched = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(uk_tz)
else:
    date_fetched = datetime.now(uk_tz)

fx_ticker = yf.Ticker("GBPUSD=X")
fx_info = fx_ticker.info
gbp_usd_rate = fx_info.get("regularMarketPrice")  # USD per GBP

# --------------------------
# 3) Fetch current YNAB S27 balance
# --------------------------
with ynab.ApiClient(configuration) as api_client:
    accounts_api = ynab.AccountsApi(api_client)
    s27_accounts_response = accounts_api.get_account_by_id(BUDGET_ID, S27_INDEX_ACCOUNT_ID)
    s27_account_balance_gbp = s27_accounts_response.data.account.balance / 1000.0

# --------------------------
# 4) Read previous values
# --------------------------
prev_price_usd, prev_gbp_usd_rate = read_prev_values(PREV_FILE)
if prev_price_usd is None or prev_gbp_usd_rate is None:
    prev_price_usd = last_price
    prev_gbp_usd_rate = gbp_usd_rate

# --------------------------
# 5) Compute totals & diffs
# --------------------------
shares = S27_SHARES_OWN
P_prev = float(prev_price_usd)
R_prev = float(prev_gbp_usd_rate)
P_curr = float(last_price)
R_curr = float(gbp_usd_rate)

price_effect_gbp = shares * (P_curr - P_prev) / R_curr
fx_effect_gbp = shares * P_prev * (1.0 / R_curr - 1.0 / R_prev)

txn_date = date.today().isoformat()

# --------------------------
# 6) Create YNAB transactions
# --------------------------
MIN_GBP = 0.01  # Minimum threshold to log a transaction

if abs(price_effect_gbp) < MIN_GBP and abs(fx_effect_gbp) < MIN_GBP:
    print("Both price and FX effects are negligible. No transactions created.")
else:
    transactions = []
    if abs(price_effect_gbp) >= MIN_GBP:
        transactions.append({
            "account_id": S27_INDEX_ACCOUNT_ID,
            "date": txn_date,
            "amount": int(price_effect_gbp * 1000),  # milliunits
            "payee_name": "Stock",
            "memo": f"Price: USD {P_curr:.2f} DT: {date_fetched.strftime('%d/%m/%Y %H:%M')}"
        })
    if abs(fx_effect_gbp) >= MIN_GBP:
        transactions.append({
            "account_id": S27_INDEX_ACCOUNT_ID,
            "date": txn_date,
            "amount": int(fx_effect_gbp * 1000),  # milliunits
            "payee_name": "USD-GBP FX",
            "memo": f"USD/GBP: {R_curr:.5f}"
        })

    with ynab.ApiClient(configuration) as api_client:
        transactions_api = ynab.TransactionsApi(api_client)
        wrapper = PostTransactionsWrapper(transactions=transactions)
        try:
            response = transactions_api.create_transaction(BUDGET_ID, wrapper)
            print("Transactions successfully created:")
            print(response)
        except Exception as e:
            print("Error creating transactions:", e)

# --------------------------
# 7) Save current values for next run
# --------------------------
save_prev_values(PREV_FILE, last_price, gbp_usd_rate)

# --------------------------
# 8) Print summary & sanity check
# --------------------------
current_total_gbp = ((shares * last_price) / gbp_usd_rate)
balance_diff = current_total_gbp - s27_account_balance_gbp

print("\nSummary:")
print(f"last_price (USD): {last_price}")
print(f"date_fetched (UK): {date_fetched.isoformat()}")
print(f"price_effect_gbp: {price_effect_gbp:.2f}")
print(f"fx_effect_gbp: {fx_effect_gbp:.2f}\n")

print(f"total_effect_gbp (price + FX): {(price_effect_gbp + fx_effect_gbp):.2f}")
print(f"balance_diff (current - previous_total): {balance_diff:.2f}")
print(f"Check: total_effect_gbp ≈ balance_diff? {abs((price_effect_gbp + fx_effect_gbp) - balance_diff) < 0.02}")
