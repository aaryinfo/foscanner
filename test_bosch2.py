import yfinance as yf

ticker = yf.Ticker("BOSCHLTD.NS")
hist = ticker.history(period="5d", interval="5m")
dates = hist.index.date
latest_date = dates[-1]
day_data = hist[hist.index.date == latest_date]
print("\nBOSCHLTD.NS Lowest Low:", day_data['Low'].min())
