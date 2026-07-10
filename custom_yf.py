import urllib.request
import json
import pandas as pd
from datetime import datetime
import time

def download_data_custom(symbols, period="10y"):
    frames = {}
    for sym in symbols:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range={period}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            res = urllib.request.urlopen(req)
            data = json.loads(res.read())
            result = data['chart']['result'][0]
            
            timestamps = result['timestamp']
            quote = result['indicators']['quote'][0]
            
            dates = [datetime.fromtimestamp(ts).strftime('%Y-%m-%d') for ts in timestamps]
            df = pd.DataFrame({
                'Open': quote['open'],
                'High': quote['high'],
                'Low': quote['low'],
                'Close': quote['close'],
                'Adj Close': quote['close'], # Fake Adj Close
                'Volume': quote.get('volume', [0]*len(dates))
            }, index=pd.to_datetime(dates))
            frames[sym] = df
            print(f"Downloaded {sym}")
        except Exception as e:
            print(f"Failed {sym}: {e}")
        time.sleep(0.5)
        
    if not frames: return None
    
    # Create multi-index dataframe mimicking yfinance
    # Columns: MultiIndex[(Price, Ticker), (Price, Ticker)...]
    # Price = Open, High, Low, Close, Adj Close, Volume
    
    # Combine all frames
    df_concat = pd.concat(frames.values(), axis=1, keys=frames.keys())
    # The current columns are [Ticker, Price]. yfinance returns [Price, Ticker].
    df_concat = df_concat.swaplevel(0, 1, axis=1).sort_index(axis=1)
    return df_concat

if __name__ == "__main__":
    from gann_app import GLOBAL_ASSETS
    symbols = [item["symbol"] for item in GLOBAL_ASSETS]
    df = download_data_custom(symbols)
    print(df.tail())
    df.to_csv('gann_data_global.csv.gz', compression='gzip')
