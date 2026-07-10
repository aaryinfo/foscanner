import datetime
import math
from typing import Dict, List, Any

# Ensure absolute imports since this will be run as a module or from app.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from astro_engine.ephemeris import get_planetary_positions, get_moon_nakshatra
from astro_engine.gann_astro import get_daily_aspects, price_to_angle
from astro_engine.vedic import get_nakshatra_info, calculate_tithi, check_combustion, check_eclipse_proximity
from astro_engine.numerology import get_date_vibration

def calculate_daily_astro_score(date_obj: datetime.datetime) -> Dict[str, Any]:
    """
    Computes a composite Astro Bias Score (-100 to +100) for a given date.
    """
    pos = get_planetary_positions(date_obj, sidereal=True)
    
    # 1. Vedic Layer
    moon_long = pos['Moon']['longitude']
    sun_long = pos['Sun']['longitude']
    rahu_long = pos.get('Rahu', {}).get('longitude', 0)
    ketu_long = pos.get('Ketu', {}).get('longitude', 0)
    
    nak_idx, _ = get_moon_nakshatra(moon_long)
    nak_info = get_nakshatra_info(nak_idx)
    tithi_idx, tithi_name = calculate_tithi(sun_long, moon_long)
    eclipse_status = check_eclipse_proximity(sun_long, moon_long, rahu_long, ketu_long)
    
    # 2. Aspect Intensity
    aspects = get_daily_aspects(pos)
    aspect_score = sum(asp['score'] for asp in aspects)
    
    # 3. Numerology
    date_vib = get_date_vibration(date_obj)
    
    # 4. Retrograde Penalty (Mercury/Venus/Mars retrogrades often cause choppiness)
    retrogrades = []
    retro_penalty = 0
    for p in ['Mercury', 'Venus', 'Mars']:
        if p in pos and pos[p]['is_retrograde']:
            retrogrades.append(p)
            retro_penalty -= 10
            
    # Composite Score Calculation
    base_score = 0
    
    if nak_info['tag'] == 'Volatile':
        base_score -= 15
    elif nak_info['tag'] == 'Highly Volatile':
        base_score -= 30
    elif nak_info['tag'] == 'Stable':
        base_score += 10
        
    if "Volatile" in tithi_name or "Challenging" in tithi_name:
        base_score -= 15
        
    if "Eclipse" in eclipse_status:
        base_score -= 50 # Eclipses dominate and create high volatility/reversals
        
    total_score = base_score + aspect_score + retro_penalty
    
    # Clamp to -100, +100
    total_score = max(-100, min(100, total_score))
    
    bias = "Neutral"
    if total_score >= 30: bias = "Bullish"
    elif total_score <= -30: bias = "Bearish/Volatile"
    
    if eclipse_status != "No Eclipse":
        bias = "Highly Volatile (Eclipse Window)"
        
    return {
        "date": date_obj.strftime("%Y-%m-%d"),
        "score": total_score,
        "bias": bias,
        "nakshatra": nak_info['name'],
        "nakshatra_tag": nak_info['tag'],
        "tithi": tithi_name,
        "eclipse": eclipse_status,
        "aspects": aspects,
        "retrogrades": retrogrades,
        "numerology": date_vib
    }

def calculate_stock_astro_score(date_obj: datetime.datetime, ticker: str, price: float) -> Dict[str, Any]:
    """
    Computes a stock-specific Astro Bias Score by combining the global macro score
    with the Gann Square of 9 alignment of the stock's price to the Sun's longitude.
    """
    macro_report = calculate_daily_astro_score(date_obj)
    base_score = macro_report['score']
    
    if not price or price <= 0:
        return macro_report # Fallback to macro if no price
        
    import math
    
    price_angle = price_to_angle(price)
    
    # We need planetary positions for this date
    pos = get_planetary_positions(date_obj, sidereal=True)
    sun_long = pos['Sun']['longitude']
    moon_long = pos['Moon']['longitude']
    
    # Continuous scoring function based on Gann angles
    # Gann considers 0, 90, 180, 270 as Hard/Volatile aspects.
    # A cosine wave with frequency 4 peaks at these angles.
    # We multiply by -30 so that hard aspects give -30 (Bearish/Volatile).
    sun_modifier = -math.cos(math.radians((sun_long - price_angle) * 4)) * 25
    
    # Moon moves faster, so it gives short term nuance
    moon_modifier = -math.cos(math.radians((moon_long - price_angle) * 4)) * 15
    
    price_modifier = int(sun_modifier + moon_modifier)
    
    total_score = base_score + price_modifier
    total_score = max(-100, min(100, total_score))
    
    bias = "Neutral"
    if total_score >= 30: bias = "Bullish"
    elif total_score <= -30: bias = "Bearish/Volatile"
    
    # Copy macro report and update with stock specific data
    stock_report = macro_report.copy()
    stock_report['score'] = total_score
    stock_report['bias'] = bias
    stock_report['price_modifier'] = price_modifier
    
    return stock_report


def get_top_5_turn_date_stocks(date_obj: datetime.datetime, tickers: List[str], current_prices: Dict[str, float]) -> List[Dict]:
    """
    Calculate the "Top 5 Stocks with Turn Dates" for a given day.
    Checks if Sun's longitude matches the Square of 9 angles of the stock's price.
    """
    pos = get_planetary_positions(date_obj, sidereal=True)
    sun_long = pos['Sun']['longitude']
    
    results = []
    
    for ticker in tickers:
        price = current_prices.get(ticker)
        if not price or price <= 0:
            continue
            
        # Price to angle
        price_angle = (math.sqrt(price) * 180) - 225
        price_angle = price_angle % 360
        
        # Check alignment with Sun
        diff = abs(sun_long - price_angle)
        if diff > 180:
            diff = 360 - diff
            
        # Standard Gann Square of 9 aspects (0, 45, 90, 120, 135, 180)
        strong_angles = [0, 45, 90, 120, 135, 180]
        min_orb = 360
        aligned_angle = None
        
        for ang in strong_angles:
            orb = abs(diff - ang)
            if orb < min_orb:
                min_orb = orb
                aligned_angle = ang
                
        # If orb is very tight (e.g., < 2 degrees), flag it as a turn date
        if min_orb <= 2.0:
            results.append({
                "ticker": ticker,
                "price": price,
                "orb": min_orb,
                "alignment": f"Sun aligned with Square of 9 price level (Aspect: {aligned_angle}°)"
            })
            
    # Sort by tightest orb
    results = sorted(results, key=lambda x: x['orb'])
    
    return results[:5]

def get_dignity(planet: str, sign_idx: int) -> str:
    """Returns basic planetary dignity (Exalted, Own Sign, Debilitated, Neutral)"""
    exaltations = {
        'Sun': 0, 'Moon': 1, 'Mars': 9, 'Mercury': 5, 
        'Jupiter': 3, 'Venus': 11, 'Saturn': 6, 'Rahu': 1, 'Ketu': 7
    }
    debilitations = {
        'Sun': 6, 'Moon': 7, 'Mars': 3, 'Mercury': 11, 
        'Jupiter': 9, 'Venus': 5, 'Saturn': 0, 'Rahu': 7, 'Ketu': 1
    }
    own_signs = {
        'Sun': [4], 'Moon': [3], 'Mars': [0, 7], 'Mercury': [2, 5],
        'Jupiter': [8, 11], 'Venus': [1, 6], 'Saturn': [9, 10]
    }
    
    if exaltations.get(planet) == sign_idx: return "Exalted"
    if debilitations.get(planet) == sign_idx: return "Debilitated"
    if sign_idx in own_signs.get(planet, []): return "Own Sign"
    return "Neutral"

def calculate_sector_bias(date_obj: datetime.datetime) -> List[Dict]:
    """
    Determines astrological bias for market sectors based on planetary dignity.
    """
    pos = get_planetary_positions(date_obj, sidereal=True)
    
    sectors = [
        {"name": "Banking & Finance", "planet": "Jupiter", "emoji": "🏦"},
        {"name": "IT & Tech", "planet": "Mercury", "emoji": "💻"},
        {"name": "Auto & FMCG", "planet": "Venus", "emoji": "🚗"},
        {"name": "Metals & Real Estate", "planet": "Mars", "emoji": "🏗️"},
        {"name": "Energy & Pharma", "planet": "Sun", "emoji": "⚡"}
    ]
    
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    
    results = []
    
    for sec in sectors:
        planet = sec['planet']
        if planet not in pos:
            continue
            
        p_data = pos[planet]
        sign_idx = p_data['sign']
        dignity = get_dignity(planet, sign_idx)
        is_retro = p_data.get('is_retrograde', False)
        
        score = 0
        if dignity == 'Exalted' or dignity == 'Own Sign':
            score = 2
        elif dignity == 'Debilitated':
            score = -2
            
        if is_retro and planet not in ['Sun', 'Moon']:
            score -= 1  # Retrograde creates uncertainty/weakness
            
        bias = "Neutral"
        if score >= 1:
            bias = "Bullish"
        elif score <= -1:
            bias = "Bearish"
            
        sign_name = signs[sign_idx]
        reason = f"{planet} is in {sign_name}"
        if dignity != "Neutral":
            reason += f" ({dignity})"
        if is_retro:
            reason += " [Retrograde]"
            
        results.append({
            "sector": sec['name'],
            "emoji": sec['emoji'],
            "planet": planet,
            "bias": bias,
            "reason": reason
        })
        
    return results

if __name__ == "__main__":
    today = datetime.datetime.utcnow()
    report = calculate_daily_astro_score(today)
    import json
    print(json.dumps(report, indent=2))
