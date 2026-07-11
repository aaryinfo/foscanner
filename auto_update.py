import yfinance as yf
import pandas as pd
import time
from gann_app import FNO_STOCKS, GLOBAL_ASSETS

print("Starting automated data update...")

# --- UPDATE NSE F&O DATA ---
print("\n[1/2] Updating NSE F&O Data (20y)...")
nse_symbols = [item["symbol"] for item in FNO_STOCKS]
nse_tickers = [s + ".NS" if not s.endswith(".NS") and not s.startswith("^") else s for s in nse_symbols]

try:
    nse_data = yf.download(nse_tickers, period="20y", interval="1d", progress=False, group_by="ticker", threads=False)
    nse_data.to_csv("gann_data_20y.csv.gz", compression="gzip")
    print(f"[OK] Successfully updated gann_data_20y.csv.gz ({len(nse_symbols)} symbols)")
except Exception as e:
    print(f"[ERROR] Failed to update NSE data: {e}")

# --- UPDATE GLOBAL ASSETS DATA ---
print("\n[2/2] Updating Global Assets Data (10y)...")
global_symbols = [item["symbol"] for item in GLOBAL_ASSETS]

try:
    global_data = yf.download(global_symbols, period="10y", interval="1d", progress=False, group_by="ticker", threads=False)
    global_data.to_csv("gann_data_global.csv.gz", compression="gzip")
    print(f"[OK] Successfully updated gann_data_global.csv.gz ({len(global_symbols)} symbols)")
except Exception as e:
    print(f"[ERROR] Failed to update Global data: {e}")

print("\n[3/3] Generating Astro Forecast (-90 to +10 days)...")
try:
    from datetime import datetime, timedelta
    import json
    from market_modules.scoring import calculate_daily_astro_score, calculate_sector_bias
    
    forecast = []
    base_date = datetime.utcnow()
    for i in range(-90, 15):
        target_date = base_date + timedelta(days=i)
        score_data = calculate_daily_astro_score(target_date)
        sector_bias = calculate_sector_bias(target_date)
        forecast.append({
            "date": score_data['date'],
            "score": score_data['score'],
            "bias": score_data['bias'],
            "nakshatra": score_data['nakshatra'],
            "tithi": score_data['tithi'],
            "eclipse": score_data['eclipse'],
            "numerology_vib": score_data['numerology'],
            "sector_bias": sector_bias,
            "sun_long": score_data.get('sun_long', 30.0),
            "moon_long": score_data.get('moon_long', 150.0)
        })
    
    with open('astro_forecast.json', 'w', encoding='utf-8') as f:
        json.dump(forecast, f, indent=4)
    print(f"[OK] Successfully generated astro_forecast.json")

    print("\n[4/4] Generating Top 5 Turn Date Stocks for Today...")
    from market_modules.data_fetcher import get_all_tickers, get_current_price
    from market_modules.scoring import get_top_5_turn_date_stocks
    
    tickers = get_all_tickers()
    current_prices = {}
    for t in tickers:
        p = get_current_price(t)
        if p:
            current_prices[t] = p
            
    top_5 = get_top_5_turn_date_stocks(base_date, tickers, current_prices)
    
    with open('top_stocks.json', 'w', encoding='utf-8') as f:
        json.dump(top_5, f, indent=4)
    print(f"[OK] Successfully generated top_stocks.json")

except Exception as e:
    import traceback
    print(f"[ERROR] Failed to generate Astro forecast: {e}")
    traceback.print_exc()

print("\nUpdate process completed successfully!")
