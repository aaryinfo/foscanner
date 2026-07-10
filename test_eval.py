import yfinance as yf
from datetime import datetime

setup = {
    "symbol": "RELIANCE.NS",
    "entry": 2900,
    "t1": 2950,
    "sl": 2880,
    "signal": "BULL REVERSAL"
}

ticker = yf.Ticker(setup["symbol"])
hist = ticker.history(period="5d", interval="5m")

if not hist.empty:
    dates = hist.index.date
    latest_date = dates[-1]
    day_data = hist[hist.index.date == latest_date]
    
    entry = setup["entry"]
    t1 = setup["t1"]
    sl = setup["sl"]
    is_bull = "BULL" in setup["signal"].upper()
    
    triggered = False
    trigger_time = None
    outcome = "Open"
    
    for index, row in day_data.iterrows():
        low = row['Low']
        high = row['High']
        
        if not triggered:
            if is_bull and low <= entry:
                triggered = True
                trigger_time = index.strftime("%H:%M")
            elif not is_bull and high >= entry:
                triggered = True
                trigger_time = index.strftime("%H:%M")
                
        if triggered:
            if is_bull:
                if low <= sl:
                    outcome = "Failed"
                    break
                elif high >= t1:
                    outcome = "Success"
                    break
            else:
                if high >= sl:
                    outcome = "Failed"
                    break
                elif low <= t1:
                    outcome = "Success"
                    break

    print(f"Triggered: {triggered}, Time: {trigger_time}, Outcome: {outcome}")
