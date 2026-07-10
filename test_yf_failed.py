import yfinance as yf

for sym in ["PAGEIND.NS", "SHREECEM.NS"]:
    ticker = yf.Ticker(sym)
    hist = ticker.history(period="5d", interval="5m")
    dates = hist.index.date
    latest_date = dates[-1]
    day_data = hist[hist.index.date == latest_date]
    print(f"\n{sym} on {latest_date}")
    print(day_data.head(2))
