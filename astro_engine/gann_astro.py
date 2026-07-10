import math
from typing import Dict, List, Tuple

def square_of_9(price: float) -> Dict:
    """
    Calculate key Square of 9 price levels from a given price.
    Returns resistance and support levels at 45°, 90°, 135°, 180°, 225°, 270°, 315°, 360°.
    """
    root    = math.sqrt(price)
    angles  = [11.25, 22.5, 33.75, 45, 90, 135, 180, 225, 270, 315, 360]
    levels  = {}

    for angle in angles:
        add  = angle / 360.0
        up   = round((root + add) ** 2, 2)
        down = round((root - add) ** 2, 2)
        if down < 0:
            down = 0.0
        levels[f"+{angle}°"] = up
        levels[f"-{angle}°"] = down

    return {
        "base_price":  round(price, 2),
        "sqrt_price":  round(root, 4),
        "levels":      levels,
    }

def price_to_angle(price: float) -> float:
    """
    Convert a price to an angle on the Square of 9.
    Common formula: Angle = (sqrt(price) * 180) - 225
    Returns a value between 0 and 360.
    """
    if price < 0:
        return 0.0
    angle = (math.sqrt(price) * 180) - 225
    return angle % 360

def aspect_intensity(planet_a_long: float, planet_b_long: float) -> Tuple[str, float, int]:
    """
    Calculate the aspect between two planets.
    Returns (Aspect Name, orb, Intensity/Score weight)
    Positive score for bullish/harmonious, Negative for bearish/volatile.
    """
    diff = abs(planet_a_long - planet_b_long)
    if diff > 180:
        diff = 360 - diff
        
    # Standard aspects and their allowed orbs
    aspects = [
        ("Conjunction", 0, 8, -2), # Can be volatile, let's score slightly bearish/volatile
        ("Opposition", 180, 8, -3), # Bearish/Volatile
        ("Square", 90, 8, -4),      # Bearish
        ("Trine", 120, 8, 4),       # Bullish
        ("Sextile", 60, 6, 2),      # Bullish
    ]
    
    for aspect_name, angle, orb, weight in aspects:
        if abs(diff - angle) <= orb:
            # Score weakens as orb increases
            actual_orb = abs(diff - angle)
            intensity = weight * (1 - (actual_orb / orb))
            return aspect_name, actual_orb, round(intensity)
            
    return "None", diff, 0

def get_daily_aspects(planetary_positions: Dict) -> List[Dict]:
    """
    Compare fast planets (Moon, Mercury, Venus, Mars) 
    with slow planets (Jupiter, Saturn, Rahu, Ketu, Uranus, Neptune).
    Returns a list of significant aspects.
    """
    fast = ['Moon', 'Mercury', 'Venus', 'Mars']
    slow = ['Jupiter', 'Saturn', 'Rahu', 'Ketu', 'Uranus', 'Neptune']
    
    aspects_found = []
    
    for f in fast:
        for s in slow:
            if f in planetary_positions and s in planetary_positions:
                long_f = planetary_positions[f]['longitude']
                long_s = planetary_positions[s]['longitude']
                
                asp_name, orb, score = aspect_intensity(long_f, long_s)
                if asp_name != "None":
                    aspects_found.append({
                        "planet1": f,
                        "planet2": s,
                        "aspect": asp_name,
                        "orb": round(orb, 2),
                        "score": score
                    })
                    
    return aspects_found
