import yfinance as yf
import pandas as pd

# Test ICICIBANK
data = yf.download("ICICIBANK.NS", period="10y", interval="1mo", progress=False)

if isinstance(data.columns, pd.MultiIndex):
    df = data["ICICIBANK.NS"].dropna()
else:
    df = data.dropna()

close = df["Close"]

ema9 = close.ewm(span=9, adjust=False).mean()
ema20 = close.ewm(span=20, adjust=False).mean()

delta = close.diff()
gain = delta.where(delta > 0, 0.0)
loss = -delta.where(delta < 0, 0.0)
avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))

print("Last 6 months EMAs:")
for i in range(-6, 0):
    print(f"Date: {df.index[i].date()}, Close: {close.iloc[i]:.2f}, EMA9: {ema9.iloc[i]:.2f}, EMA20: {ema20.iloc[i]:.2f}, RSI: {rsi.iloc[i]:.2f}")

cross_bull = False
for offset in range(-6, 0):
    if ema9.iloc[offset] > ema20.iloc[offset] and ema9.iloc[offset-1] <= ema20.iloc[offset-1]:
        cross_bull = True

print(f"Bull Cross in last 6 months: {cross_bull}")
