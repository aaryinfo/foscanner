"""
Reversal Time Cycle Engine
Computes swing points, cycle projections, confluence zones, Square of 9 levels, and runs historical backtests.
"""

import json
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd

# ── Gann Core Cycles (calendar days) ─────────────────────────────────────────
GANN_CYCLES = [30, 45, 60, 90, 120, 144, 180, 270, 360, 720, 1095, 1825, 2555, 3650, 5475, 7300]
CYCLE_LABELS = {
    30:  "1M",  45:  "45D", 60:  "2M",  90:  "Qtr",
    120: "4M",  144: "144D",180: "6M",  270: "9M",
    360: "1Yr", 720: "2Yr", 1095: "3Yr", 1825: "5Yr",
    2555: "7Yr", 3650: "10Yr", 5475: "15Yr", 7300: "20Yr"
}


# ── Swing Point Detection ─────────────────────────────────────────────────────
def find_swing_points(df: pd.DataFrame, window: int = 10) -> Tuple[List, List]:
    """
    Find swing highs and swing lows using a rolling window.
    Returns (swing_highs, swing_lows) as lists of (date, price) tuples.
    """
    highs, lows = [], []
    prices_h = df["High"].values
    prices_l = df["Low"].values
    dates    = df.index.tolist()
    n        = len(df)

    for i in range(window, n - window):
        # Swing High: highest in window on both sides
        if prices_h[i] == max(prices_h[i - window: i + window + 1]):
            highs.append((dates[i], float(prices_h[i])))
        # Swing Low: lowest in window on both sides
        if prices_l[i] == min(prices_l[i - window: i + window + 1]):
            lows.append((dates[i], float(prices_l[i])))

    return highs, lows

# ── Cycle Projections ────────────────────────────────────────────────────
# ── Market Holidays & Non-Trading Days ───────────────────────────────────────
NSE_HOLIDAYS_2026 = {
    "2026-01-26", "2026-03-03", "2026-03-26", "2026-03-31",
    "2026-04-03", "2026-04-14", "2026-05-01", "2026-05-28",
    "2026-06-26", "2026-09-14", "2026-10-02", "2026-10-20",
    "2026-11-10", "2026-11-24", "2026-12-25"
}

def is_non_trading_day(dt_date, market="NSE") -> bool:
    if dt_date.weekday() in (5, 6):
        return True
    if market == "NSE":
        date_str = dt_date.strftime("%Y-%m-%d")
        if date_str in NSE_HOLIDAYS_2026:
            return True
    return False

def project_cycles(pivot_date: Union[str, datetime, pd.Timestamp], pivot_price: float,
                   pivot_type: str, cycles=GANN_CYCLES, today=None) -> List[Dict]:
    """
    From a swing pivot, project all cycle dates forward.
    pivot_type: 'high' or 'low'
    """
    if isinstance(pivot_date, pd.Timestamp):
        pivot_date = pivot_date.to_pydatetime()
    elif isinstance(pivot_date, str):
        try:
            pivot_date = datetime.strptime(pivot_date, "%Y-%m-%d")
        except Exception:
            pass
    elif not isinstance(pivot_date, datetime) and hasattr(pivot_date, "year"):
        pivot_date = datetime(pivot_date.year, pivot_date.month, pivot_date.day)

    if today is None:
        today = datetime.today()

    pivot_date_str = pivot_date.strftime("%Y-%m-%d")
    pivot_price_round = round(pivot_price, 2)

    projections = []
    for days in cycles:
        target_date = pivot_date + timedelta(days=days)

        projections.append({
            "pivot_date":   pivot_date_str,
            "pivot_price":  pivot_price_round,
            "pivot_type":   pivot_type,
            "cycle_days":   days,
            "cycle_label":  CYCLE_LABELS.get(days, f"{days}D"),
            "target_date":  target_date.strftime("%Y-%m-%d"),
            "target_dt":    target_date, # native datetime object for fast confluence grouping
            "days_away":    (target_date - today).days,
        })
    return projections

# ── Confluence Detection ──────────────────────────────────────────────────────
def find_confluence_zones(all_projections: List[Dict],
                           tolerance_days: int = 3) -> List[Dict]:
    """
    Find dates where 2+ cycle projections cluster within tolerance_days.
    These are high-probability turning point zones.
    """
    from collections import defaultdict
    date_map = defaultdict(list)

    # Use native datetime objects directly (no slow strptime calls)
    for proj in all_projections:
        td = proj.get("target_dt")
        if td:
            date_map[td].append(proj)

    confluence = []
    dates_sorted = sorted(date_map.keys())
    skip_dates = set()

    for i, d in enumerate(dates_sorted):
        if d in skip_dates:
            continue
            
        cluster = list(date_map[d])
        # Merge nearby dates within tolerance
        for j in range(i + 1, len(dates_sorted)):
            if (dates_sorted[j] - d).days <= tolerance_days:
                cluster.extend(date_map[dates_sorted[j]])
                skip_dates.add(dates_sorted[j])
            else:
                break

        if len(cluster) >= 2:
            # Deduplicate
            seen = set()
            unique = []
            for p in cluster:
                key = (p["pivot_date"], p["cycle_days"])
                if key not in seen:
                    seen.add(key)
                    unique.append(p)

            if len(unique) >= 2:
                pivot_types = set(p["pivot_type"] for p in unique)
                strength = len(unique)
                
                min_dt = min(p["target_dt"] for p in unique)
                max_dt = max(p["target_dt"] for p in unique)
                
                min_str = min_dt.strftime("%Y-%m-%d")
                max_str = max_dt.strftime("%Y-%m-%d")
                date_display = min_str if min_str == max_str else f"{min_str} to {max_str}"
                
                confluence.append({
                    "date":         d.strftime("%Y-%m-%d"),
                    "date_display": date_display,
                    "date_obj":     d, # store native date object for fast backtesting
                    "count":        strength,
                    "cycles":       [f"{p['cycle_label']} from {p['pivot_type'].upper()} {p['pivot_date']}" for p in unique],
                    "signal":       "REVERSAL" if len(pivot_types) > 1 else
                                    ("BEAR REVERSAL" if "high" in pivot_types else "BULL REVERSAL"),
                    "strength":     "STRONG" if strength >= 4 else
                                    "MODERATE" if strength >= 2 else "WEAK",
                    "days_away":    (d.date() - datetime.today().date()).days,
                })

    # Sort by date
    confluence.sort(key=lambda x: x["date"])
    return confluence

# ── Square of 9 ──────────────────────────────────────────────────────────────
def square_of_9(price: float) -> Dict:
    """
    Calculate key Square of 9 price levels from a given price.
    Returns resistance and support levels at 45°, 90°, 135°, 180°, 225°, 270°, 315°, 360°.
    """
    root    = math.sqrt(price)
    angles  = [45, 90, 135, 180, 225, 270, 315, 360]
    levels  = {}

    for angle in angles:
        add  = angle / 360.0
        up   = round((root + add) ** 2, 2)
        down = round((root - add) ** 2, 2)
        if down < 0:
            down = 0.0
        levels[f"+{angle}°"] = up
        levels[f"-{angle}°"] = down

    return {
        "base_price":  round(price, 2),
        "sqrt_price":  round(root, 4),
        "levels":      levels,
    }

# ── Backtest Logic ────────────────────────────────────────────────────────────
def backtest_confluences(highs: List, lows: List, confluence_zones: List[Dict]) -> Dict:
    """
    Backtest historical confluence zones against actual swing highs/lows.
    Returns summary statistics and historical results.
    """
    today_str = datetime.today().strftime("%Y-%m-%d")
    past_confluences = [c for c in confluence_zones if c["date"] < today_str]

    if not past_confluences:
        return {
            "accuracy": 0.0,
            "total_zones": 0,
            "success_count": 0,
            "failed_count": 0,
            "results": []
        }

    # Generate set of all calendar dates within 3 days of any swing point for O(1) hash lookups
    reversal_dates = set()
    pivots_list = []
    
    for d, p in highs:
        d_dt = d.to_pydatetime() if hasattr(d, 'to_pydatetime') else d
        if not isinstance(d_dt, datetime) and hasattr(d_dt, 'year'):
            d_dt = datetime(d_dt.year, d_dt.month, d_dt.day)
        pivots_list.append((d_dt, "SWING HIGH"))
        for offset in range(-3, 4):
            reversal_dates.add((d_dt + timedelta(days=offset)).strftime("%Y-%m-%d"))
            
    for d, p in lows:
        d_dt = d.to_pydatetime() if hasattr(d, 'to_pydatetime') else d
        if not isinstance(d_dt, datetime) and hasattr(d_dt, 'year'):
            d_dt = datetime(d_dt.year, d_dt.month, d_dt.day)
        pivots_list.append((d_dt, "SWING LOW"))
        for offset in range(-3, 4):
            reversal_dates.add((d_dt + timedelta(days=offset)).strftime("%Y-%m-%d"))

    success_count = 0
    test_results = []

    for c in past_confluences:
        # O(1) check
        is_success = c["date"] in reversal_dates
        
        matched_pivot_type = None
        matched_date_str = None

        if is_success:
            success_count += 1
            # Search for exact matching pivot details (only for logged successes)
            c_date = c.get("date_obj")
            if not c_date:
                try:
                    c_date = datetime.strptime(c["date"], "%Y-%m-%d")
                except Exception:
                    continue
            
            for p_dt, p_type in pivots_list:
                if isinstance(p_dt, datetime) and abs((p_dt - c_date).days) <= 3:
                    matched_pivot_type = p_type
                    matched_date_str = p_dt.strftime("%Y-%m-%d")
                    break
        
        test_results.append({
            "date": c["date"],
            "signal": c["signal"],
            "strength": c["strength"],
            "count": c["count"],
            "success": is_success,
            "matched_type": matched_pivot_type,
            "matched_date": matched_date_str
        })

    accuracy = (success_count / len(past_confluences)) * 100 if past_confluences else 0.0

    return {
        "accuracy": round(accuracy, 1),
        "total_zones": len(past_confluences),
        "success_count": success_count,
        "failed_count": len(past_confluences) - success_count,
        "results": test_results[-30:]  # Return last 30 historical zones for table
    }


# ── Dynamic Report Generator ──────────────────────────────────────────────────
def generate_description(symbol: str, last_close: float, last_date: str, 
                         confluence: List[Dict], sq9: Dict, backtest: Dict,
                         top_highs: List = None, top_lows: List = None) -> str:
    """
    Generate HTML-formatted financial analysis detailing W.D. cycle results, Chart Analysis, and Trade Setup.
    """
    future_conf = [c for c in confluence if c["days_away"] >= 0]
    
    html = f"<div class='report-section'>"
    html += f"<p>As of <strong>{last_date}</strong>, <strong>{symbol}</strong> is trading at <strong>₹{last_close:,.2f}</strong>. "
    
    if future_conf:
        nxt = future_conf[0]
        html += f"The next key forward cycle confluence date is projected for <strong>{nxt['date']}</strong> (in <strong>{nxt['days_away']} days</strong>). "
        html += f"This is classified as a <strong>{nxt['strength']}</strong> strength zone indicating a potential <strong>{nxt['signal']}</strong>. "
        html += f"This zone represents a cluster of {nxt['count']} overlapping calendar cycles (including {', '.join(nxt['cycles'][:2])}).</p>"
    else:
        html += "No major cycle confluence zones are projected in the next 365 calendar days.</p>"
    
    html += "</div>"

    # Chart Analysis Section
    last_high_dt = None
    last_low_dt = None
    if top_highs:
        last_high_date, last_high_price = top_highs[-1]
        last_high_dt = datetime.strptime(str(last_high_date)[:10], "%Y-%m-%d")
    if top_lows:
        last_low_date, last_low_price = top_lows[-1]
        last_low_dt = datetime.strptime(str(last_low_date)[:10], "%Y-%m-%d")
        
    html += "<div class='report-section' style='margin-top:14px; padding-top:12px; border-top:1px solid var(--border);'>"
    html += "<h4>Chart Analysis & Current Structure:</h4>"
    nxt_signal = nxt['signal'] if future_conf else ""
    if last_high_dt and last_low_dt:
        if last_high_dt > last_low_dt:
            html += f"<p>The most recent structural pivot was a <strong>Swing High</strong> at ₹{last_high_price:,.2f} on {last_high_dt.strftime('%d %b %Y')}. "
            html += f"Prior to that, a <strong>Swing Low</strong> was established at ₹{last_low_price:,.2f} on {last_low_dt.strftime('%d %b %Y')}.</p>"
            current_bias = "BEARISH" if nxt_signal in ["REVERSAL", "BEAR REVERSAL"] else "BULLISH"
        else:
            html += f"<p>The most recent structural pivot was a <strong>Swing Low</strong> at ₹{last_low_price:,.2f} on {last_low_dt.strftime('%d %b %Y')}. "
            html += f"Prior to that, a <strong>Swing High</strong> was established at ₹{last_high_price:,.2f} on {last_high_dt.strftime('%d %b %Y')}.</p>"
            current_bias = "BULLISH" if nxt_signal in ["REVERSAL", "BULL REVERSAL"] else "BEARISH"
    else:
        current_bias = "BULLISH" if "BULL" in nxt_signal else "BEARISH"
        html += "<p>Insufficient recent structural swings to establish short-term trend.</p>"
        
    dist_high = abs(last_close - sq9['levels']['+90°'])
    dist_low = abs(last_close - sq9['levels']['-90°'])
    if dist_high < dist_low:
        html += f"<p>Price is currently hovering near overhead resistance (₹{sq9['levels']['+90°']:.2f}).</p>"
    else:
        html += f"<p>Price is currently hovering near underlying support (₹{sq9['levels']['-90°']:.2f}).</p>"
    html += "</div>"

    # Trade Setup Section
    html += "<div class='report-section' style='margin-top:14px; padding-top:12px; border-top:1px solid var(--border);'>"
    html += f"<h4>Actionable Trade Setup ({current_bias}):</h4>"
    html += f"<p>Based on the predicted <strong>{current_bias}</strong> momentum shift around the Confluence Date:</p>"
    html += "<ul>"
    if current_bias == "BULLISH":
        html += f"<li><strong>Entry:</strong> Buy momentum breakout above <strong>₹{sq9['levels']['+45°']:.2f}</strong></li>"
        html += f"<li><strong>Stop Loss (SL):</strong> Strict closing basis below <strong>₹{sq9['levels']['-45°']:.2f}</strong></li>"
        html += f"<li><strong>Targets:</strong> <strong>₹{sq9['levels']['+90°']:.2f}</strong> (T1) and <strong>₹{sq9['levels']['+180°']:.2f}</strong> (T2)</li>"
    else:
        html += f"<li><strong>Entry:</strong> Sell breakdown below <strong>₹{sq9['levels']['-45°']:.2f}</strong></li>"
        html += f"<li><strong>Stop Loss (SL):</strong> Strict closing basis above <strong>₹{sq9['levels']['+45°']:.2f}</strong></li>"
        html += f"<li><strong>Targets:</strong> <strong>₹{sq9['levels']['-90°']:.2f}</strong> (T1) and <strong>₹{sq9['levels']['-180°']:.2f}</strong> (T2)</li>"
    html += "</ul>"
    html += "</div>"
    
    html += "<div class='report-section' style='margin-top:14px; padding-top:12px; border-top:1px solid var(--border);'>"
    html += "<h4>Square of 9 Price Target Matrix:</h4>"
    html += f"<p>Derived from the base price index of ₹{sq9['base_price']}:</p>"
    html += "<ul>"
    html += f"<li>Overhead Resistance: <strong>₹{sq9['levels']['+90°']:.2f}</strong> (+90°) | <strong>₹{sq9['levels']['+180°']:.2f}</strong> (+180°)</li>"
    html += f"<li>Downside Support: <strong>₹{sq9['levels']['-90°']:.2f}</strong> (-90°) | <strong>₹{sq9['levels']['-180°']:.2f}</strong> (-180°)</li>"
    html += "</ul>"
    html += "</div>"

    html += "<div class='report-section' style='margin-top:14px; padding-top:12px; border-top:1px solid var(--border);'>"
    html += "<h4>Model Accuracy Verification:</h4>"
    html += f"<p>We historically backtested this model for {symbol} by comparing all past cycle confluences against actual swing pivot highs and lows (using a ±3-day tolerance window).</p>"
    html += "<ul>"
    html += f"<li><strong>Model Accuracy:</strong> <span style='color:var(--gold); font-weight:700;'>{backtest['accuracy']}%</span></li>"
    html += f"<li><strong>Total Confluences Detected:</strong> {backtest['total_zones']} zones</li>"
    html += f"<li><strong>Successful turning points:</strong> {backtest['success_count']}</li>"
    html += f"<li><strong>Failed projections:</strong> {backtest['failed_count']}</li>"
    html += "</ul>"
    html += "</div>"
    
    return html

# ── Master Analysis Function ──────────────────────────────────────────────────
def analyse(df: pd.DataFrame, symbol: str, swing_window: int = 10, period: str = "2y") -> Dict:
    """
    Full cycle analysis pipeline. Returns JSON-serialisable dict.
    """
    df = df.copy()
    df.index = pd.to_datetime(df.index)

    # Last known price
    last_close  = float(df["Close"].iloc[-1])
    last_date   = df.index[-1].strftime("%Y-%m-%d")

    # Swing points
    highs, lows = find_swing_points(df, window=swing_window)
    
    # We use all historical pivots for generating the full set of projections (for backtesting)
    today = datetime.today()
    all_proj_full = []
    for date, price in highs:
        all_proj_full.extend(project_cycles(date, price, "high", today=today))
    for date, price in lows:
        all_proj_full.extend(project_cycles(date, price, "low", today=today))

    # Generate full historical confluence zones list
    confluence_full = find_confluence_zones(all_proj_full, tolerance_days=3)

    # Backtest historical performance
    backtest = backtest_confluences(highs, lows, confluence_full)

    # For UI chart display, filter confluences to recent past + future (-30 to +365 days)
    today = datetime.today()
    filtered_confluence = [c for c in confluence_full
                           if "date_obj" in c and -30 <= (c["date_obj"] - today).days <= 365]

    # For cycle overlays, keep recent pivots to avoid clutter (last 3 of each)
    top_highs   = highs[-3:] if len(highs) >= 3 else highs
    top_lows    = lows[-3:]  if len(lows)  >= 3 else lows
    
    # Square of 9 from last close
    sq9 = square_of_9(last_close)

    # OHLC for chart (scale chart window with period)
    if period == "1y":
        chart_df = df.tail(252)
    elif period == "2y":
        chart_df = df.tail(504)
    elif period == "3y":
        chart_df = df.tail(756)
    elif period == "5y":
        chart_df = df.tail(1260)
    elif period == "10y":
        chart_df = df.tail(2520)
    elif period == "20y":
        chart_df = df.tail(5040)
    else:
        chart_df = df

    dates = chart_df.index.strftime("%Y-%m-%d").tolist()
    opens = chart_df["Open"].values
    highs = chart_df["High"].values
    lows = chart_df["Low"].values
    closes = chart_df["Close"].values
    ohlc = [
        {
            "date": dates[i],
            "open": round(float(opens[i]), 2),
            "high": round(float(highs[i]), 2),
            "low": round(float(lows[i]), 2),
            "close": round(float(closes[i]), 2),
        }
        for i in range(len(chart_df))
    ]

    # Update signals based on actual current market structure bias to sync report and screener
    last_high_dt = None
    last_low_dt = None
    if top_highs:
        last_high_dt = datetime.strptime(str(top_highs[-1][0])[:10], "%Y-%m-%d")
    if top_lows:
        last_low_dt = datetime.strptime(str(top_lows[-1][0])[:10], "%Y-%m-%d")

    current_trend = "UNKNOWN"
    if last_high_dt and last_low_dt:
        if last_high_dt > last_low_dt:
            current_trend = "DOWN" # Trend is down, next reversal is BULLISH
        else:
            current_trend = "UP"   # Trend is up, next reversal is BEARISH

    for c in filtered_confluence:
        if current_trend != "UNKNOWN":
            c["signal"] = "BULL REVERSAL" if current_trend == "DOWN" else "BEAR REVERSAL"

    # Generate detailed description
    description = generate_description(symbol, last_close, last_date, filtered_confluence, sq9, backtest, top_highs, top_lows)

    # Clean up non-serialisable datetime objects before returning JSON
    for c in filtered_confluence:
        if "date_obj" in c:
            del c["date_obj"]

    return {
        "symbol":       symbol,
        "last_close":   last_close,
        "last_date":    last_date,
        "swing_highs":  [(str(d.date()) if hasattr(d,'date') else str(d), p) for d,p in top_highs],
        "swing_lows":   [(str(d.date()) if hasattr(d,'date') else str(d), p) for d,p in top_lows],
        "projections":  sorted([
            {
                "pivot_date": p["pivot_date"],
                "pivot_price": p["pivot_price"],
                "pivot_type": p["pivot_type"],
                "cycle_days": p["cycle_days"],
                "cycle_label": p["cycle_label"],
                "target_date": p["target_date"],
                "days_away": p["days_away"]
            }
            for p in all_proj_full if "target_dt" in p and -30 <= (p["target_dt"] - today).days <= 365
        ], key=lambda x: x["target_date"]),
        "confluence":   filtered_confluence,
        "square_of_9":  sq9,
        "ohlc":         ohlc,
        "backtest":     backtest,
        "description":  description
    }

if __name__ == "__main__":
    # Quick self-test with synthetic data
    dates = pd.date_range("2023-01-01", periods=400, freq="B")
    np.random.seed(42)
    close = 1000 + np.cumsum(np.random.randn(400) * 15)
    df = pd.DataFrame({
        "Open":  close - np.random.rand(400) * 10,
        "High":  close + np.random.rand(400) * 20,
        "Low":   close - np.random.rand(400) * 20,
        "Close": close,
    }, index=dates)
    result = analyse(df, "TEST")
    print(f"Swing Highs : {result['swing_highs']}")
    print(f"Swing Lows  : {result['swing_lows']}")
    print(f"Confluence  : {len(result['confluence'])} zones found")
    print(f"Sq9 +90°    : {result['square_of_9']['levels']['+90°']}")
    print(f"Backtest Acc: {result['backtest']['accuracy']}%")
    print("Engine OK")
