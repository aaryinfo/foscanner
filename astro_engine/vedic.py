from typing import Dict, Tuple

# 27 Nakshatras and their historical market volatility tags
NAKSHATRAS = [
    ("Ashwini", "Neutral"),
    ("Bharani", "Volatile"), # Ruled by Venus, fierce
    ("Krittika", "Volatile"), # Ruled by Sun, sharp
    ("Rohini", "Stable"),
    ("Mrigashira", "Neutral"),
    ("Ardra", "Highly Volatile"), # Ruled by Rahu, destructive
    ("Punarvasu", "Stable"),
    ("Pushya", "Stable"),
    ("Ashlesha", "Volatile"), # Ruled by Mercury, tricky
    ("Magha", "Volatile"), # Ruled by Ketu, sudden changes
    ("Purva Phalguni", "Neutral"),
    ("Uttara Phalguni", "Stable"),
    ("Hasta", "Neutral"),
    ("Chitra", "Volatile"), # Ruled by Mars
    ("Swati", "Volatile"), # Ruled by Rahu
    ("Vishakha", "Neutral"),
    ("Anuradha", "Stable"),
    ("Jyeshtha", "Volatile"), # Ruled by Mercury, sharp
    ("Mula", "Highly Volatile"), # Ruled by Ketu, root/destruction
    ("Purva Ashadha", "Neutral"),
    ("Uttara Ashadha", "Stable"),
    ("Shravana", "Stable"),
    ("Dhanishta", "Neutral"),
    ("Shatabhisha", "Volatile"), # Ruled by Rahu
    ("Purva Bhadrapada", "Volatile"), # Ruled by Jupiter but fierce
    ("Uttara Bhadrapada", "Stable"),
    ("Revati", "Stable"),
]

def get_nakshatra_info(nak_idx: int) -> Dict[str, str]:
    if 0 <= nak_idx < 27:
        name, tag = NAKSHATRAS[nak_idx]
        return {"name": name, "tag": tag}
    return {"name": "Unknown", "tag": "Neutral"}

def calculate_tithi(sun_long: float, moon_long: float) -> Tuple[int, str]:
    """
    Tithi is the lunar day. 1 Tithi = 12 degrees difference between Moon and Sun.
    Returns (Tithi Number 1-30, Name of Tithi).
    15 is Purnima (Full Moon), 30 is Amavasya (New Moon).
    """
    diff = moon_long - sun_long
    if diff < 0:
        diff += 360
        
    tithi_idx = int(diff / 12) + 1
    
    # Amavasya (New Moon) proximity can be volatile
    if tithi_idx == 30:
        name = "Amavasya (New Moon) - Volatile"
    elif tithi_idx == 15:
        name = "Purnima (Full Moon) - Volatile"
    elif tithi_idx in [4, 9, 14, 19, 24, 29]: # Rikta Tithis (Empty/Challenging)
        name = f"Tithi {tithi_idx} (Rikta/Challenging)"
    else:
        name = f"Tithi {tithi_idx}"
        
    return tithi_idx, name

def check_combustion(planet_long: float, sun_long: float, orb: float = 8.0) -> bool:
    """
    Check if a planet is combust (too close to the Sun).
    Combust planets lose their strength.
    """
    diff = abs(planet_long - sun_long)
    if diff > 180:
        diff = 360 - diff
    return diff <= orb

def check_eclipse_proximity(sun_long: float, moon_long: float, rahu_long: float, ketu_long: float) -> str:
    """
    Check if the current date is close to an eclipse.
    Solar Eclipse: New Moon (Sun conj Moon) + close to Rahu or Ketu.
    Lunar Eclipse: Full Moon (Sun opp Moon) + close to Rahu or Ketu.
    Returns a string indicating eclipse status.
    """
    diff = moon_long - sun_long
    if diff < 0:
        diff += 360
        
    is_new_moon = (diff < 15 or diff > 345)
    is_full_moon = (165 < diff < 195)
    
    # Distance of Sun/Moon from nodes
    sun_rahu = min(abs(sun_long - rahu_long), 360 - abs(sun_long - rahu_long))
    sun_ketu = min(abs(sun_long - ketu_long), 360 - abs(sun_long - ketu_long))
    
    node_dist = min(sun_rahu, sun_ketu)
    
    # Within 18 degrees of a node during New/Full moon is an eclipse window
    if node_dist <= 18:
        if is_new_moon:
            return "Solar Eclipse Window"
        elif is_full_moon:
            return "Lunar Eclipse Window"
            
    return "No Eclipse"
