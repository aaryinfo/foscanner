import pandas as pd
import datetime
from .scoring import calculate_daily_astro_score, calculate_stock_astro_score

def run_backtest(df: pd.DataFrame, ticker: str = "^NSEI") -> dict:
    """
    Run backtest on historical dataframe to see correlation of 
    Astro Bias Score with Next Day Return.
    """
    if df.empty or 'Close' not in df.columns:
        return {"error": "Invalid dataframe"}
        
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df.set_index('Date', inplace=True)
    df['Daily_Return'] = df['Close'].pct_change() * 100
    df['Next_Day_Return'] = df['Daily_Return'].shift(-1)
    
    # 1. Pre-load Astro Forecast JSON to avoid heavy computation on Vercel
    precalculated_scores = {}
    try:
        import json
        import os
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'astro_forecast.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                forecasts = json.load(f)
                for f_data in forecasts:
                    precalculated_scores[f_data['date']] = f_data
    except Exception as e:
        print(f"Error loading historical astro scores: {e}")

    try:
        from gann_engine import is_non_trading_day
    except ImportError:
        is_non_trading_day = lambda d, m: False # Fallback

    import datetime
    today = datetime.datetime.utcnow().date()
    start_date = today - datetime.timedelta(days=60)
    
    date_list = [start_date + datetime.timedelta(days=x) for x in range(61)]
    
    bullish_hits = 0
    bullish_total = 0
    bearish_hits = 0
    bearish_total = 0
    
    day_by_day = []
    
    for d in date_list:
        date_str = d.strftime("%Y-%m-%d")
        
        # Check if holiday
        if is_non_trading_day(d, "NSE"):
            day_by_day.append({
                "date": date_str,
                "score": "-",
                "bias": "Holiday",
                "actual_return": "-",
                "is_hit": "Holiday"
            })
            continue
            
        if d not in df.index:
            # Data might be missing or not updated
            day_by_day.append({
                "date": date_str,
                "score": "-",
                "bias": "Pending/No Data",
                "actual_return": "-",
                "is_hit": "Pending"
            })
            continue
            
        row = df.loc[d]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[-1] # Take the last if duplicates
            
        price = row['Close']
        macro_report = precalculated_scores.get(date_str)
        # Convert date to datetime for scoring
        d_datetime = datetime.datetime.combine(d, datetime.datetime.min.time())
        score_report = calculate_stock_astro_score(d_datetime, ticker, price, macro_report)
        score = score_report['score']
        
        next_ret = row['Next_Day_Return']
        is_hit = None
        
        if pd.isna(next_ret):
            # Pending result
            if score >= 30:
                bullish_total += 1
            elif score <= -30:
                bearish_total += 1
            
            day_by_day.append({
                "date": date_str,
                "score": score,
                "bias": score_report['bias'],
                "actual_return": "-",
                "is_hit": "Pending"
            })
            continue

        if score >= 30: # Bullish signal
            bullish_total += 1
            if next_ret > 0:
                bullish_hits += 1
                is_hit = True
            else:
                is_hit = False
        elif score <= -30: # Bearish signal
            bearish_total += 1
            if next_ret < 0:
                bearish_hits += 1
                is_hit = True
            else:
                is_hit = False
                
        day_by_day.append({
            "date": date_str,
            "score": score,
            "bias": score_report['bias'],
            "actual_return": round(next_ret, 2),
            "is_hit": is_hit
        })
                
    total_signals = bullish_total + bearish_total
    total_hits = bullish_hits + bearish_hits
    hit_rate = (total_hits / total_signals * 100) if total_signals > 0 else 0
    
    # Reverse so most recent is first
    day_by_day.reverse()
    
    return {
        "days_tested": 60,
        "total_signals": total_signals,
        "hit_rate": round(hit_rate, 2),
        "bullish_signals": bullish_total,
        "bearish_signals": bearish_total,
        "history": day_by_day
    }
