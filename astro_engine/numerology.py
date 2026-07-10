from datetime import datetime

def reduce_to_single_digit(n: int) -> int:
    """
    Reduce a number to a single digit (1-9) as per numerology.
    Exception: master numbers 11, 22, 33 are sometimes kept, but for standard
    date vibration we usually reduce all the way to 1-9.
    """
    if n == 0:
        return 0
    res = n % 9
    return res if res != 0 else 9

def get_date_vibration(date_obj: datetime) -> int:
    """
    Calculate the daily vibration number.
    Formula: Day + Month + Year reduced to single digit.
    Example: 15-Aug-1947 -> 1+5 + 8 + 1+9+4+7 = 6 + 8 + 21 = 35 -> 8
    """
    day_sum = sum(int(d) for d in str(date_obj.day))
    month_sum = sum(int(d) for d in str(date_obj.month))
    year_sum = sum(int(d) for d in str(date_obj.year))
    
    total = day_sum + month_sum + year_sum
    return reduce_to_single_digit(total)

def get_instrument_vibration(listing_date_str: str) -> int:
    """
    Calculate the base numerology vibration for an instrument based on its listing date.
    listing_date_str format: "YYYY-MM-DD"
    """
    try:
        dt = datetime.strptime(listing_date_str, "%Y-%m-%d")
        return get_date_vibration(dt)
    except ValueError:
        return 0
