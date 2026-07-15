import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional

# Pre-defined instrument lists
NSE_INDICES = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "SENSEX": "^BSESN"
}

US_INDICES = {
    "S&P 500": "^GSPC",
    "NASDAQ 100": "^NDX",
    "DOW JONES": "^DJI"
}

# Add some mega caps and common F&O stocks for demonstration
NSE_STOCKS = ["RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS", "ICICIBANK.NS"]
US_STOCKS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]

def fetch_historical_data(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical OHLC data from yfinance.
    Returns a pandas DataFrame.
    """
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty:
            return pd.DataFrame()
            
        # Clean up MultiIndex columns from yfinance >= 0.2.40 if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
            
        data.reset_index(inplace=True)
        # Rename 'Date' or 'Datetime' column to 'Date'
        if 'Datetime' in data.columns:
            data.rename(columns={'Datetime': 'Date'}, inplace=True)
            
        return data
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()

def get_current_price(ticker: str) -> Optional[float]:
    """Fetch the latest close price for a ticker."""
    df = fetch_historical_data(ticker, period="5d")
    if not df.empty:
        return float(df['Close'].iloc[-1])
    return None

def get_all_tickers() -> List[str]:
    try:
        from gann_app import FNO_STOCKS, GLOBAL_ASSETS
        nse_tickers = [item["symbol"] + ".NS" if not item["symbol"].endswith(".NS") and not item["symbol"].startswith("^") else item["symbol"] for item in FNO_STOCKS]
        global_tickers = [item["symbol"] for item in GLOBAL_ASSETS]
        return list(NSE_INDICES.values()) + nse_tickers + global_tickers
    except ImportError:
        return list(NSE_INDICES.values()) + list(US_INDICES.values()) + NSE_STOCKS + US_STOCKS

if __name__ == "__main__":
    df = fetch_historical_data("^NSEI", period="1mo")
    print(df.head())
