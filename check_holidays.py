import holidays

in_holidays = holidays.India(years=2026)
for date, name in sorted(in_holidays.items()):
    print(f"{date}: {name}")
