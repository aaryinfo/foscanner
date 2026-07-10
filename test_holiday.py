from datetime import date
from gann_engine import is_non_trading_day

print("June 25:", is_non_trading_day(date(2026, 6, 25), "NSE"))
print("June 26:", is_non_trading_day(date(2026, 6, 26), "NSE"))
print("June 27:", is_non_trading_day(date(2026, 6, 27), "NSE"))
print("June 28:", is_non_trading_day(date(2026, 6, 28), "NSE"))
print("June 29:", is_non_trading_day(date(2026, 6, 29), "NSE"))
