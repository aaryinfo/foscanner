"""
Reversal Time Cycle Engine
Computes swing points, cycle projections, confluence zones, Square of 9 levels, and runs historical backtests.
"""

import json
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Union, Optional

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
# ── Market Holidays — Auto-Detected ──────────────────────────────────────────
# Uses the `holidays` library to automatically find Indian national holidays
# for ANY year. No hardcoded dates — works for 2024, 2025, 2026, 2030, etc.
_HOLIDAY_CACHE = {}

try:
    import holidays as _holidays_lib
    _HAS_HOLIDAYS_LIB = True
except ImportError:
    _HAS_HOLIDAYS_LIB = False

def get_nse_holidays(year: int) -> set:
    """
    Get all NSE non-trading holidays for a given year.
    Auto-detected using the `holidays` library (Indian national/gazette holidays).
    Results are cached per year for performance.
    """
    if year in _HOLIDAY_CACHE:
        return _HOLIDAY_CACHE[year]

    holiday_dates = set()
    if _HAS_HOLIDAYS_LIB:
        # India() covers all gazette holidays: Republic Day, Holi, Good Friday,
        # Ambedkar Jayanti, May Day, Independence Day, Gandhi Jayanti, Dussehra,
        # Diwali, Guru Nanak Jayanti, Christmas, Eid, Muharram, etc.
        india_holidays = _holidays_lib.India(years=year)
        for dt, name in india_holidays.items():
            holiday_dates.add(dt.strftime("%Y-%m-%d"))

    _HOLIDAY_CACHE[year] = holiday_dates
    return holiday_dates

def is_non_trading_day(dt_date, market="NSE") -> bool:
    """Check if a date is a non-trading day (weekend or market holiday)."""
    if dt_date.weekday() in (5, 6):
        return True
    if market == "NSE":
        date_str = dt_date.strftime("%Y-%m-%d")
        holidays = get_nse_holidays(dt_date.year)
        if date_str in holidays:
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

# ── Cluster Signal Determination ──────────────────────────────────────────────
def _determine_cluster_signal(pivots: List[Dict]) -> str:
    """
    Determine the reversal signal for a confluence cluster based on Gann Time Cycle theory.
    
    Gann logic:
    - Cycles projected from a Swing HIGH: the stock peaked then fell.
      When the cycle completes, price is expected to reverse back UP → BULL REVERSAL.
    - Cycles projected from a Swing LOW: the stock bottomed then rose.
      When the cycle completes, price is expected to reverse back DOWN → BEAR REVERSAL.
    
    For mixed clusters (cycles from both highs and lows):
    - Use the majority pivot type.
    - If equal count, use the most recent pivot's type.
    """
    high_count = sum(1 for p in pivots if p["pivot_type"] == "high")
    low_count = sum(1 for p in pivots if p["pivot_type"] == "low")
    
    if high_count > 0 and low_count == 0:
        return "BULL REVERSAL"   # All from highs → reversal back up
    elif low_count > 0 and high_count == 0:
        return "BEAR REVERSAL"   # All from lows → reversal back down
    else:
        # Mixed cluster: use majority, or most recent pivot if tied
        if high_count > low_count:
            return "BULL REVERSAL"
        elif low_count > high_count:
            return "BEAR REVERSAL"
        else:
            # Equal count — use the most recent pivot date to break the tie
            most_recent = max(pivots, key=lambda p: p["pivot_date"])
            return "BULL REVERSAL" if most_recent["pivot_type"] == "high" else "BEAR REVERSAL"


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
                    "signal":       _determine_cluster_signal(unique),
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

def compute_intraday_levels(last_close: float, sq9: Dict, signal: str,
                            win_rate: float = 0.393, min_rr: float = 1.6,
                            max_risk_pct: float = 5.0) -> Optional[Dict]:
    """
    Antigravity Positive Expectancy Filter.
    
    Computes intraday Entry/SL/Target levels using Square of 9, enforcing:
    1. Structural SL anchored to -90° or -180° Gann levels (not arbitrary %)
    2. Dynamic target cascade: try ±90° → ±180° → ±360° (pick first with R:R ≥ min_rr)
    3. Expectancy calculation: EV = (win_rate × Reward) - ((1 - win_rate) × Risk)
    4. Only returns valid setups where EV > 0
    
    Returns None if no valid positive-EV setup exists.
    """
    levels = sq9['levels']
    loss_rate = round(1.0 - win_rate, 4)
    
    if 'BULL' in signal.upper():
        bias = 'BULLISH'
        entry = round(levels['+45°'], 2)
        # Structural SL: anchor to -90° (strong Gann support)
        sl_primary = round(levels['-90°'], 2)
        sl_fallback = round(levels['-45°'], 2)
        # Target cascade: try +90° → +180° → +360°
        target_cascade = [
            ('+90°',  round(levels['+90°'], 2)),
            ('+180°', round(levels['+180°'], 2)),
            ('+360°', round(levels['+360°'], 2)),
        ]
    else:
        bias = 'BEARISH'
        entry = round(levels['-45°'], 2)
        # Structural SL: anchor to +90° (strong Gann resistance)
        sl_primary = round(levels['+90°'], 2)
        sl_fallback = round(levels['+45°'], 2)
        # Target cascade: try -90° → -180° → -360°
        target_cascade = [
            ('-90°',  round(levels['-90°'], 2)),
            ('-180°', round(levels['-180°'], 2)),
            ('-360°', round(levels['-360°'], 2)),
        ]
    
    if entry <= 0:
        return None
    
    # ── Stop Loss Optimization ────────────────────────────────────────────
    # Use structural -90° level. If risk exceeds max_risk_pct, fall back to -45°
    sl = sl_primary
    risk_check = round(abs(entry - sl) / entry * 100, 2)
    sl_level = '-90°' if bias == 'BULLISH' else '+90°'
    
    if risk_check > max_risk_pct:
        sl = sl_fallback
        sl_level = '-45°' if bias == 'BULLISH' else '+45°'
    
    risk = round(abs(entry - sl), 2)
    if risk <= 0:
        return None
    
    risk_pct = round((risk / entry) * 100, 2)
    
    # ── Dynamic Target Selection (Cascade) ────────────────────────────────
    # Try each SQ9 level in order; pick the first that satisfies R:R ≥ min_rr
    selected_target = None
    selected_level = None
    rejection_log = []
    
    for level_name, target_price in target_cascade:
        reward = round(abs(target_price - entry), 2)
        rr = round(reward / risk, 2) if risk > 0 else 0
        if rr >= min_rr:
            selected_target = target_price
            selected_level = level_name
            break
        else:
            rejection_log.append(f"{level_name} R:R 1:{rr} (below 1:{min_rr})")
    
    if selected_target is None:
        # No SQ9 level provides adequate R:R — discard setup entirely
        return {
            'signal': signal, 'bias': bias, 'entry': entry, 'sl': sl,
            't1': target_cascade[0][1], 't2': target_cascade[1][1],
            'risk': risk, 'risk_pct': risk_pct,
            'reward1': 0, 'reward1_pct': 0, 'reward2': 0, 'reward2_pct': 0,
            'risk_reward_t1': '1:0', 'risk_reward_t2': '1:0',
            'rr1_num': 0, 'rr2_num': 0,
            'target_level': 'NONE', 'sl_level': sl_level,
            'expectancy': round(-(loss_rate * risk), 2),
            'expectancy_pct': round(-(loss_rate * risk_pct), 2),
            'win_rate': win_rate,
            'is_valid': False,
            'rejection_reason': 'No SQ9 level meets minimum R:R of 1:' + str(min_rr),
            'rejection_log': rejection_log,
            'valid_for': 'REJECTED'
        }
    
    # ── Compute final metrics for selected target ─────────────────────────
    t1 = selected_target
    reward1 = round(abs(t1 - entry), 2)
    reward1_pct = round((reward1 / entry) * 100, 2)
    rr1 = round(reward1 / risk, 2) if risk > 0 else 0
    
    # T2 is the next level after the selected one in the cascade
    t2_candidates = [tp for ln, tp in target_cascade if abs(tp - entry) > abs(t1 - entry)]
    t2 = t2_candidates[0] if t2_candidates else t1
    reward2 = round(abs(t2 - entry), 2)
    reward2_pct = round((reward2 / entry) * 100, 2)
    rr2 = round(reward2 / risk, 2) if risk > 0 else 0
    
    # ── Expectancy Calculation ────────────────────────────────────────────
    # EV = (WinRate × Reward) - (LossRate × Risk)
    ev = round((win_rate * reward1) - (loss_rate * risk), 2)
    ev_pct = round((win_rate * reward1_pct) - (loss_rate * risk_pct), 2)
    
    is_valid = ev > 0
    rejection_reason = None if is_valid else f'Negative EV: ₹{ev} (win {win_rate*100}% × ₹{reward1} - lose {loss_rate*100}% × ₹{risk})'
    
    return {
        'signal': signal,
        'bias': bias,
        'entry': entry,
        'sl': sl,
        't1': t1,
        't2': t2,
        'risk': risk,
        'risk_pct': risk_pct,
        'reward1': reward1,
        'reward1_pct': reward1_pct,
        'reward2': reward2,
        'reward2_pct': reward2_pct,
        'risk_reward_t1': f'1:{rr1}',
        'risk_reward_t2': f'1:{rr2}',
        'rr1_num': rr1,
        'rr2_num': rr2,
        'target_level': selected_level,
        'sl_level': sl_level,
        'expectancy': ev,
        'expectancy_pct': ev_pct,
        'win_rate': win_rate,
        'is_valid': is_valid,
        'rejection_reason': rejection_reason,
        'rejection_log': rejection_log,
        'valid_for': 'Next intraday session' if is_valid else 'REJECTED'
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
        else:
            html += f"<p>The most recent structural pivot was a <strong>Swing Low</strong> at ₹{last_low_price:,.2f} on {last_low_dt.strftime('%d %b %Y')}. "
            html += f"Prior to that, a <strong>Swing High</strong> was established at ₹{last_high_price:,.2f} on {last_high_dt.strftime('%d %b %Y')}.</p>"
    else:
        html += "<p>Insufficient recent structural swings to establish short-term trend.</p>"
    
    # Derive trade bias directly from the confluence signal (which is now correctly determined)
    current_bias = "BEARISH" if "BEAR" in nxt_signal else "BULLISH"
    dist_high = abs(last_close - sq9['levels']['+90°'])
    dist_low = abs(last_close - sq9['levels']['-90°'])
    if dist_high < dist_low:
        html += f"<p>Price is currently hovering near overhead resistance (₹{sq9['levels']['+90°']:.2f}).</p>"
    else:
        html += f"<p>Price is currently hovering near underlying support (₹{sq9['levels']['-90°']:.2f}).</p>"
    html += "</div>"

    # Trade Setup Section — Antigravity Positive Expectancy Filter
    intraday = compute_intraday_levels(last_close, sq9, nxt_signal if nxt_signal else "BULL REVERSAL")
    html += "<div class='report-section' style='margin-top:14px; padding-top:12px; border-top:1px solid var(--border);'>"
    
    if intraday and intraday.get('is_valid'):
        html += f"<h4>✅ Intraday Trade Setup ({intraday['bias']}) — Positive Expectancy:</h4>"
        html += f"<p>Antigravity filter passed. Target selected at <strong>{intraday['target_level']}</strong> SQ9 level. "
        html += f"SL anchored to structural <strong>{intraday['sl_level']}</strong> Gann level.</p>"
        
        # Show rejection log if lower levels were skipped
        if intraday.get('rejection_log'):
            html += "<p style='font-size:11px;color:var(--muted);'>Target cascade: "
            html += " → ".join(intraday['rejection_log'])
            html += f" → <strong style='color:var(--green);'>{intraday['target_level']} ✓</strong></p>"
        
        html += "<ul>"
        html += f"<li><strong>Entry:</strong> ₹{intraday['entry']:,.2f}</li>"
        html += f"<li><strong>Stop Loss ({intraday['sl_level']}):</strong> ₹{intraday['sl']:,.2f} &nbsp;(Risk: ₹{intraday['risk']:,.2f} | {intraday['risk_pct']}%)</li>"
        html += f"<li><strong>Target 1 ({intraday['target_level']}):</strong> ₹{intraday['t1']:,.2f} &nbsp;(Reward: ₹{intraday['reward1']:,.2f} | R:R {intraday['risk_reward_t1']})</li>"
        html += f"<li><strong>Target 2:</strong> ₹{intraday['t2']:,.2f} &nbsp;(R:R {intraday['risk_reward_t2']})</li>"
        html += "</ul>"
        
        # Expectancy box
        ev_color = 'var(--green)' if intraday['expectancy'] > 0 else 'var(--red)'
        html += f"<div style='margin-top:10px;padding:8px 12px;background:rgba(0,200,150,0.08);border:1px solid rgba(0,200,150,0.2);border-radius:6px;'>"
        html += f"<strong>Expected Value (EV):</strong> <span style='color:{ev_color};font-weight:700;font-size:14px;'>₹{intraday['expectancy']:,.2f}</span> per trade"
        html += f"<br><span style='font-size:11px;color:var(--muted);'>Formula: ({intraday['win_rate']*100:.1f}% × ₹{intraday['reward1']:,.2f}) − ({(1-intraday['win_rate'])*100:.1f}% × ₹{intraday['risk']:,.2f})</span>"
        html += "</div>"
        html += "<p style='font-size:11px;color:var(--muted);margin-top:8px;'><em>⚠ Levels valid for intraday session only. Recalculate for next session.</em></p>"
    elif intraday:
        html += f"<h4>❌ No Valid Setup — Negative Expectancy:</h4>"
        html += f"<p style='color:var(--red);'>{intraday.get('rejection_reason', 'Setup rejected by Antigravity filter.')}</p>"
        if intraday.get('rejection_log'):
            html += "<p style='font-size:11px;color:var(--muted);'>Checked: " + " → ".join(intraday['rejection_log']) + "</p>"
        html += f"<p style='font-size:11px;color:var(--muted);'>EV = ₹{intraday.get('expectancy', 0):,.2f} (negative — trade would lose money over time)</p>"
    else:
        html += "<h4>❌ No Valid Setup Available</h4>"
        html += "<p style='color:var(--muted);'>Insufficient data to compute intraday levels.</p>"
    
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
    chart_opens = chart_df["Open"].values
    chart_highs = chart_df["High"].values
    chart_lows = chart_df["Low"].values
    chart_closes = chart_df["Close"].values
    ohlc = [
        {
            "date": dates[i],
            "open": round(float(chart_opens[i]), 2),
            "high": round(float(chart_highs[i]), 2),
            "low": round(float(chart_lows[i]), 2),
            "close": round(float(chart_closes[i]), 2),
        }
        for i in range(len(chart_df))
    ]

    # Signal is now correctly determined by _determine_cluster_signal() in find_confluence_zones()
    # No blanket override needed — each confluence zone has the right signal based on its cycle sources

    # Generate detailed description
    description = generate_description(symbol, last_close, last_date, filtered_confluence, sq9, backtest, top_highs, top_lows)

    # Clean up non-serialisable datetime objects before returning JSON
    for c in filtered_confluence:
        if "date_obj" in c:
            del c["date_obj"]

    # Compute intraday trade levels (Antigravity Positive Expectancy Filter)
    future_conf = [c for c in filtered_confluence if c.get('days_away', -1) >= 0]
    intraday_signal = future_conf[0]['signal'] if future_conf else ('BULL REVERSAL' if top_highs and top_lows and str(top_highs[-1][0]) > str(top_lows[-1][0]) else 'BEAR REVERSAL')
    intraday_levels = compute_intraday_levels(last_close, sq9, intraday_signal)
    setup_valid = intraday_levels is not None and intraday_levels.get('is_valid', False)

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
        "intraday_levels": intraday_levels,
        "setup_valid":  setup_valid,
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
    print(f"Sq9 +90     : {result['square_of_9']['levels']['+90°']}")
    print(f"Backtest Acc: {result['backtest']['accuracy']}%")
    
    # Antigravity EV validation
    intra = result.get('intraday_levels')
    if intra:
        print(f"\n-- Antigravity Filter --")
        print(f"  Setup Valid : {intra.get('is_valid', 'N/A')}")
        print(f"  Bias        : {intra.get('bias')}")
        print(f"  Entry       : Rs.{intra.get('entry')}")
        print(f"  SL ({intra.get('sl_level','?')}): Rs.{intra.get('sl')}  Risk: {intra.get('risk_pct')}%")
        print(f"  T1 ({intra.get('target_level','?')}): Rs.{intra.get('t1')}  R:R {intra.get('risk_reward_t1')}")
        print(f"  T2          : Rs.{intra.get('t2')}  R:R {intra.get('risk_reward_t2')}")
        print(f"  Expectancy  : Rs.{intra.get('expectancy')} ({intra.get('expectancy_pct')}%)")
        if intra.get('rejection_log'):
            print(f"  Cascade Log : {' -> '.join(intra['rejection_log'])}")
        if not intra.get('is_valid'):
            print(f"  REJECTED    : {intra.get('rejection_reason')}")
    else:
        print("  Intraday levels: None (no data)")
    
    print(f"Setup Valid : {result.get('setup_valid', False)}")
    print("Engine OK")
