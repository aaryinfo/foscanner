from gann_app import _screener_cache
import time

if "NSE" in _screener_cache and _screener_cache["NSE"]["results"]:
    print(_screener_cache["NSE"]["results"][0].get("date"))
else:
    print("No cache")
