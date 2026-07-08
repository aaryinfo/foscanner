import sqlite3
import json
import yfinance as yf
from datetime import datetime
import pandas as pd
import os

def get_summary():
    db_path = 'auth.db'
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return
        
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Get the latest scan_date
    c.execute("SELECT MAX(scan_date) FROM screener_results")
    row = c.fetchone()
    if not row or not row[0]:
        print("No scan data found.")
        return
    
    latest_date = row[0]
    print(f"Latest scan date: {latest_date}")
    
    c.execute("SELECT market, results_json FROM screener_results WHERE scan_date = ?", (latest_date,))
    rows = c.fetchall()
    
    all_picks = []
    
    for market, results_json in rows:
        try:
            results = json.loads(results_json)
        except:
            continue
            
        for r in results:
            # Check if it passed the filter. 
            # Looking at how it's done in gann_dashboard, maybe it's just in the results.
            # We'll take all results that have entry targets.
            trend = r.get("reversal_type", "")
            symbol = r.get("symbol", "")
            
            intra = r.get("intraday_sq9", {})
            if not intra:
                continue
                
            entry = intra.get("entry_level")
            sl = intra.get("sl_level")
            # T1 or Target
            target = intra.get("target_level") 
            if not target or target == "NONE":
                target = intra.get("t1")
                
            if entry and sl and target:
                all_picks.append({
                    "symbol": symbol,
                    "market": market,
                    "trend": trend,
                    "entry": float(entry),
                    "target": float(target),
                    "sl": float(sl)
                })
    
    if not all_picks:
        print("No picks found.")
        return
        
    print(f"Found {len(all_picks)} picks.")
    
    symbols = [p["symbol"] for p in all_picks]
    # Fetch yfinance data
    print(f"Fetching yfinance data for {symbols}...")
    try:
        hist = yf.download(symbols, period="5d", group_by="ticker", auto_adjust=False)
    except Exception as e:
        print(f"yfinance download error: {e}")
        return
        
    report = []
    success_count = 0
    total_count = 0
    
    for p in all_picks:
        sym = p["symbol"]
        try:
            if len(symbols) == 1:
                df = hist
            else:
                df = hist[sym] if sym in hist.columns.levels[0] else None
                
            if df is None or df.empty:
                print(f"No data for {sym}")
                continue
                
            last_bar = df.iloc[-1]
            high = float(last_bar["High"])
            low = float(last_bar["Low"])
            close = float(last_bar["Close"])
            
            status = "PENDING"
            if p["trend"] == "BULL REVERSAL":
                if high >= p["target"]:
                    status = "SUCCESS"
                elif low <= p["sl"]:
                    status = "FAILED"
            else: # BEAR REVERSAL
                if low <= p["target"]:
                    status = "SUCCESS"
                elif high >= p["sl"]:
                    status = "FAILED"
            
            if status != "PENDING":
                total_count += 1
                if status == "SUCCESS":
                    success_count += 1
                    
            p["actual_high"] = round(high, 2)
            p["actual_low"] = round(low, 2)
            p["actual_close"] = round(close, 2)
            p["status"] = status
            report.append(p)
            
        except Exception as e:
            print(f"Error processing {sym}: {e}")
            
    print(json.dumps(report, indent=2))
    
    if total_count > 0:
        print(f"Success Rate: {success_count/total_count*100:.2f}%")
    else:
        print("No triggered trades.")

if __name__ == "__main__":
    get_summary()
