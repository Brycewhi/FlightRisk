import aiohttp
import asyncio
import config
from typing import Optional, Dict, Union, Any
import logging
import sys
import os

# Add parent directory to path to import mocks
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tests import mocks

logger = logging.getLogger(__name__)

class TrafficEngine:
    """
    Sensing layer for geospatial data acquisition. 
    Interfaces with Google Maps Directions API via AsyncIO to provide 
    duration variance required for stochastic risk modeling.
    """
    
    def __init__(self) -> None:
        self.api_key = config.GOOGLE_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api/directions/json"

    async def _fetch_single_route(
        self, 
        session: aiohttp.ClientSession,
        origin: str, 
        destination: str, 
        model: str, 
        departure_time: Union[int, float, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Internal Helper: Asynchronously retrieves a single trip duration estimate.
        
        Args:
            session: aiohttp ClientSession
            origin: Starting location
            destination: Ending location
            model: Google traffic model ('optimistic', 'best_guess', 'pessimistic')
            departure_time: Unix timestamp or 'now'
        
        Returns:
            Dict with route data or None if fetch fails
        """
        # Google API requires integer for timestamps
        if isinstance(departure_time, float):
            departure_time = int(departure_time)
            
        params = {
            "origin": origin,
            "destination": destination,
            "departure_time": departure_time, 
            "traffic_model": model, 
            "key": self.api_key,
            "mode": "driving"
        }

        try:
            async with session.get(self.base_url, params=params, timeout=5.0) as response:
                if response.status != 200:
                    logger.warning(f"Traffic API error ({model}): HTTP {response.status}")
                    return None
                    
                data = await response.json()

                if data.get('status') != 'OK':
                    status_msg = data.get('status', 'UNKNOWN')
                    logger.warning(f"Traffic API status error ({model}): {status_msg}")
                    return None
                
                # Robust extraction: Ensure routes exist before indexing
                if not data.get('routes') or len(data['routes']) == 0:
                    logger.debug(f"No routes found for {origin} -> {destination} ({model})")
                    return None

                route = data['routes'][0]
                if not route.get('legs') or len(route['legs']) == 0:
                    logger.debug(f"No legs in route for {origin} -> {destination} ({model})")
                    return None
                
                leg = route['legs'][0]
                
                # 'duration_in_traffic' is only present if traffic data is available
                # Fallback to standard 'duration' if missing
                duration_node = leg.get('duration_in_traffic', leg.get('duration'))
                
                if not duration_node:
                    logger.warning(f"No duration data for {model} model")
                    return None

                return {
                    "model_used": model,
                    "seconds": duration_node['value'],
                    "human_readable": duration_node['text'],
                    "distance_meters": leg['distance']['value'],
                    "polyline": route['overview_polyline']['points'] 
                }
                
        except asyncio.TimeoutError:
            logger.warning(f"Traffic API timeout ({model})")
            return None
        except Exception as e:
            logger.error(f"Traffic Engine error ({model}): {e}")
            return None

    async def get_traffic_metrics(
        self, 
        origin: str, 
        destination: str,
        departure_time: Union[int, str] = "now"
    ) -> Dict[str, Any]:
        """
        Orchestrates parallel requests to build the Triangular Distribution.
        Fires 3 concurrent API calls (optimistic, best_guess, pessimistic).
        
        Returns: 
            Dict with 'min', 'mode', 'max' (in minutes) and 'polyline'
        """
        # SAFETY LOCK: Uses the centralized config flag to prevent real API calls.
        if config.USE_MOCK_DATA:
            logger.debug("Using mock traffic data")
            return mocks.get_mock_traffic()

        if not self.api_key:
            logger.warning("No Traffic API Key found. Using Mock.")
            return mocks.get_mock_traffic()

        async with aiohttp.ClientSession() as session:
            # 1. Define the 3 concurrent tasks
            task_opt = self._fetch_single_route(session, origin, destination, "optimistic", departure_time)
            task_best = self._fetch_single_route(session, origin, destination, "best_guess", departure_time)
            task_pess = self._fetch_single_route(session, origin, destination, "pessimistic", departure_time)
            
            # 2. Fire them all at once (AsyncIO Scatter/Gather pattern)
            results = await asyncio.gather(task_opt, task_best, task_pess)
            
            clean_data: Dict[str, Any] = {}
            polyline_data = None
            
            for res in results:
                if res:
                    mins = round(res["seconds"] / 60.0, 2)
                    
                    if res["model_used"] == "best_guess":
                        clean_data["mode"] = mins
                    elif res["model_used"] == "optimistic":
                        clean_data["min"] = mins
                    elif res["model_used"] == "pessimistic":
                        clean_data["max"] = mins
                    
                    # Capture polyline from any available source
                    if not polyline_data and res.get("polyline"):
                        polyline_data = res["polyline"]

            # Attach polyline if captured
            if polyline_data:
                clean_data["polyline"] = polyline_data

            # Fail-safe: If API partially failed, fill gaps with the mode
            if "mode" in clean_data:
                if "min" not in clean_data:
                    clean_data["min"] = clean_data["mode"] * 0.9
                if "max" not in clean_data:
                    clean_data["max"] = clean_data["mode"] * 1.2
            
            # If completely failed, return Mock
            if not clean_data:
                logger.warning("All traffic models failed. Returning mock data.")
                return mocks.get_mock_traffic()
            
            logger.debug(f"Traffic metrics: {clean_data}")
            return clean_data

# --- UNIT TEST BLOCK ---
if __name__ == "__main__":
    import time
    async def test_run():
        engine = TrafficEngine()
        home = "Stony Brook University, NY"
        jfk = "JFK Airport, NY"
        
        logger.info(f"Fetching PARALLEL traffic models for: {home} -> {jfk}")
        start = time.time()
        
        data = await engine.get_traffic_metrics(home, jfk)
        
        duration = time.time() - start
        logger.info(f"\n✅ Completed in {duration:.2f} seconds")
        logger.info(f"Optimistic (Min): {data.get('min')} mins")
        logger.info(f"Best Guess (Mode): {data.get('mode')} mins")
        logger.info(f"Pessimistic (Max): {data.get('max')} mins")
        
        if 'polyline' in data:
            logger.info(f"Polyline captured: {data['polyline'][:30]}...")

    asyncio.run(test_run())