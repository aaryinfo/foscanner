"""
Reversal Time Cycle — Flask App
Serves the dashboard HTML and provides /api/analyse, /api/stocks, and /api/screener endpoints.
"""

import json
import os
import time
import sys
import threading
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Vercel's filesystem is read-only, so we must use /tmp/ for the local sqlite database
DB_PATH = '/tmp/auth.db' if os.environ.get('VERCEL') else 'auth.db'

# ── Try to import heavy deps gracefully ──────────────────────────────────────
import traceback
try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
    from flask import Flask, jsonify, request, send_from_directory
    from gann_engine import analyse, compute_intraday_levels
except Exception as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

app = Flask(__name__, static_folder=".")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            clerk_id TEXT PRIMARY KEY,
            email TEXT,
            trial_start_date TEXT,
            has_agreed_tos BOOLEAN
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clerk_id TEXT,
            machine_number TEXT,
            last_login_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ── F&O Stocks Universe (211 Stocks) ──────────────────────────────────────────
FNO_STOCKS = [
    {"symbol": "360ONE", "name": "360 ONE WAM LIMITED"},
    {"symbol": "ABB", "name": "ABB India Limited"},
    {"symbol": "APLAPOLLO", "name": "APL Apollo Tubes Limited"},
    {"symbol": "AUBANK", "name": "AU Small Finance Bank Limited"},
    {"symbol": "ADANIENSOL", "name": "Adani Energy Solutions Limited"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises Limited"},
    {"symbol": "ADANIGREEN", "name": "Adani Green Energy Limited"},
    {"symbol": "ADANIPORTS", "name": "Adani Ports and Special Economic Zone Limited"},
    {"symbol": "ADANIPOWER", "name": "Adani Power Limited"},
    {"symbol": "ABCAPITAL", "name": "Aditya Birla Capital Limited"},
    {"symbol": "ALKEM", "name": "Alkem Laboratories Limited"},
    {"symbol": "AMBER", "name": "Amber Enterprises India Limited"},
    {"symbol": "AMBUJACEM", "name": "Ambuja Cements Limited"},
    {"symbol": "ANGELONE", "name": "Angel One Limited"},
    {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals Enterprise Limited"},
    {"symbol": "ASHOKLEY", "name": "Ashok Leyland Limited"},
    {"symbol": "ASIANPAINT", "name": "Asian Paints Limited"},
    {"symbol": "ASTRAL", "name": "Astral Limited"},
    {"symbol": "AUROPHARMA", "name": "Aurobindo Pharma Limited"},
    {"symbol": "DMART", "name": "Avenue Supermarts Limited"},
    {"symbol": "AXISBANK", "name": "Axis Bank Limited"},
    {"symbol": "BSE", "name": "BSE Limited"},
    {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto Limited"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Limited"},
    {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv Limited"},
    {"symbol": "BAJAJHLDNG", "name": "Bajaj Holdings & Investment Limited"},
    {"symbol": "BANDHANBNK", "name": "Bandhan Bank Limited"},
    {"symbol": "BANKBARODA", "name": "Bank of Baroda"},
    {"symbol": "BANKINDIA", "name": "Bank of India"},
    {"symbol": "BDL", "name": "Bharat Dynamics Limited"},
    {"symbol": "BEL", "name": "Bharat Electronics Limited"},
    {"symbol": "BHARATFORG", "name": "Bharat Forge Limited"},
    {"symbol": "BHEL", "name": "Bharat Heavy Electricals Limited"},
    {"symbol": "BPCL", "name": "Bharat Petroleum Corporation Limited"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Limited"},
    {"symbol": "BIOCON", "name": "Biocon Limited"},
    {"symbol": "BLUESTARCO", "name": "Blue Star Limited"},
    {"symbol": "BOSCHLTD", "name": "Bosch Limited"},
    {"symbol": "BRITANNIA", "name": "Britannia Industries Limited"},
    {"symbol": "CGPOWER", "name": "CG Power and Industrial Solutions Limited"},
    {"symbol": "CANBK", "name": "Canara Bank"},
    {"symbol": "CDSL", "name": "Central Depository Services (India) Limited"},
    {"symbol": "CHOLAFIN", "name": "Cholamandalam Investment and Finance Company Limited"},
    {"symbol": "CIPLA", "name": "Cipla Limited"},
    {"symbol": "COALINDIA", "name": "Coal India Limited"},
    {"symbol": "COCHINSHIP", "name": "Cochin Shipyard Limited"},
    {"symbol": "COFORGE", "name": "Coforge Limited"},
    {"symbol": "COLPAL", "name": "Colgate Palmolive (India) Limited"},
    {"symbol": "CAMS", "name": "Computer Age Management Services Limited"},
    {"symbol": "CONCOR", "name": "Container Corporation of India Limited"},
    {"symbol": "CROMPTON", "name": "Crompton Greaves Consumer Electricals Limited"},
    {"symbol": "CUMMINSIND", "name": "Cummins India Limited"},
    {"symbol": "DLF", "name": "DLF Limited"},
    {"symbol": "DABUR", "name": "Dabur India Limited"},
    {"symbol": "DALBHARAT", "name": "Dalmia Bharat Limited"},
    {"symbol": "DELHIVERY", "name": "Delhivery Limited"},
    {"symbol": "DIVISLAB", "name": "Divi's Laboratories Limited"},
    {"symbol": "DIXON", "name": "Dixon Technologies (India) Limited"},
    {"symbol": "DRREDDY", "name": "Dr. Reddy's Laboratories Limited"},
    {"symbol": "ETERNAL", "name": "ETERNAL LIMITED"},
    {"symbol": "EICHERMOT", "name": "Eicher Motors Limited"},
    {"symbol": "EXIDEIND", "name": "Exide Industries Limited"},
    {"symbol": "FORCEMOT", "name": "FORCE MOTORS LTD"},
    {"symbol": "NYKAA", "name": "FSN E-Commerce Ventures Limited"},
    {"symbol": "FORTIS", "name": "Fortis Healthcare Limited"},
    {"symbol": "GAIL", "name": "GAIL (India) Limited"},
    {"symbol": "GVT&D", "name": "GE Vernova T&D India Limited"},
    {"symbol": "GMRAIRPORT", "name": "GMR AIRPORTS LIMITED"},
    {"symbol": "GLENMARK", "name": "Glenmark Pharmaceuticals Limited"},
    {"symbol": "GODFRYPHLP", "name": "Godfrey Phillips India Limited"},
    {"symbol": "GODREJCP", "name": "Godrej Consumer Products Limited"},
    {"symbol": "GODREJPROP", "name": "Godrej Properties Limited"},
    {"symbol": "GRASIM", "name": "Grasim Industries Limited"},
    {"symbol": "HCLTECH", "name": "HCL Technologies Limited"},
    {"symbol": "HDFCAMC", "name": "HDFC Asset Management Company Limited"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Limited"},
    {"symbol": "HDFCLIFE", "name": "HDFC Life Insurance Company Limited"},
    {"symbol": "HAVELLS", "name": "Havells India Limited"},
    {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp Limited"},
    {"symbol": "HINDALCO", "name": "Hindalco Industries Limited"},
    {"symbol": "HAL", "name": "Hindustan Aeronautics Limited"},
    {"symbol": "HINDPETRO", "name": "Hindustan Petroleum Corporation Limited"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Limited"},
    {"symbol": "HINDZINC", "name": "Hindustan Zinc Limited"},
    {"symbol": "POWERINDIA", "name": "Hitachi Energy India Limited"},
    {"symbol": "HYUNDAI", "name": "Hyundai Motor India Limited"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Limited"},
    {"symbol": "ICICIGI", "name": "ICICI Lombard General Insurance Company Limited"},
    {"symbol": "ICICIPRULI", "name": "ICICI Prudential Life Insurance Company Limited"},
    {"symbol": "IDFCFIRSTB", "name": "IDFC First Bank Limited"},
    {"symbol": "ITC", "name": "ITC Limited"},
    {"symbol": "INDIANB", "name": "Indian Bank"},
    {"symbol": "IEX", "name": "Indian Energy Exchange Limited"},
    {"symbol": "IOC", "name": "Indian Oil Corporation Limited"},
    {"symbol": "IRFC", "name": "Indian Railway Finance Corporation Limited"},
    {"symbol": "IREDA", "name": "Indian Renewable Energy Development Agency Limited"},
    {"symbol": "INDUSTOWER", "name": "Indus Towers Limited"},
    {"symbol": "INDUSINDBK", "name": "IndusInd Bank Limited"},
    {"symbol": "NAUKRI", "name": "Info Edge (India) Limited"},
    {"symbol": "INFY", "name": "Infosys Limited"},
    {"symbol": "INOXWIND", "name": "Inox Wind Limited"},
    {"symbol": "INDIGO", "name": "InterGlobe Aviation Limited"},
    {"symbol": "JINDALSTEL", "name": "JINDAL STEEL LIMITED"},
    {"symbol": "JSWENERGY", "name": "JSW Energy Limited"},
    {"symbol": "JSWSTEEL", "name": "JSW Steel Limited"},
    {"symbol": "JIOFIN", "name": "Jio Financial Services Limited"},
    {"symbol": "JUBLFOOD", "name": "Jubilant Foodworks Limited"},
    {"symbol": "KEI", "name": "KEI Industries Limited"},
    {"symbol": "KPITTECH", "name": "KPIT Technologies Limited"},
    {"symbol": "KALYANKJIL", "name": "Kalyan Jewellers India Limited"},
    {"symbol": "KAYNES", "name": "Kaynes Technology India Limited"},
    {"symbol": "KFINTECH", "name": "Kfin Technologies Limited"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Limited"},
    {"symbol": "LTF", "name": "L&T Finance Limited"},
    {"symbol": "LICHSGFIN", "name": "LIC Housing Finance Limited"},
    {"symbol": "LTM", "name": "LTM Limited"},
    {"symbol": "LT", "name": "Larsen & Toubro Limited"},
    {"symbol": "LAURUSLABS", "name": "Laurus Labs Limited"},
    {"symbol": "LICI", "name": "Life Insurance Corporation Of India"},
    {"symbol": "LODHA", "name": "Lodha Developers Limited"},
    {"symbol": "LUPIN", "name": "Lupin Limited"},
    {"symbol": "M&M", "name": "Mahindra & Mahindra Limited"},
    {"symbol": "MANAPPURAM", "name": "Manappuram Finance Limited"},
    {"symbol": "MANKIND", "name": "Mankind Pharma Limited"},
    {"symbol": "MARICO", "name": "Marico Limited"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Limited"},
    {"symbol": "MFSL", "name": "Max Financial Services Limited"},
    {"symbol": "MAXHEALTH", "name": "Max Healthcare Institute Limited"},
    {"symbol": "MAZDOCK", "name": "Mazagon Dock Shipbuilders Limited"},
    {"symbol": "MOTILALOFS", "name": "Motilal Oswal Financial Services Limited"},
    {"symbol": "MPHASIS", "name": "MphasiS Limited"},
    {"symbol": "MCX", "name": "Multi Commodity Exchange of India Limited"},
    {"symbol": "MUTHOOTFIN", "name": "Muthoot Finance Limited"},
    {"symbol": "NBCC", "name": "NBCC (India) Limited"},
    {"symbol": "NHPC", "name": "NHPC Limited"},
    {"symbol": "NMDC", "name": "NMDC Limited"},
    {"symbol": "NTPC", "name": "NTPC Limited"},
    {"symbol": "NATIONALUM", "name": "National Aluminium Company Limited"},
    {"symbol": "NESTLEIND", "name": "Nestle India Limited"},
    {"symbol": "NAM-INDIA", "name": "Nippon Life India Asset Management Limited"},
    {"symbol": "NUVAMA", "name": "Nuvama Wealth Management Limited"},
    {"symbol": "OBEROIRLTY", "name": "Oberoi Realty Limited"},
    {"symbol": "ONGC", "name": "Oil & Natural Gas Corporation Limited"},
    {"symbol": "OIL", "name": "Oil India Limited"},
    {"symbol": "PAYTM", "name": "One 97 Communications Limited"},
    {"symbol": "OFSS", "name": "Oracle Financial Services Software Limited"},
    {"symbol": "POLICYBZR", "name": "PB Fintech Limited"},
    {"symbol": "PGEL", "name": "PG Electroplast Limited"},
    {"symbol": "PIIND", "name": "PI Industries Limited"},
    {"symbol": "PNBHOUSING", "name": "PNB Housing Finance Limited"},
    {"symbol": "PAGEIND", "name": "Page Industries Limited"},
    {"symbol": "PATANJALI", "name": "Patanjali Foods Limited"},
    {"symbol": "PERSISTENT", "name": "Persistent Systems Limited"},
    {"symbol": "PETRONET", "name": "Petronet LNG Limited"},
    {"symbol": "PIDILITIND", "name": "Pidilite Industries Limited"},
    {"symbol": "POLYCAB", "name": "Polycab India Limited"},
    {"symbol": "PFC", "name": "Power Finance Corporation Limited"},
    {"symbol": "POWERGRID", "name": "Power Grid Corporation of India Limited"},
    {"symbol": "PREMIERENE", "name": "Premier Energies Limited"},
    {"symbol": "PRESTIGE", "name": "Prestige Estates Projects Limited"},
    {"symbol": "PNB", "name": "Punjab National Bank"},
    {"symbol": "RBLBANK", "name": "RBL Bank Limited"},
    {"symbol": "RECLTD", "name": "REC Limited"},
    {"symbol": "RADICO", "name": "Radico Khaitan Limited"},
    {"symbol": "RVNL", "name": "Rail Vikas Nigam Limited"},
    {"symbol": "RELIANCE", "name": "Reliance Industries Limited"},
    {"symbol": "SBICARD", "name": "SBI Cards and Payment Services Limited"},
    {"symbol": "SBILIFE", "name": "SBI Life Insurance Company Limited"},
    {"symbol": "SHREECEM", "name": "SHREE CEMENT LIMITED"},
    {"symbol": "SRF", "name": "SRF Limited"},
    {"symbol": "SAMMAANCAP", "name": "Sammaan Capital Limited"},
    {"symbol": "MOTHERSON", "name": "Samvardhana Motherson International Limited"},
    {"symbol": "SHRIRAMFIN", "name": "Shriram Finance Limited"},
    {"symbol": "SIEMENS", "name": "Siemens Limited"},
    {"symbol": "SOLARINDS", "name": "Solar Industries India Limited"},
    {"symbol": "SONACOMS", "name": "Sona BLW Precision Forgings Limited"},
    {"symbol": "SBIN", "name": "State Bank of India"},
    {"symbol": "SAIL", "name": "Steel Authority of India Limited"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Limited"},
    {"symbol": "SUPREMEIND", "name": "Supreme Industries Limited"},
    {"symbol": "SUZLON", "name": "Suzlon Energy Limited"},
    {"symbol": "SWIGGY", "name": "Swiggy Limited"},
    {"symbol": "TATACONSUM", "name": "TATA CONSUMER PRODUCTS LIMITED"},
    {"symbol": "TVSMOTOR", "name": "TVS Motor Company Limited"},
    {"symbol": "TCS", "name": "Tata Consultancy Services Limited"},
    {"symbol": "TATAELXSI", "name": "Tata Elxsi Limited"},
    {"symbol": "TMPV", "name": "Tata Motors Passenger Vehicles Limited"},
    {"symbol": "TATAPOWER", "name": "Tata Power Company Limited"},
    {"symbol": "TATASTEEL", "name": "Tata Steel Limited"},
    {"symbol": "TECHM", "name": "Tech Mahindra Limited"},
    {"symbol": "FEDERALBNK", "name": "The Federal Bank Limited"},
    {"symbol": "INDHOTEL", "name": "The Indian Hotels Company Limited"},
    {"symbol": "PHOENIXLTD", "name": "The Phoenix Mills Limited"},
    {"symbol": "TITAN", "name": "Titan Company Limited"},
    {"symbol": "TORNTPHARM", "name": "Torrent Pharmaceuticals Limited"},
    {"symbol": "TRENT", "name": "Trent Limited"},
    {"symbol": "TIINDIA", "name": "Tube Investments of India Limited"},
    {"symbol": "UNOMINDA", "name": "UNO Minda Limited"},
    {"symbol": "UPL", "name": "UPL Limited"},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Limited"},
    {"symbol": "UNIONBANK", "name": "Union Bank of India"},
    {"symbol": "UNITDSPR", "name": "United Spirits Limited"},
    {"symbol": "VBL", "name": "Varun Beverages Limited"},
    {"symbol": "VEDL", "name": "Vedanta Limited"},
    {"symbol": "VMM", "name": "Vishal Mega Mart Limited"},
    {"symbol": "IDEA", "name": "Vodafone Idea Limited"},
    {"symbol": "VOLTAS", "name": "Voltas Limited"},
    {"symbol": "WAAREEENER", "name": "Waaree Energies Limited"},
    {"symbol": "WIPRO", "name": "Wipro Limited"},
    {"symbol": "YESBANK", "name": "Yes Bank Limited"},
    {"symbol": "ZYDUSLIFE", "name": "Zydus Lifesciences Limited"}
]

GLOBAL_ASSETS = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "AMZN", "name": "Amazon.com Inc."},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "TSLA", "name": "Tesla Inc."},
    {"symbol": "META", "name": "Meta Platforms Inc."},
    {"symbol": "BTC-USD", "name": "Bitcoin USD (TV: BTCUSD)"},
    {"symbol": "ETH-USD", "name": "Ethereum USD (TV: ETHUSD)"},
    {"symbol": "SOL-USD", "name": "Solana USD (TV: SOLUSD)"},
    {"symbol": "BNB-USD", "name": "Binance Coin USD (TV: BNBUSD)"},
    {"symbol": "GC=F", "name": "Gold Futures (TV: GC1!)"},
    {"symbol": "SI=F", "name": "Silver Futures (TV: SI1!)"},
    {"symbol": "CL=F", "name": "Crude Oil Futures (TV: CL1!)"},
    {"symbol": "NG=F", "name": "Natural Gas Futures (TV: NG1!)"},
    {"symbol": "ZC=F", "name": "Corn Futures (TV: ZC1!)"},
]

COMPANY_MAP = {item["symbol"]: item["name"] for item in FNO_STOCKS + GLOBAL_ASSETS}

# ── Cache & Cache Config ──────────────────────────────────────────────────────
_cache: dict = {}
CACHE_TTL = 3600  # 1 hour

# ── Screener State & Cache ─────────────────────────────────────────────────────
def get_default_screener_state():
    return {
        "results": [],
        "last_updated": 0,
        "is_loading": False,
        "status": "Not run yet",
        "error": None
    }

_screener_cache = {
    "NSE": get_default_screener_state(),
    "GLOBAL": get_default_screener_state()
}
SCREENER_LOCK = threading.RLock()

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_data(symbol: str, market: str = "NSE", period: str = "2y") -> pd.DataFrame:
    """Fetch daily OHLC from yfinance with simple in-memory cache."""
    key = f"{symbol}_{market}_{period}"
    if key in _cache and (time.time() - _cache[key]["ts"]) < CACHE_TTL:
        return _cache[key]["df"]

    search_sym = f"{symbol}.NS" if market == "NSE" and not symbol.endswith(".NS") else symbol

    # Use cached data to ensure report exactly matches the screener
    cache_file = Path("gann_data_20y.csv.gz") if market == "NSE" else Path("gann_global_10y.csv.gz")
    df = None
    if cache_file.exists():
        try:
            cached_df = pd.read_csv(cache_file, header=[0, 1], index_col=0)
            cached_df.index = pd.to_datetime(cached_df.index)
            if search_sym in cached_df.columns.levels[1]:
                df = cached_df.xs(search_sym, level=1, axis=1).dropna()
        except Exception:
            pass

    if df is None or df.empty:
        df = yf.download(search_sym, period=period, interval="1d", progress=False)

    if df.empty:
        raise ValueError(f"No data for {symbol}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    df = df[["Open", "High", "Low", "Close"]].dropna()
    _cache[key] = {"df": df, "ts": time.time()}
    return df

from gann_engine import is_non_trading_day

# ── Background Market Screener Task ───────────────────────────────────────────
def run_market_screener(market="NSE"):
    global _screener_cache
    
    with SCREENER_LOCK:
        if _screener_cache[market]["is_loading"]:
            return
        _screener_cache[market]["is_loading"] = True
        _screener_cache[market]["status"] = f"Preparing {market} symbols..."
        _screener_cache[market]["error"] = None
        
    try:
        if market == "NSE":
            symbols = [item["symbol"] for item in FNO_STOCKS]
            tickers = [s + ".NS" for s in symbols]
            process_items = FNO_STOCKS
            period_str = "20y"
        else:
            symbols = [item["symbol"] for item in GLOBAL_ASSETS]
            tickers = symbols
            process_items = GLOBAL_ASSETS
            period_str = "10y"  # Less data for crypto/comm sometimes, 10y is safer
            
        # On Vercel, avoid downloading data due to serverless timeouts
        if market == "NSE":
            cache_file = Path("gann_data_20y.csv.gz")
        else:
            cache_file = Path("gann_data_global.csv.gz")
        is_vercel = os.environ.get("VERCEL") == "1"
        
        data = None
        if cache_file.exists() and (is_vercel or (time.time() - cache_file.stat().st_mtime) < 12 * 3600):
            with SCREENER_LOCK:
                _screener_cache[market]["status"] = f"Loading {market} data from disk cache..."
            try:
                data = pd.read_csv(cache_file, header=[0, 1], index_col=0)
                data.index = pd.to_datetime(data.index)
            except Exception as e:
                print(f"Failed to read cache {cache_file}: {e}")
                data = None

        if data is None:
            with SCREENER_LOCK:
                _screener_cache[market]["status"] = f"Downloading {market} data (takes ~1-2 min)..."
            data = yf.download(tickers, period=period_str, interval="1d", progress=False, group_by="ticker", threads=True)
            if not is_vercel:
                try:
                    data.to_csv(cache_file, compression="gzip")
                except Exception as cache_err:
                    print(f"Failed to save pickle cache: {cache_err}")
        
        with SCREENER_LOCK:
            _screener_cache[market]["status"] = "Running cycle calculations..."
            
        from datetime import timezone
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        today = now.date()
        
        # Determine the next actual trading day when market opens
        is_today_trading = not is_non_trading_day(today, market)
        is_before_close = now.hour < 15 or (now.hour == 15 and now.minute < 30)
        
        if is_today_trading and is_before_close:
            next_trading_day = today
        else:
            curr = today + timedelta(days=1)
            while is_non_trading_day(curr, market):
                curr += timedelta(days=1)
            next_trading_day = curr
            
        # Include all non-trading days preceding next_trading_day
        target_dates_list = [next_trading_day]
        prev = next_trading_day - timedelta(days=1)
        while is_non_trading_day(prev, market):
            target_dates_list.append(prev)
            prev -= timedelta(days=1)
            
        target_dates = [d.strftime("%Y-%m-%d") for d in target_dates_list]
        
        results = []
        
        # Evaluate all stocks regardless of environment
        pass        
        def process_stock(item):
            sym = item["symbol"]
            ticker = sym if market == "GLOBAL" else sym + ".NS"
            try:
                # Extract fields if they exist in the downloaded batch DataFrame
                if isinstance(data.columns, pd.MultiIndex):
                    if ticker not in data.columns.levels[0]:
                        return None
                    ticker_df = pd.DataFrame({
                        "Open": data[ticker]["Open"],
                        "High": data[ticker]["High"],
                        "Low": data[ticker]["Low"],
                        "Close": data[ticker]["Close"]
                    }).dropna()
                else:
                    if len(tickers) == 1:
                        ticker_df = data[["Open", "High", "Low", "Close"]].dropna()
                    else:
                        return None
                
                if ticker_df.empty or len(ticker_df) < 50:
                    return None
                
                # Analyze using swing window=10
                res = analyse(ticker_df, sym, swing_window=10, period=period_str)
                
                backtest = res.get("backtest", {})
                accuracy = backtest.get("accuracy", 0.0)
                success_count = backtest.get("success_count", 0)
                
                stock_results = []
                # Only include stocks with validated patterns (accuracy >= 30.0)
                if success_count > 0 and accuracy >= 30.0:
                    # Use the analysis result's own intraday_levels for signal consistency
                    # This ensures the screener signal matches what ANALYSE shows
                    intra = res.get("intraday_levels")
                    setup_valid = res.get("setup_valid", False)
                    
                    if not setup_valid or intra is None or not intra.get('is_valid', False):
                        return None
                    
                    # Find the best matching confluence for the target trading dates
                    matching_confs = [c for c in res["confluence"] 
                                     if c["date"] in target_dates and c["count"] >= 3]
                    
                    if matching_confs:
                        # Use the strongest confluence for metadata
                        best_conf = max(matching_confs, key=lambda c: c["count"])
                        
                        stock_results.append({
                            "symbol": sym,
                            "name": item["name"],
                            "last_close": res["last_close"],
                            "entry": intra["entry"],
                            "sl": intra["sl"],
                            "t1": intra["t1"],
                            "t2": intra["t2"],
                            "risk_pct": intra["risk_pct"],
                            "risk_reward": intra["risk_reward_t1"],
                            "rr1_num": intra["rr1_num"],
                            "target_level": intra["target_level"],
                            "sl_level": intra["sl_level"],
                            "expectancy": intra["expectancy"],
                            "expectancy_pct": intra["expectancy_pct"],
                            "date": next_trading_day.strftime("%Y-%m-%d"),
                            "date_display": best_conf.get("date_display", next_trading_day.strftime("%Y-%m-%d")),
                            "days_away": best_conf["days_away"],
                            "signal": intra["signal"],   # Use intra signal for consistency with ANALYSE page
                            "strength": best_conf["strength"],
                            "count": best_conf["count"],
                            "accuracy": accuracy,
                            "active_cycles": best_conf.get("cycles", [])[:4]
                        })
                return stock_results
            except Exception:
                return None

        # Execute in parallel with 16 worker threads
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=16) as executor:
            thread_results = list(executor.map(process_stock, process_items))
            
        for r in thread_results:
            if r:
                results.extend(r)
                
        # Deduplicate results by symbol, keeping the one closest to next_trading_day (or highest quality)
        deduped = {}
        next_trading_day_str = next_trading_day.strftime("%Y-%m-%d")
        for r in results:
            sym = r["symbol"]
            if sym not in deduped:
                deduped[sym] = r
            else:
                existing = deduped[sym]
                # Prefer target trading day
                if r["date"] == next_trading_day_str and existing["date"] != next_trading_day_str:
                    deduped[sym] = r
                elif existing["date"] == next_trading_day_str and r["date"] != next_trading_day_str:
                    pass
                elif r["expectancy"] > existing["expectancy"]:
                    deduped[sym] = r
        results = list(deduped.values())
                
        # Sort results: highest EV first, then R:R, then strength
        strength_order = {"STRONG": 0, "MODERATE": 1, "WEAK": 2}
        results.sort(key=lambda x: (-x["expectancy"], -x["rr1_num"], strength_order.get(x["strength"], 9)))
        
        # Keep top 10 highest-EV backtest-validated setups
        top_results = results[:10]
        
        with SCREENER_LOCK:
            _screener_cache[market]["results"] = top_results
            _screener_cache[market]["last_updated"] = time.time()
            _screener_cache[market]["status"] = "Completed"
            
    except Exception as e:
        with SCREENER_LOCK:
            _screener_cache[market]["error"] = str(e)
            _screener_cache[market]["status"] = f"Failed: {str(e)}"
    finally:
        with SCREENER_LOCK:
            _screener_cache[market]["is_loading"] = False

def start_background_scan(market: str = "NSE"):
    if not _screener_cache[market]["is_loading"]:
        if os.environ.get("VERCEL") == "1":
            run_market_screener(market)
        else:
            import threading
            threading.Thread(target=run_market_screener, args=(market,), daemon=True).start()

# ── API Endpoints ─────────────────────────────────────────────────────────────
@app.route("/api/analyse")
def api_analyse():
    symbol = request.args.get("symbol", "RELIANCE").upper()
    market = request.args.get("market", "NSE").upper()
    period = request.args.get("period", "2y")
    window = int(request.args.get("window", "10"))

    try:
        df     = fetch_data(symbol, market, period)
        result = analyse(df, symbol, swing_window=window, period=period)
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.route("/api/stocks")
def api_stocks():
    """Returns the lists of F&O Stocks and Global Assets."""
    return jsonify({"ok": True, "stocks": FNO_STOCKS, "global": GLOBAL_ASSETS})

@app.route("/api/screener")
def api_screener():
    """Endpoint for market screener status and results."""
    market = request.args.get("market", "NSE").upper()
    force = request.args.get("force", "false").lower() == "true"
    
    if market not in _screener_cache:
        market = "NSE"
        
    is_vercel = os.environ.get("VERCEL") == "1"
    if is_vercel and _screener_cache[market]["last_updated"] == 0 and not _screener_cache[market]["is_loading"]:
        force = True
    if force:
        with SCREENER_LOCK:
            _screener_cache[market]["is_loading"] = False
            if not _screener_cache[market]["is_loading"]:
                start_background_scan(market)
                
                return jsonify({
                    "ok": True,
                    "ready": True,
                    "is_loading": False,
                    "status": _screener_cache[market]["status"],
                    "last_updated": _screener_cache[market]["last_updated"],
                    "error": _screener_cache[market]["error"],
                    "results": _screener_cache[market]["results"]
                })
                
    return jsonify({
        "ok": True,
        "ready": not _screener_cache[market]["is_loading"] and _screener_cache[market]["last_updated"] > 0,
        "is_loading": _screener_cache[market]["is_loading"],
        "status": _screener_cache[market]["status"],
        "last_updated": _screener_cache[market]["last_updated"],
        "error": _screener_cache[market]["error"],
        "results": _screener_cache[market]["results"]
    })

@app.route("/api/technical")
def api_technical():
    market = request.args.get("market", "NSE").upper()
    try:
        if market == "NSE":
            symbols = [item["symbol"] for item in FNO_STOCKS]
            tickers = [s + ".NS" for s in symbols]
        else:
            symbols = [item["symbol"] for item in GLOBAL_ASSETS]
            tickers = symbols
            
        # No artificial limits on symbols
        # Download 10 years of data to ensure 20-month EMA and 14-month RSI have enough warmup to match TradingView
        cache_file = Path(f"gann_tech_{market}.csv.gz")
        is_vercel = os.environ.get("VERCEL") == "1"
        data = None

        if cache_file.exists() and (is_vercel or (time.time() - cache_file.stat().st_mtime) < 12 * 3600):
            try:
                data = pd.read_csv(cache_file, header=[0, 1], index_col=0)
                data.index = pd.to_datetime(data.index)
            except Exception:
                data = None

        if data is None:
            data = yf.download(tickers, period="10y", interval="1mo", progress=False, group_by="ticker", threads=True)
            if not is_vercel:
                try:
                    data.to_csv(cache_file, compression="gzip")
                except Exception:
                    pass
        
        matches = []
        for i, ticker in enumerate(tickers):
            sym = symbols[i]
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    if ticker not in data.columns.levels[0]:
                        continue
                    df = pd.DataFrame({
                        "Open": data[ticker]["Open"],
                        "High": data[ticker]["High"],
                        "Low": data[ticker]["Low"],
                        "Close": data[ticker]["Close"]
                    }).dropna()
                else:
                    if len(tickers) == 1:
                        df = data[["Open", "High", "Low", "Close"]].dropna()
                    else:
                        continue
                        
                if df.empty or len(df) < 25:
                    continue
                    
                close = df["Close"]
                ema9 = close.ewm(span=9, adjust=False).mean()
                ema20 = close.ewm(span=20, adjust=False).mean()
                
                # Wilder's Smoothing RSI calculation (matches TradingView)
                delta = close.diff()
                gain = delta.where(delta > 0, 0.0)
                loss = -delta.where(delta < 0, 0.0)
                avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
                avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                
                # Condition 1: EMA Cross (within last 6 months)
                cross_bull = False
                cross_bear = False
                for offset in range(-6, 0):
                    if ema9.iloc[offset] > ema20.iloc[offset] and ema9.iloc[offset-1] <= ema20.iloc[offset-1]:
                        cross_bull = True
                    if ema9.iloc[offset] < ema20.iloc[offset] and ema9.iloc[offset-1] >= ema20.iloc[offset-1]:
                        cross_bear = True
                
                # Condition 2: Previous 4-5 candles in consolidation range
                recent_highs = df["High"].iloc[-6:-1]
                recent_lows = df["Low"].iloc[-6:-1]
                range_pct = (recent_highs.max() - recent_lows.min()) / recent_lows.min()
                in_range = range_pct < 0.25  # 25% max range over 5 months for consolidation
                
                # Condition 3: RSI between 45 to 55
                current_rsi = rsi.iloc[-1]
                rsi_ok = 45 <= current_rsi <= 55
                
                if (cross_bull or cross_bear) and in_range and rsi_ok:
                    signal = "BULLISH" if cross_bull else "BEARISH"
                    matches.append({
                        "symbol": sym,
                        "close": round(close.iloc[-1], 2),
                        "rsi": round(current_rsi, 2),
                        "signal": signal,
                        "name": COMPANY_MAP.get(sym, sym)
                    })
            except Exception as ex:
                continue
                
        return jsonify({"ok": True, "results": matches})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.json
    clerk_id = data.get("clerk_id")
    email = data.get("email")
    machine_number = data.get("machine_number")
    
    if not clerk_id or not machine_number:
        return jsonify({"ok": False, "error": "Missing clerk_id or machine_number"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if user exists
    c.execute("SELECT trial_start_date, has_agreed_tos FROM users WHERE clerk_id = ?", (clerk_id,))
    user = c.fetchone()
    
    now_str = datetime.utcnow().isoformat()
    
    if not user:
        # New user
        c.execute("INSERT INTO users (clerk_id, email, trial_start_date, has_agreed_tos) VALUES (?, ?, ?, ?)",
                  (clerk_id, email, now_str, False))
        trial_start_date = now_str
        has_agreed_tos = False
    else:
        trial_start_date = user[0]
        has_agreed_tos = bool(user[1])
        
    # Log device
    c.execute("INSERT INTO devices (clerk_id, machine_number, last_login_at) VALUES (?, ?, ?)",
              (clerk_id, machine_number, now_str))
              
    # Optional: count devices or emails per machine here if you want to block
    # For now we just log it as requested.

    conn.commit()
    conn.close()
    
    # Check trial expiry (15 days)
    trial_start = datetime.fromisoformat(trial_start_date)
    trial_end = trial_start + timedelta(days=15)
    
    if datetime.utcnow() > trial_end:
        return jsonify({"ok": True, "status": "expired"})
        
    remaining_days = (trial_end - datetime.utcnow()).days
        
    if not has_agreed_tos:
        return jsonify({"ok": True, "status": "needs_tos", "remaining_days": remaining_days})
        
    return jsonify({"ok": True, "status": "active", "remaining_days": remaining_days})

@app.route("/api/auth/agree_tos", methods=["POST"])
def auth_agree_tos():
    data = request.json
    clerk_id = data.get("clerk_id")
    
    if not clerk_id:
        return jsonify({"ok": False, "error": "Missing clerk_id"}), 400
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET has_agreed_tos = 1 WHERE clerk_id = ?", (clerk_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"ok": True})

@app.route("/payment.html")
def payment_page():
    return send_from_directory(".", "payment.html")

@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory("assets", filename)

@app.route("/interactive_disclaimer_spa.html")
def interactive_disclaimer_page():
    return send_from_directory(".", "interactive_disclaimer_spa.html")

@app.route("/")
def index():
    return send_from_directory(".", "gann_dashboard.html")

if __name__ == "__main__":
    # Pre-load the market scanner background task when starting up
    print("Pre-loading Reversals Market Screener in background...")
    start_background_scan("NSE")
    start_background_scan("GLOBAL")

    print("\n" + "="*55)
    print("  Reversal Time Cycle Dashboard")
    print("  Open: http://localhost:5050")
    print("="*55 + "\n")
    app.run(debug=True, port=5050)
