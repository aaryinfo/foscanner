import yfinance as yf
import pandas as pd
import time
from gann_app import FNO_STOCKS, GLOBAL_ASSETS

print("Starting automated data update...")

# --- UPDATE NSE F&O DATA ---
print("\n[1/2] Updating NSE F&O Data (20y)...")
nse_symbols = [item["symbol"] for item in FNO_STOCKS]
nse_tickers = [s + ".NS" for s in nse_symbols]

try:
    nse_data = yf.download(nse_tickers, period="20y", interval="1d", progress=False, group_by="ticker", threads=False)
    nse_data.to_csv("gann_data_20y.csv.gz", compression="gzip")
    print(f"✅ Successfully updated gann_data_20y.csv.gz ({len(nse_symbols)} symbols)")
except Exception as e:
    print(f"❌ Failed to update NSE data: {e}")

# --- UPDATE GLOBAL ASSETS DATA ---
print("\n[2/2] Updating Global Assets Data (10y)...")
global_symbols = [item["symbol"] for item in GLOBAL_ASSETS]

try:
    global_data = yf.download(global_symbols, period="10y", interval="1d", progress=False, group_by="ticker", threads=False)
    global_data.to_csv("gann_data_global.csv.gz", compression="gzip")
    print(f"✅ Successfully updated gann_data_global.csv.gz ({len(global_symbols)} symbols)")
except Exception as e:
    print(f"❌ Failed to update Global data: {e}")

print("\nUpdate process completed successfully!")
