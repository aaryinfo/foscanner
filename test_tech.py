import yfinance as yf
import pandas as pd
from gann_app import FNO_STOCKS

symbols = [item["symbol"] for item in FNO_STOCKS]
tickers = [s + ".NS" for s in symbols]

data = yf.download(tickers, period="3y", interval="1mo", progress=False, group_by="ticker", threads=True)

for i, ticker in enumerate(tickers):
    sym = symbols[i]
    try:
        if isinstance(data.columns, pd.MultiIndex):
            if ticker not in data.columns.levels[0]: continue
            df = data[ticker].dropna()
        else:
            if len(tickers) == 1: df = data.dropna()
            else: continue
            
        if len(df) < 20: continue
            
        close = df["Close"]
        ema9 = close.ewm(span=9, adjust=False).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        crossed_bull = False
        for offset in range(-6, 0):
            if ema9.iloc[offset] > ema20.iloc[offset] and ema9.iloc[offset-1] <= ema20.iloc[offset-1]:
                crossed_bull = True
                break
                
        crossed_bear = False
        for offset in range(-6, 0):
            if ema9.iloc[offset] < ema20.iloc[offset] and ema9.iloc[offset-1] >= ema20.iloc[offset-1]:
                crossed_bear = True
                break
                
        recent_highs = df["High"].iloc[-6:-1]
        recent_lows = df["Low"].iloc[-6:-1]
        range_pct = (recent_highs.max() - recent_lows.min()) / recent_lows.min()
        
        current_rsi = rsi.iloc[-1]
        
        is_cross = crossed_bull or crossed_bear
        is_range = range_pct < 0.25
        is_rsi = 40 <= current_rsi <= 60
        
        if is_cross and is_range and is_rsi:
            print(f"{sym}: Cross! Range={range_pct:.2f}, RSI={current_rsi:.2f}")
            
    except Exception as e:
        pass
