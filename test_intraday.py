import urllib.request
import json
import pandas as pd
from datetime import datetime

url = "https://query2.finance.yahoo.com/v8/finance/chart/RELIANCE.NS?interval=5m&range=1d"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    result = data['chart']['result'][0]
    
    timestamps = result['timestamp']
    quote = result['indicators']['quote'][0]
    
    dates = [datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') for ts in timestamps]
    df = pd.DataFrame({
        'Open': quote['open'],
        'High': quote['high'],
        'Low': quote['low'],
        'Close': quote['close']
    }, index=dates)
    
    print(df.head())
    print("...")
    print(df.tail())
except Exception as e:
    print(f"Failed: {e}")
