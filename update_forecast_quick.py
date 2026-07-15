import json
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from market_modules.scoring import calculate_daily_astro_score, calculate_sector_bias

print("Updating astro_forecast.json...")
forecast = []
base_date = datetime.utcnow()
for i in range(-90, 15):
    target_date = base_date + timedelta(days=i)
    score_data = calculate_daily_astro_score(target_date)
    sector_bias = calculate_sector_bias(target_date)
    forecast.append({
        "date": score_data['date'],
        "score": score_data['score'],
        "bias": score_data['bias'],
        "nakshatra": score_data['nakshatra'],
        "tithi": score_data['tithi'],
        "eclipse": score_data['eclipse'],
        "numerology_vib": score_data['numerology'],
        "sector_bias": sector_bias,
        "sun_long": score_data.get('sun_long', 30.0),
        "moon_long": score_data.get('moon_long', 150.0)
    })

with open('astro_forecast.json', 'w', encoding='utf-8') as f:
    json.dump(forecast, f, indent=4)
print("Done!")
