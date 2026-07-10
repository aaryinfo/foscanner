import datetime
from typing import Dict, List, Tuple, Any
import logging
import os

try:
    import swisseph as swe
    HAS_SWE = True
    if os.environ.get('VERCEL'):
        logging.warning("Vercel detected. Forcing mock ephemeris since data files are missing.")
        HAS_SWE = False
except ImportError:
    HAS_SWE = False
    
if not HAS_SWE:
    logging.warning("Using mock ephemeris data.")
    class MockSwe:
        SUN = 0; MOON = 1; MERCURY = 2; VENUS = 3; MARS = 4; JUPITER = 5; SATURN = 6
        URANUS = 7; NEPTUNE = 8; PLUTO = 9; TRUE_NODE = 10
        SIDM_LAHIRI = 1
        FLG_SWIEPH = 2
        FLG_SPEED = 256
        FLG_SIDEREAL = 64 * 1024
        
        @staticmethod
        def set_ephe_path(path): pass
        @staticmethod
        def set_sid_mode(mode): pass
        @staticmethod
        def julday(y, m, d, h): return 2451545.0 + d
        @staticmethod
        def calc_ut(jd, body, flags): return ([0.0, 0.0, 0.0, 1.0], 0)
    swe = MockSwe()

# Define the celestial bodies we care about
PLANETS = {
    'Sun': swe.SUN,
    'Moon': swe.MOON,
    'Mercury': swe.MERCURY,
    'Venus': swe.VENUS,
    'Mars': swe.MARS,
    'Jupiter': swe.JUPITER,
    'Saturn': swe.SATURN,
    'Uranus': swe.URANUS,
    'Neptune': swe.NEPTUNE,
    'Pluto': swe.PLUTO,
    'Rahu': swe.TRUE_NODE, # True Node for Rahu
}

def setup_ephemeris(path: str = None):
    """Set the path for the Swiss Ephemeris data files if available."""
    if path:
        swe.set_ephe_path(path)
    # Set standard Vedic Ayanamsa (Lahiri/Chitra Paksha)
    swe.set_sid_mode(swe.SIDM_LAHIRI)

def get_julian_day(date_obj: datetime.datetime) -> float:
    """Convert a datetime object to Julian Day number (ET/UT)."""
    # Assuming the date_obj is in UTC for standard ephemeris calculation
    # swe.julday(year, month, day, hour (decimal))
    hour_decimal = date_obj.hour + date_obj.minute / 60.0 + date_obj.second / 3600.0
    jd = swe.julday(date_obj.year, date_obj.month, date_obj.day, hour_decimal)
    return jd

def get_planetary_positions(date_obj: datetime.datetime, sidereal: bool = True) -> Dict[str, Any]:
    """
    Calculate the positions of all major planets for a given date.
    sidereal=True uses Vedic (Lahiri) Ayanamsa.
    sidereal=False uses Tropical (Western) Zodiac.
    """
    jd = get_julian_day(date_obj)
    
    positions = {}
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    if sidereal:
        flags |= swe.FLG_SIDEREAL

    for name, swe_id in PLANETS.items():
        # calc_ut returns a tuple: (longitude, latitude, distance, speed_long, speed_lat, speed_dist)
        res, ret_flag = swe.calc_ut(jd, swe_id, flags)
        
        longitude = res[0]
        declination = res[1] # Actually latitude in ecliptic coordinates, but useful for 2D. True declination requires equatorial.
        speed = res[3]
        
        is_retrograde = speed < 0
        
        # Determine current sign (0-11)
        sign_idx = int(longitude / 30)
        degree_in_sign = longitude % 30
        
        positions[name] = {
            'longitude': longitude,
            'sign': sign_idx,
            'degree_in_sign': degree_in_sign,
            'speed': speed,
            'is_retrograde': is_retrograde
        }
        
    # Calculate Ketu (always opposite to Rahu in mean/true calculations)
    if 'Rahu' in positions:
        ketu_long = (positions['Rahu']['longitude'] + 180) % 360
        positions['Ketu'] = {
            'longitude': ketu_long,
            'sign': int(ketu_long / 30),
            'degree_in_sign': ketu_long % 30,
            'speed': positions['Rahu']['speed'], # Same speed
            'is_retrograde': positions['Rahu']['is_retrograde']
        }
        
    return positions

def get_moon_nakshatra(longitude: float) -> Tuple[int, float]:
    """
    Calculate the Nakshatra (0-26) and the degree within the Nakshatra.
    Each Nakshatra is 13 degrees 20 minutes (13.333... degrees).
    """
    nakshatra_length = 360 / 27
    nak_idx = int(longitude / nakshatra_length)
    degree_in_nak = longitude % nakshatra_length
    return nak_idx, degree_in_nak

if __name__ == "__main__":
    # Test script
    setup_ephemeris()
    now = datetime.datetime.utcnow()
    pos = get_planetary_positions(now, sidereal=True)
    import json
    print(json.dumps(pos, indent=2))
    
    nak, deg = get_moon_nakshatra(pos['Moon']['longitude'])
    print(f"Moon Nakshatra Index: {nak}, Degree: {deg:.2f}")
