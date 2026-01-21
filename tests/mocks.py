import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Union

def get_mock_flight_data(flight_number: str = "DL100") -> Dict[str, Union[str, int]]:
    """
    Generates a synthetic flight schedule for testing/cost-saving.
    Simulates a flight departing in ~3 hours to ensure relevant risk calculations.
    
    Returns:
        dict: Standardized AeroDataBox API response structure.
    """
    # Always use timezone-aware UTC to prevent offset errors in the solver
    now = datetime.now(timezone.utc)
    
    # Dynamic Schedule: Departure set to T+3h to allow meaningful risk analysis
    dep_dt = now + timedelta(hours=3, minutes=random.randint(0, 30))
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

def get_mock_traffic() -> Dict[str, Union[float, str]]:
    """
    Simulates Google Maps Directions API response.
    Returns a Triangular Distribution (Min, Mode, Max) for Monte Carlo sampling.
    """
    base = random.randint(45, 65)
    return {
        "min": float(base - 10),  # Optimistic (No traffic)
        "mode": float(base),      # Realistic (Current traffic)
        "max": float(base + 15),  # Pessimistic (Accident/Gridlock)
        "polyline": "uzpwFvps|U"  # Mock polyline for map rendering
    }

def get_mock_weather() -> Dict[str, Dict[str, Union[float, str]]]:
    """
    Simulates OpenWeather OneCall 3.0 API response.
    Returns nested dictionaries for checkpoints.
    """
    def _get_point(name: str) -> Dict[str, Union[float, str]]:
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

def get_mock_tsa_wait(airport_code: str = "JFK") -> float:
    """
    Simulates the TSA Wait Times API.
    Used to test the 'Hybrid Architecture' logic without calling the real API.
    
    Args:
        airport_code: The IATA code (e.g. 'JFK', 'LGA').
        
    Returns:
        float: Simulated wait time in minutes (e.g., 24.5).
    """
    # Base randomness
    wait = random.uniform(12.0, 35.0)
    
    # Simulate busier airports
    if any(code in airport_code.upper() for code in ["JFK", "LGA", "LAX", "ORD"]):
        wait += 10.0
        
    return round(wait, 1)