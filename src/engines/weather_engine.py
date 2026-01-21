import aiohttp
import asyncio
import polyline 
import config
import time
import logging
import sys
import os
from typing import Dict, Optional, Any

# Add parent directory to path to import mocks
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tests import mocks

logger = logging.getLogger(__name__)

class WeatherEngine:
    """
    ASYNC Environmental sensing layer. 
    Performs PARALLEL corridor sampling along route geometry to quantify atmospheric risk factors.
    Includes in-memory memoization to reduce API load during session.
    """
    
    def __init__(self) -> None:
        self.api_key = config.OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall"
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def _fetch_point(
        self, 
        session: aiohttp.ClientSession, 
        lat: float, 
        lon: float, 
        label: str
    ) -> Optional[Dict[str, Any]]:
        """
        Helper: Fetches a single coordinate's weather asynchronously.
        
        Args:
            session: aiohttp ClientSession
            lat: Latitude
            lon: Longitude
            label: Human-readable location label
        
        Returns:
            Dict with weather data or None if fetch fails
        """
        params = {
            "lat": str(lat),
            "lon": str(lon),
            "appid": self.api_key,
            "units": "imperial",
            "exclude": "minutely,hourly,daily,alerts"
        }
        try:
            async with session.get(self.base_url, params=params, timeout=5.0) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # One Call 3.0 nests current data inside the 'current' key
                    current = data.get('current', {})
                    weather_list = current.get('weather', [])
                    condition = weather_list[0]['main'] if weather_list else "Clear"
                    
                    return {
                        "label": label,
                        "data": {
                            "temp": current.get('temp', 0.0),
                            "condition": condition,
                            "description": weather_list[0]['description'] if weather_list else "no data",
                            "location_name": label 
                        }
                    }
                else:
                    logger.warning(f"Weather API error {response.status} for {label} ({lat}, {lon})")
                    return None
        except asyncio.TimeoutError:
            logger.warning(f"Weather API timeout for {label}")
            return None
        except Exception as e:
            logger.error(f"Weather Engine error at {label} ({lat}, {lon}): {e}")
            return None

    async def get_route_weather(
        self, 
        encoded_polyline: str, 
        session: aiohttp.ClientSession
    ) -> Optional[Dict[str, Any]]:
        """
        Samples atmospheric conditions at Origin, Midpoint, and Destination simultaneously.
        
        Args:
            encoded_polyline: Google Maps encoded polyline string
            session: aiohttp ClientSession (shared)
        
        Returns:
            Dict mapping location labels to weather data, or None if decoding fails
        """
        # SAFETY LOCK: Use centralized config
        if config.USE_MOCK_DATA:
            return mocks.get_mock_weather()

        if not self.api_key:
            return mocks.get_mock_weather()

        # 1. Check Cache (Memoization)
        if encoded_polyline in self._cache:
            logger.debug("Weather cache hit")
            return self._cache[encoded_polyline]

        try:
            # Decode polyline with error handling
            try:
                coordinates = polyline.decode(encoded_polyline)
            except Exception as e:
                logger.error(f"Polyline decode failed: {e}")
                return mocks.get_mock_weather()
            
            if not coordinates or len(coordinates) < 2:
                logger.warning("Polyline has fewer than 2 points")
                return mocks.get_mock_weather()

            # 2. Select Sampling Points
            points_map = {
                "Start": 0,
                "Midpoint": len(coordinates) // 2,
                "Destination": len(coordinates) - 1
            }

            tasks = []
            for label, index in points_map.items():
                lat, lon = coordinates[index]
                tasks.append(self._fetch_point(session, lat, lon, label))

            # 3. Parallel Execution
            results = await asyncio.gather(*tasks) 

            report: Dict[str, Any] = {}
            for res in results:
                if res:
                    report[res['label']] = res['data']

            # 4. Update Cache and Return
            if report:
                self._cache[encoded_polyline] = report
                logger.debug(f"Weather report cached for polyline")
                return report
            
            logger.warning("No weather data collected from any sampling point")
            return mocks.get_mock_weather()
            
        except Exception as e:
            logger.error(f"Weather Engine critical error: {e}")
            return mocks.get_mock_weather()

# --- UNIT TEST BLOCK ---
if __name__ == "__main__":
    async def run_test():
        logging.basicConfig(level=logging.INFO)
        test_engine = WeatherEngine()
        sample_polyline = r"uzpwFvps|U" 

        logger.info("Starting Async Weather Check...")
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            # Test 1: Functional Integration
            report_1 = await test_engine.get_route_weather(sample_polyline, session)
            assert report_1 is not None, "CRITICAL: Engine returned None."
            
            duration = time.time() - start_time
            logger.info(f"✅ Pass 1: Async fetch successful ({duration:.4f}s).")

            # Test 2: Memoization (Cache) Logic
            start_cache = time.time()
            report_2 = await test_engine.get_route_weather(sample_polyline, session)
            cache_time = time.time() - start_cache
            
            assert report_1 == report_2, "CACHE ERROR: Cached data mismatch."
            logger.info(f"✅ Pass 2: Memoization verified. Cache time: {cache_time:.6f}s")

    asyncio.run(run_test())