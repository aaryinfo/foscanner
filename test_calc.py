from datetime import datetime, timedelta
import os
import sys
sys.path.append(os.getcwd())
from gann_engine import is_non_trading_day

trial_start_date = '2026-06-26T04:37:29.729360'
trial_start = datetime.fromisoformat(trial_start_date)
print("trial_start:", trial_start)

trading_days_added = 0
trial_end = trial_start
while trading_days_added < 15:
    trial_end += timedelta(days=1)
    if not is_non_trading_day(trial_end, "NSE"):
        trading_days_added += 1

print("trial_end:", trial_end)

now = datetime.utcnow()
print("now:", now)

remaining_days = 0
curr = now
while curr < trial_end:
    curr += timedelta(days=1)
    if not is_non_trading_day(curr, "NSE"):
        remaining_days += 1
        
print("remaining_days:", remaining_days)
