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
    sample_size = min(len(df), 252) # up to 1 year
    sample_df = df.tail(sample_size).dropna()
    
    bullish_hits = 0
    bullish_total = 0
    bearish_hits = 0
    bearish_total = 0
    
    for _, row in sample_df.iterrows():
        date_obj = row['Date']
        if isinstance(date_obj, str):
            date_obj = datetime.datetime.strptime(date_obj, "%Y-%m-%d")
        elif isinstance(date_obj, pd.Timestamp):
            date_obj = date_obj.to_pydatetime()
            
        score_report = calculate_daily_astro_score(date_obj)
        score = score_report['score']
        next_ret = row['Next_Day_Return']
        
        if score >= 30: # Bullish signal
            bullish_total += 1
            if next_ret > 0:
                bullish_hits += 1
        elif score <= -30: # Bearish signal
            bearish_total += 1
            if next_ret < 0:
                bearish_hits += 1
                
    total_signals = bullish_total + bearish_total
    total_hits = bullish_hits + bearish_hits
    hit_rate = (total_hits / total_signals * 100) if total_signals > 0 else 0
    
    return {
        "days_tested": sample_size,
        "total_signals": total_signals,
        "hit_rate": round(hit_rate, 2),
        "bullish_signals": bullish_total,
        "bearish_signals": bearish_total
    }
