import aiohttp
import asyncio
import polyline
import config
import time
from typing import Dict, Optional, Any, Union

class WeatherEngine:
    """
    ASYNC Environmental sensing layer. 
    Performs PARALLEL corridor sampling along route geometry to quantify atmospheric risk factors.
    """
    api_key: str
    base_url: str
    _cache: Dict[str, Dict[str, Any]]

    def __init__(self) -> None:
        self.api_key = config.OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall"
        self._cache: Dict[str, Dict] = {}

    async def _fetch_point(self, session: aiohttp.ClientSession, lat: float, lon: float, label: str) -> Optional[Dict[str, Any]]:
        """
        Helper: Fetches a single coordinate's weather asynchronously.
        """
        params: Dict[str, Union[str, float, int]] = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "imperial",
            "exclude": "minutely,hourly,daily,alerts"
        }
        try:
            async with session.get(self.base_url, params=params) as response:
                # DEBUG: Verifying the live connection in Railway Logs
                print(f"🌦️ WEATHER DEBUG [{label}] - Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    # One Call 3.0 nests current data inside the 'current' key
                    current = data.get('current', {})
                    weather_list = current.get('weather', [])
                    condition = weather_list[0]['main'] if weather_list else "Clear"
                    
                    return {
                        "label": label,
                        "data": {
                            "temp": current.get('temp', 0), # Accessing 'current' block
                            "condition": condition,
                            "description": weather_list[0]['description'] if weather_list else "no data",
                            "location_name": label 
                        }
                    }
                else:
                    # Logs exact reason if the call fails (e.g. 401 Unauthorized)
                    error_text = await response.text()
                    print(f"❌ WEATHER API ERROR: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"⚠️ Weather API Error at {label}: {e}")
            return None

    async def get_route_weather(self, encoded_polyline: str, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        """
        Samples atmospheric conditions at Origin, Midpoint, and Destination simultaneously.
        """
        try:
            if encoded_polyline in self._cache:
                return self._cache[encoded_polyline]

            coordinates = polyline.decode(encoded_polyline)
            if not coordinates:
                return None

            points_map = {
                "Start": 0,
                "Midpoint": len(coordinates) // 2,
                "Destination": len(coordinates) - 1
            }

            tasks = []
            for label, index in points_map.items():
                lat, lon = coordinates[index]
                tasks.append(self._fetch_point(session, lat, lon, label))

            results = await asyncio.gather(*tasks) 

            report: Dict[str, Any] = {}
            for res in results:
                if res:
                    report[res['label']] = res['data']

            if report:
                self._cache[encoded_polyline] = report
                return report
            return None
            
        except Exception as e:
            print(f"Weather Engine System Error: {e}")
            return None

# Local Unit Test Block remains unchanged...

# Local Unit Test Block.
if __name__ == "__main__":
    async def run_test():
        test_engine = WeatherEngine()
        # Sample polyline (roughly maps to a short route segment).
        sample_polyline = r"uzpwFvps|U" 

        print("Starting Async Weather Check...")
        start_time = time.time()
        
        # We must create the session here to pass it in.
        async with aiohttp.ClientSession() as session:
            # Test 1: Functional Integration.
            report_1 = await test_engine.get_route_weather(sample_polyline, session)
            
            # Assertions: Validating that the engine didn't fail.
            assert report_1 is not None, "CRITICAL: Engine returned None on first pass."
            assert "Start" in report_1, "DATA ERROR: Missing 'Start' key in report."
            
            duration = time.time() - start_time
            print(f"✅ Pass 1: Async fetch successful ({duration:.4f}s).")

            # Test 2: Memoization (Cache) Logic.
            start_cache = time.time()
            report_2 = await test_engine.get_route_weather(sample_polyline, session)
            cache_time = time.time() - start_cache
            
            assert report_1 == report_2, "CACHE ERROR: Cached data does not match original."
            assert cache_time < 0.001, f"PERFORMANCE ERROR: Cache too slow ({cache_time}s)."
            print(f"✅ Pass 2: Memoization verified. Cache time: {cache_time:.6f}s")

    # Execute the async loop.
    asyncio.run(run_test())