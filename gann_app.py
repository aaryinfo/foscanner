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
import urllib.parse
try:
    import psycopg2
except ImportError:
    pass

from pathlib import Path
from datetime import datetime, timedelta

# Vercel's filesystem is read-only, so we must use /tmp/ for the local sqlite database
DB_PATH = '/tmp/auth.db' if os.environ.get('VERCEL') else 'auth.db'
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        return conn, True
    else:
        conn = sqlite3.connect(DB_PATH)
        return conn, False

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
    conn, is_postgres = get_db_connection()
    c = conn.cursor()
    
    if is_postgres:
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
                id SERIAL PRIMARY KEY,
                clerk_id TEXT,
                machine_number TEXT,
                last_login_at TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS screener_results (
                id SERIAL PRIMARY KEY,
                market TEXT NOT NULL,
                scan_date TEXT NOT NULL,
                data_date TEXT,
                results_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        # Create index for fast lookups by market + scan_date
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_screener_market_date 
            ON screener_results (market, scan_date)
        ''')
    else:
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS screener_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT NOT NULL,
                scan_date TEXT NOT NULL,
                data_date TEXT,
                results_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
    
    conn.commit()
    conn.close()

init_db()

# ── F&O Stocks Universe (211 Stocks) ──────────────────────────────────────────
FNO_STOCKS = [
    {"symbol": "^NSEI", "name": "NIFTY 50 INDEX"},
    {"symbol": "^NSEBANK", "name": "NIFTY BANK INDEX"},
    {"symbol": "NIFTY_FIN_SERVICE.NS", "name": "NIFTY FIN SERVICE INDEX"},
    {"symbol": "^NSEMDCP50", "name": "NIFTY MIDCAP 50 INDEX"},
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
    # US Indices & Broad Market
    {"symbol": "^NDX", "name": "NASDAQ-100 Index"},
    {"symbol": "^GSPC", "name": "S&P 500 Index"},
    {"symbol": "^DJI", "name": "Dow Jones Industrial Average"},
    {"symbol": "^IXIC", "name": "NASDAQ Composite Index"},
    {"symbol": "^RUT", "name": "Russell 2000 Index"},
    {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF (All US Stocks)"},
    
    # Tech Stocks
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "AMZN", "name": "Amazon.com Inc."},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "TSLA", "name": "Tesla Inc."},
    {"symbol": "META", "name": "Meta Platforms Inc."},
    
    # Crypto
    {"symbol": "BTC-USD", "name": "Bitcoin USD (TV: BTCUSD)"},
    {"symbol": "ETH-USD", "name": "Ethereum USD (TV: ETHUSD)"},
    {"symbol": "SOL-USD", "name": "Solana USD (TV: SOLUSD)"},
    {"symbol": "BNB-USD", "name": "Binance Coin USD (TV: BNBUSD)"},
    
    # Commodities & Forex
    {"symbol": "XAUUSD=X", "name": "Gold / US Dollar (XAU/USD)"},
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

    search_sym = f"{symbol}.NS" if market == "NSE" and not symbol.endswith(".NS") and not symbol.startswith("^") else symbol

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

# ── Helper: Get the current scan date (next trading day) ──────────────────────
def _get_scan_date(market="NSE"):
    """Determine the scan date = next trading day. This is the key for DB caching."""
    from datetime import timezone
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    today = now.date()
    
    is_today_trading = not is_non_trading_day(today, market)
    is_before_close = now.hour < 15 or (now.hour == 15 and now.minute < 30)
    
    if is_today_trading and is_before_close:
        return today
    else:
        curr = today + timedelta(days=1)
        while is_non_trading_day(curr, market):
            curr += timedelta(days=1)
        return curr

# ── Helper: Load cached screener results from DB ─────────────────────────────
def _load_screener_from_db(market, scan_date_str):
    """Load previously saved screener results from the database. Returns list or None."""
    try:
        conn, is_postgres = get_db_connection()
        c = conn.cursor()
        param = "%s" if is_postgres else "?"
        c.execute(
            f"SELECT results_json, data_date FROM screener_results WHERE market = {param} AND scan_date = {param} ORDER BY created_at DESC LIMIT 1",
            (market, scan_date_str)
        )
        row = c.fetchone()
        conn.close()
        if row:
            return json.loads(row[0]), row[1]
    except Exception as e:
        print(f"Failed to load screener from DB: {e}")
    return None, None

# ── Helper: Save screener results to DB ───────────────────────────────────────
def _save_screener_to_db(market, scan_date_str, data_date_str, results):
    """Persist screener results to the database for consistent retrieval."""
    try:
        conn, is_postgres = get_db_connection()
        c = conn.cursor()
        param = "%s" if is_postgres else "?"
        now_str = datetime.utcnow().isoformat()
        results_json = json.dumps(results)
        
        # Delete old results for this market+scan_date to avoid duplicates
        c.execute(
            f"DELETE FROM screener_results WHERE market = {param} AND scan_date = {param}",
            (market, scan_date_str)
        )
        
        c.execute(
            f"INSERT INTO screener_results (market, scan_date, data_date, results_json, created_at) VALUES ({param}, {param}, {param}, {param}, {param})",
            (market, scan_date_str, data_date_str, results_json, now_str)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to save screener to DB: {e}")

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
            tickers = [s + ".NS" if not s.endswith(".NS") and not s.startswith("^") else s for s in symbols]
            process_items = FNO_STOCKS
            period_str = "20y"
        else:
            symbols = [item["symbol"] for item in GLOBAL_ASSETS]
            tickers = symbols
            process_items = GLOBAL_ASSETS
            period_str = "10y"
            
        # ── DETERMINISTIC DATA SOURCE: Use ONLY the cached CSV file ──────────
        # This eliminates price inconsistency between cached vs live data
        if market == "NSE":
            cache_file = Path("gann_data_20y.csv.gz")
        else:
            cache_file = Path("gann_data_global.csv.gz")
        
        with SCREENER_LOCK:
            _screener_cache[market]["status"] = f"Loading {market} data from disk cache..."
            
        data = None
        data_date_str = "unknown"
        
        if cache_file.exists():
            try:
                data = pd.read_csv(cache_file, header=[0, 1], index_col=0)
                data.index = pd.to_datetime(data.index)
                # Record the last date in the data for transparency
                data_date_str = data.index[-1].strftime("%Y-%m-%d")
            except Exception as e:
                print(f"Failed to read cache {cache_file}: {e}")
                data = None
        
        if data is None:
            # If no cache file exists at all, download once and save
            is_vercel = os.environ.get("VERCEL") == "1"
            if is_vercel:
                raise ValueError(f"No cached data file found: {cache_file}. Run auto_update.py locally and redeploy.")
            
            with SCREENER_LOCK:
                _screener_cache[market]["status"] = f"Downloading {market} data (one-time, takes ~1-2 min)..."
            data = yf.download(tickers, period=period_str, interval="1d", progress=False, group_by="ticker", threads=True)
            try:
                data.to_csv(cache_file, compression="gzip")
            except Exception as cache_err:
                print(f"Failed to save cache: {cache_err}")
            data_date_str = data.index[-1].strftime("%Y-%m-%d")
        
        with SCREENER_LOCK:
            _screener_cache[market]["status"] = "Running cycle calculations..."
            
        from datetime import timezone
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        today = now.date()
        
        # Determine the next actual trading day when market opens
        next_trading_day = _get_scan_date(market)
            
        # Include all non-trading days preceding next_trading_day
        target_dates_list = [next_trading_day]
        prev = next_trading_day - timedelta(days=1)
        while is_non_trading_day(prev, market):
            target_dates_list.append(prev)
            prev -= timedelta(days=1)
            
        # Also include the PREVIOUS actual trading day to show recent setups
        # that might still be perfectly valid for entry today.
        target_dates_list.append(prev)
        prev2 = prev - timedelta(days=1)
        while is_non_trading_day(prev2, market):
            target_dates_list.append(prev2)
            prev2 -= timedelta(days=1)
            
        target_dates = [d.strftime("%Y-%m-%d") for d in target_dates_list]
        
        results = []
        
        # ── DETERMINISTIC SEQUENTIAL PROCESSING ──────────────────────────────
        # Process each stock one by one. No ThreadPoolExecutor, no race conditions.
        # Only use data from the cached CSV. Skip stocks not in cache.
        total_items = len(process_items)
        for idx, item in enumerate(process_items):
            sym = item["symbol"]
            ticker = sym if market == "GLOBAL" else (sym if sym.endswith(".NS") or sym.startswith("^") else sym + ".NS")
            
            if (idx + 1) % 20 == 0:
                with SCREENER_LOCK:
                    _screener_cache[market]["status"] = f"Analyzing {idx+1}/{total_items} stocks..."
            
            try:
                # Extract from cached DataFrame ONLY — no yf.download fallback
                if isinstance(data.columns, pd.MultiIndex):
                    if ticker not in data.columns.levels[0]:
                        continue  # Skip — not in cache
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
                        continue  # Skip — can't extract
                
                if ticker_df.empty or len(ticker_df) < 50:
                    continue
                
                # Analyze using swing window=10
                res = analyse(ticker_df, sym, swing_window=10, period=period_str)
                
                backtest = res.get("backtest", {})
                accuracy = backtest.get("accuracy", 0.0)
                success_count = backtest.get("success_count", 0)
                
                # Only include stocks with validated patterns (accuracy >= 30.0)
                if success_count > 0 and accuracy >= 30.0:
                    # Use the analysis result's own intraday_levels for signal consistency
                    # This ensures the screener signal matches what ANALYSE shows
                    intra = res.get("intraday_levels")
                    setup_valid = res.get("setup_valid", False)
                    
                    if not setup_valid or intra is None or not intra.get('is_valid', False):
                        continue
                    
                    # Find the best matching confluence for the target trading dates
                    matching_confs = [c for c in res["confluence"] 
                                     if c["date"] in target_dates and c["count"] >= 3]
                    
                    if matching_confs:
                        # Use the strongest confluence for metadata
                        best_conf = max(matching_confs, key=lambda c: c["count"])
                        
                        results.append({
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
            except Exception:
                continue
                
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
        
        # Keep top 5 highest-EV backtest-validated setups
        top_results = results[:5]
        
        # ── PERSIST TO DATABASE for consistent retrieval ──────────────────────
        scan_date_str = next_trading_day.strftime("%Y-%m-%d")
        _save_screener_to_db(market, scan_date_str, data_date_str, top_results)
        
        with SCREENER_LOCK:
            _screener_cache[market]["results"] = top_results
            _screener_cache[market]["last_updated"] = time.time()
            _screener_cache[market]["status"] = "Completed"
            _screener_cache[market]["data_date"] = data_date_str
            
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
    """Endpoint for market screener status and results.
    
    Deterministic logic:
    1. Check if we already have results for today's scan_date in the DB
    2. If yes, return them immediately (consistent across all Vercel instances)
    3. If no, run a fresh scan, persist to DB, then return
    4. force=true bypasses DB cache and re-scans (RE-SCAN MARKET button)
    """
    market = request.args.get("market", "NSE").upper()
    force = request.args.get("force", "false").lower() == "true"
    
    if market not in _screener_cache:
        market = "NSE"
    
    scan_date = _get_scan_date(market)
    scan_date_str = scan_date.strftime("%Y-%m-%d")
    
    # ── Step 1: Try DB cache first (unless force re-scan) ─────────────────
    if not force:
        db_results, data_date = _load_screener_from_db(market, scan_date_str)
        if db_results is not None:
            # We have persisted results — return immediately, 100% consistent
            with SCREENER_LOCK:
                _screener_cache[market]["results"] = db_results
                _screener_cache[market]["last_updated"] = time.time()
                _screener_cache[market]["status"] = "Completed"
                _screener_cache[market]["data_date"] = data_date or "unknown"
            
            return jsonify({
                "ok": True,
                "ready": True,
                "is_loading": False,
                "status": "Completed",
                "last_updated": _screener_cache[market]["last_updated"],
                "error": None,
                "results": db_results,
                "scan_date": scan_date_str,
                "data_date": data_date or "unknown"
            })
    
    # ── Step 2: No DB cache (or force=true) — run fresh scan ──────────────
    # Also check in-memory cache (same Vercel instance, already ran)
    if not force and _screener_cache[market]["last_updated"] > 0 and _screener_cache[market]["results"]:
        return jsonify({
            "ok": True,
            "ready": True,
            "is_loading": False,
            "status": _screener_cache[market]["status"],
            "last_updated": _screener_cache[market]["last_updated"],
            "error": _screener_cache[market]["error"],
            "results": _screener_cache[market]["results"],
            "scan_date": scan_date_str,
            "data_date": _screener_cache[market].get("data_date", "unknown")
        })
    
    # ── Step 3: Fresh scan needed ─────────────────────────────────────────
    with SCREENER_LOCK:
        _screener_cache[market]["is_loading"] = False
    start_background_scan(market)
            
    return jsonify({
        "ok": True,
        "ready": not _screener_cache[market]["is_loading"] and _screener_cache[market]["last_updated"] > 0,
        "is_loading": _screener_cache[market]["is_loading"],
        "status": _screener_cache[market]["status"],
        "last_updated": _screener_cache[market]["last_updated"],
        "error": _screener_cache[market]["error"],
        "results": _screener_cache[market]["results"],
        "scan_date": scan_date_str,
        "data_date": _screener_cache[market].get("data_date", "unknown")
    })

@app.route("/api/after_market_report", methods=["GET", "POST"])
def api_after_market_report():
    if request.method == "POST":
        data = request.json or {}
        market = data.get("market", "NSE").upper()
        cached_results = data.get("results", [])[:5]
    else:
        market = request.args.get("market", "NSE").upper()
        with SCREENER_LOCK:
            if market not in _screener_cache or not _screener_cache[market].get("results"):
                return jsonify({"error": "Screener results not available. Please run the scanner first."}), 400
            cached_results = _screener_cache[market]["results"][:5]

    if not cached_results:
        return jsonify({"error": "Screener results not available. Please run the scanner first."}), 400
    
    report_data = []
    import yfinance as yf
    
    target_date = cached_results[0]["date"]
    try:
        test_sym = cached_results[0]["symbol"]
        if market == "NSE" and not test_sym.endswith(".NS") and not test_sym.startswith("^"):
            test_sym += ".NS"
        test_hist = yf.Ticker(test_sym).history(period="5d", interval="5m")
        if not test_hist.empty:
            latest_date_str = test_hist.index.date[-1].strftime("%Y-%m-%d")
            if latest_date_str != target_date:
                return jsonify({"error": f"Intraday data for the projected session ({target_date}) is not yet available. The market is closed or the session hasn't started. (Latest data: {latest_date_str})"}), 400
    except Exception as e:
        pass

    successful = 0
    failed = 0
    open_trades = 0
    never_triggered = 0
    
    for setup in cached_results:
        sym = setup["symbol"]
        yf_sym = sym
        if market == "NSE" and not sym.endswith(".NS") and not sym.startswith("^"):
            yf_sym = sym + ".NS"
            
        try:
            ticker = yf.Ticker(yf_sym)
            hist = ticker.history(period="5d", interval="5m")
            if hist.empty:
                never_triggered += 1
                continue
                
            dates = hist.index.date
            latest_date = dates[-1]
            day_data = hist[hist.index.date == latest_date]
            
            entry = setup["entry"]
            t1 = setup["t1"]
            sl = setup["sl"]
            signal = setup["signal"]
            is_bull = "BULL" in signal.upper()
            
            # Check for gap invalidation
            first_candle = day_data.iloc[0]
            if is_bull and first_candle['Open'] <= sl:
                never_triggered += 1
                continue
            if not is_bull and first_candle['Open'] >= sl:
                never_triggered += 1
                continue
                
            triggered = False
            trigger_time = None
            outcome = "Open"
            
            for index, row in day_data.iterrows():
                low = row['Low']
                high = row['High']
                open_p = row['Open']
                close_p = row['Close']
                
                if not triggered:
                    if is_bull and low <= entry:
                        triggered = True
                        trigger_time = index.strftime("%H:%M")
                    elif not is_bull and high >= entry:
                        triggered = True
                        trigger_time = index.strftime("%H:%M")
                
                if triggered:
                    if is_bull:
                        hit_sl = low <= sl
                        hit_t1 = high >= t1
                        if hit_sl and hit_t1:
                            if close_p >= t1: outcome = "Success"
                            else: outcome = "Failed"
                            break
                        elif hit_sl:
                            outcome = "Failed"
                            break
                        elif hit_t1:
                            outcome = "Success"
                            break
                    else:
                        hit_sl = high >= sl
                        hit_t1 = low <= t1
                        if hit_sl and hit_t1:
                            if close_p <= t1: outcome = "Success"
                            else: outcome = "Failed"
                            break
                        elif hit_sl:
                            outcome = "Failed"
                            break
                        elif hit_t1:
                            outcome = "Success"
                            break
                            
            if triggered:
                if outcome == "Success":
                    successful += 1
                elif outcome == "Failed":
                    failed += 1
                else:
                    open_trades += 1
                    
                report_data.append({
                    "symbol": sym,
                    "signal": signal,
                    "entry": entry,
                    "t1": t1,
                    "sl": sl,
                    "trigger_time": trigger_time,
                    "outcome": outcome,
                    "date": latest_date.strftime("%Y-%m-%d")
                })
            else:
                never_triggered += 1
                
        except Exception as e:
            never_triggered += 1
            print(f"Error evaluating {sym}: {e}")
            
    report_data.sort(key=lambda x: x["trigger_time"])
    
    total_triggered = successful + failed + open_trades
    total_signals = len(cached_results)
    success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
    
    summary = {
        "total_signals": total_signals,
        "triggered_signals": total_triggered,
        "successful": successful,
        "failed": failed,
        "open": open_trades,
        "never_triggered": never_triggered,
        "success_rate": round(success_rate, 2)
    }
    
    return jsonify({
        "summary": summary,
        "report": report_data
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
    
    conn, is_postgres = get_db_connection()
    c = conn.cursor()
    
    param_placeholder = "%s" if is_postgres else "?"
    
    # Check if user exists
    c.execute(f"SELECT trial_start_date, has_agreed_tos FROM users WHERE clerk_id = {param_placeholder}", (clerk_id,))
    user = c.fetchone()
    
    now_str = datetime.utcnow().isoformat()
    
    if not user:
        # New user
        c.execute(f"INSERT INTO users (clerk_id, email, trial_start_date, has_agreed_tos) VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder})",
                  (clerk_id, email, now_str, False))
        trial_start_date = now_str
        has_agreed_tos = False
    else:
        trial_start_date = user[0]
        has_agreed_tos = bool(user[1])
        
    # Log device
    c.execute(f"INSERT INTO devices (clerk_id, machine_number, last_login_at) VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder})",
              (clerk_id, machine_number, now_str))
              
    # Optional: count devices or emails per machine here if you want to block
    # For now we just log it as requested.

    conn.commit()
    conn.close()
    
    # Check trial expiry (15 calendar days)
    trial_start = datetime.fromisoformat(trial_start_date)
    trial_end = trial_start + timedelta(days=15)
    
    now = datetime.utcnow()
    
    if now > trial_end:
        return jsonify({"ok": True, "status": "expired"})
        
    # Calculate remaining calendar days
    remaining_days = max(0, (trial_end - now).days)
            
    if not has_agreed_tos:
        return jsonify({"ok": True, "status": "needs_tos", "remaining_days": remaining_days})
        
    return jsonify({"ok": True, "status": "active", "remaining_days": remaining_days})

@app.route("/api/auth/agree_tos", methods=["POST"])
def auth_agree_tos():
    data = request.json
    clerk_id = data.get("clerk_id")
    
    if not clerk_id:
        return jsonify({"ok": False, "error": "Missing clerk_id"}), 400
        
    conn, is_postgres = get_db_connection()
    c = conn.cursor()
    param_placeholder = "%s" if is_postgres else "?"
    c.execute(f"UPDATE users SET has_agreed_tos = 1 WHERE clerk_id = {param_placeholder}", (clerk_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"ok": True})

@app.route("/payment.html")
def serve_payment():
    return send_from_directory(".", "payment.html")

@app.route("/monthly_report.html")
def serve_monthly_report():
    return send_from_directory(".", "monthly_report.html")

@app.route("/subscription.html")
def serve_subscription():
    return send_from_directory(".", "subscription.html")

@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory("assets", filename)

@app.route("/interactive_disclaimer_spa.html")
def interactive_disclaimer_page():
    return send_from_directory(".", "interactive_disclaimer_spa.html")

@app.route("/daily_summary.html")
def serve_daily_summary():
    return send_from_directory(".", "daily_summary.html")

@app.route("/api/daily_summary")
def api_daily_summary():
    try:
        conn, is_postgres = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT MAX(scan_date) FROM screener_results")
        row = c.fetchone()
        if not row or not row[0]:
            return jsonify({"ok": False, "error": "No scan data found in DB."})
        
        latest_date = row[0]
        c.execute("SELECT market, results_json FROM screener_results WHERE scan_date = %s" if is_postgres else "SELECT market, results_json FROM screener_results WHERE scan_date = ?", (latest_date,))
        rows = c.fetchall()
        
        all_picks = []
        for market, results_json in rows:
            try:
                results = json.loads(results_json)
            except:
                continue
            for r in results:
                trend = r.get("reversal_type", "")
                symbol = r.get("symbol", "")
                intra = r.get("intraday_sq9", {})
                if not intra:
                    continue
                entry = intra.get("entry_level")
                sl = intra.get("sl_level")
                target = intra.get("target_level")
                if not target or target == "NONE":
                    target = intra.get("t1")
                
                if entry and sl and target:
                    all_picks.append({
                        "symbol": symbol,
                        "market": market,
                        "trend": trend,
                        "entry": float(entry),
                        "target": float(target),
                        "sl": float(sl)
                    })
        conn.close()
        
        if not all_picks:
            return jsonify({"ok": True, "date": latest_date, "results": [], "success_rate": 0})
            
        symbols = list(set([p["symbol"] for p in all_picks]))
        try:
            hist = yf.download(symbols, period="5d", group_by="ticker", auto_adjust=False)
        except Exception as e:
            print("yf error:", e)
            hist = None
            
        report = []
        success_count = 0
        total_count = 0
        
        for p in all_picks:
            sym = p["symbol"]
            status = "PENDING"
            if hist is not None and not hist.empty:
                try:
                    df = hist if len(symbols) == 1 else (hist[sym] if sym in hist.columns.levels[0] else None)
                    if df is not None and not df.empty:
                        last_bar = df.iloc[-1]
                        high = float(last_bar["High"])
                        low = float(last_bar["Low"])
                        close = float(last_bar["Close"])
                        
                        p["actual_high"] = round(high, 2)
                        p["actual_low"] = round(low, 2)
                        p["actual_close"] = round(close, 2)
                        
                        if p["trend"] == "BULL REVERSAL":
                            if high >= p["target"]:
                                status = "SUCCESS"
                            elif low <= p["sl"]:
                                status = "FAILED"
                        else:
                            if low <= p["target"]:
                                status = "SUCCESS"
                            elif high >= p["sl"]:
                                status = "FAILED"
                except Exception as e:
                    print("Error checking price for", sym, e)
            
            if status != "PENDING":
                total_count += 1
                if status == "SUCCESS":
                    success_count += 1
            
            p["status"] = status
            report.append(p)
            
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        return jsonify({"ok": True, "date": latest_date, "results": report, "success_rate": round(success_rate, 2)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

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
