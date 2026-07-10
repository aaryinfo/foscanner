import pandas as pd
import datetime
from .scoring import calculate_daily_astro_score

def run_backtest(df: pd.DataFrame) -> dict:
    """
    Run backtest on historical dataframe to see correlation of 
    Astro Bias Score with Next Day Return.
    DataFrame must have 'Date' and 'Close' columns.
    """
    if df.empty or 'Close' not in df.columns:
        return {"error": "Invalid dataframe"}
        
    df['Daily_Return'] = df['Close'].pct_change() * 100
    df['Next_Day_Return'] = df['Daily_Return'].shift(-1)
    
    results = []
    
    # Just run on a sample to not take too long in a demo
    # In production, this would be pre-calculated and cached in the DB
    sample_size = min(len(df), 60) # up to 60 days (approx 3 months)
    sample_df = df.tail(sample_size).dropna()
    
    bullish_hits = 0
    bullish_total = 0
    bearish_hits = 0
    bearish_total = 0
    
    day_by_day = []
    
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
        
    for _, row in sample_df.iterrows():
        date_obj = row['Date']
        if isinstance(date_obj, str):
            date_obj = datetime.datetime.strptime(date_obj, "%Y-%m-%d")
        elif isinstance(date_obj, pd.Timestamp):
            date_obj = date_obj.to_pydatetime()
            
        date_str = date_obj.strftime("%Y-%m-%d")
        
        # Look up precalculated score first, fallback to live calculation
        if date_str in precalculated_scores:
            score_report = precalculated_scores[date_str]
            score = score_report['score']
        else:
            score_report = calculate_daily_astro_score(date_obj)
            score = score_report['score']
            
        next_ret = row['Next_Day_Return']
        
        is_hit = None
        
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
            "date": date_obj.strftime("%Y-%m-%d"),
            "score": score,
            "bias": score_report['bias'],
            "actual_return": round(next_ret, 2) if pd.notnull(next_ret) else 0.0,
            "is_hit": is_hit
        })
                
    total_signals = bullish_total + bearish_total
    total_hits = bullish_hits + bearish_hits
    hit_rate = (total_hits / total_signals * 100) if total_signals > 0 else 0
    
    # Reverse so most recent is first
    day_by_day.reverse()
    
    return {
        "days_tested": sample_size,
        "total_signals": total_signals,
        "hit_rate": round(hit_rate, 2),
        "bullish_signals": bullish_total,
        "bearish_signals": bearish_total,
        "history": day_by_day
    }
