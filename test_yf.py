import yfinance as yf

ticker = yf.Ticker("RELIANCE.NS")
hist = ticker.history(period="5d", interval="5m")
print(hist.tail())
print("Unique dates:")
print(hist.index.date)
