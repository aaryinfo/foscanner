with open('gann_app.py', 'r', encoding='utf-8') as f:
    code = f.read()

target = """                    # Find the best matching confluence for the target trading dates
                    matching_confs = [c for c in res["confluence"] 
                                     if c["date"] in target_dates and c["count"] >= 3]
                    
                    if matching_confs:
                        # Use the strongest confluence for metadata
                        best_conf = max(matching_confs, key=lambda c: c["count"])
                        
                        results.append({"""

replace = """                    # Find the best matching confluence for the target trading dates
                    matching_confs = [c for c in res["confluence"] 
                                     if c["date"] in target_dates and c["count"] >= 3]
                    
                    if matching_confs:
                        best_conf = max(matching_confs, key=lambda c: c["count"])
                        has_confluence = True
                    else:
                        best_conf = {"date_display": next_trading_day.strftime("%Y-%m-%d"), "days_away": 0, "strength": "WEAK", "count": 0, "cycles": []}
                        has_confluence = False
                        
                    if True:
                        results.append({
                            "confluence_match": has_confluence,"""

if target in code:
    code = code.replace(target, replace)
    with open('gann_app.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print("Patched gann_app.py successfully")
else:
    print("Target not found in gann_app.py")
