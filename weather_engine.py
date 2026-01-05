import requests
import polyline
import config
from typing import Dict, Optional, Any, Union

class WeatherEngine:
    """
    Environmental sensing layer. 
    Performs corridor sampling along route geometry to quantify atmospheric risk factors.
    """
    api_key: str
    base_url: str
    _cache: Dict[str, Dict[str, Any]]

    def __init__(self) -> None:
        self.api_key = config.OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self._cache: Dict[str, Dict] = {}

    def get_route_weather(self, encoded_polyline: str) -> Optional[Dict[str, Any]]:
        """
        Samples atmospheric conditions at the Origin, Midpoint, and Destination.
        
        Args:
            encoded_polyline: Compressed Google Maps route geometry.
        Returns:
            Corridor weather report or None if spatial sampling fails.
        """
        try:
            # Memoization lookup to prevent redundant network I/O.
            if encoded_polyline in self._cache:
                return self._cache[encoded_polyline]
            coordinates = polyline.decode(encoded_polyline)

            if not coordinates:
                return None
            
            # Map sampling waypoints to indices.
            indices: Dict[str, int] = {
                "Start": 0,
                "Midpoint": len(coordinates) // 2,
                "Destination": len(coordinates) - 1
            }

            report: Dict[str, Any] = {}

            # Iterate through samples to build a comprehensive risk profile.
            for label, index in indices.items():
                lat, lon = coordinates[index]
                params: Dict[str, Union[str, float, int]] = {
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "imperial" 
                }

                response = requests.get(self.base_url, params=params)                
                if response.status_code == 200:
                    data = response.json()
                    # Safe extraction of weather metadata.
                    weather_list = data.get('weather', [])
                    condition = weather_list[0]['main'] if weather_list else "Clear"

                    report[label] = {
                        "temp": data['main']['temp'],
                        "condition": condition,
                        "description": weather_list[0]['description'] if weather_list else "no data",
                        "location_name": data.get('name', label)
                    }
                else:
                    print(f"Weather API Error at {label}: {response.status_code}")

            if report:
                self._cache[encoded_polyline] = report # Commit to cache.
                return report
            return None
        
        except Exception as e:
            print(f"Weather Engine System Error: {e}")
            return None
        
# Local Unit Test Block.
if __name__ == "__main__":
    import time
    test_engine = WeatherEngine()
    sample_polyline = r"uzpwFvps|U" 
    
    print("Starting WeatherEngine Check...")

    # Test 1: Functional Integration.
    report_1 = test_engine.get_route_weather(sample_polyline)
    
    # Assertions: Validating that the engine didn't fail.
    assert report_1 is not None, "CRITICAL: Engine returned None on first pass."
    assert "Start" in report_1, "DATA ERROR: Missing 'Start' key in report."
    print("✅ Pass 1: Initial data fetch successful.")

    # Test 2: Memoization (Cache) Logic.
    # We record the time it takes for a second call.
    start_time = time.time()
    report_2 = test_engine.get_route_weather(sample_polyline)
    end_time = time.time()
    
    # Assertions: Proving the cache worked.
    assert report_1 == report_2, "CACHE ERROR: Cached data does not match original."
    
    # If it hit the cache, the time should be near-zero (e.g., < 0.001 seconds) compared to a real network call which takes ~0.5 - 1.0 seconds.
    execution_time = end_time - start_time
    assert execution_time < 0.01, f"PERFORMANCE ERROR: Cache too slow ({execution_time}s)."
    
    print(f"✅ Pass 2: Memoization verified. Cache return time: {execution_time:.6f}s")
    print("\nDiagnostic Complete")