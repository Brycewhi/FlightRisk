import random
from datetime import datetime, timedelta, timezone

# Mock flight data generator for testing purposes.
def get_mock_flight_data(flight_number="DL100"):
    # Use timezone-aware UTC.
    now = datetime.now(timezone.utc)
    
    # Departure: 3 hours from now.
    dep_dt = now + timedelta(hours=3, minutes=random.randint(0, 30))
    # Arrival: 7 hours after departure.
    arr_dt = dep_dt + timedelta(hours=7, minutes=random.randint(0, 45))
    
    return {
        "flight_num": flight_number,
        "dep_ts": int(dep_dt.timestamp()),
        "arr_ts": int(arr_dt.timestamp()),
        "origin_airport": "JFK International",
        "dest_airport": "London Heathrow",
        "duration_mins": 420 + random.randint(-20, 20),
        "status": "Scheduled"
    }

# Mock traffic data generator for testing purposes.
def get_mock_traffic():
    base = random.randint(45, 65)
    return {
        "min": float(base - 10),
        "mode": float(base),
        "max": float(base + 15),
        "polyline": "uzpwFvps|U" 
    }

# Mock weather data for testing purposes.
def get_mock_weather():
    def _get_point(name):
        return {
            "temp": round(random.uniform(50, 70), 1),
            "condition": "Clouds",
            "description": "overcast clouds",
            "location_name": name
        }
    
    return {
        "Start": _get_point("Start"),
        "Midpoint": _get_point("Midpoint"),
        "Destination": _get_point("Destination")
    }