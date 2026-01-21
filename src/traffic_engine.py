import aiohttp
import asyncio
import config
from typing import Optional, Dict, Union, Any
import mocks 

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
            async with session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    print(f"TRAFFIC API Error ({model}): Status {response.status}")
                    return None
                    
                data = await response.json()

                if data.get('status') != 'OK':
                    # Common error: 'ZERO_RESULTS' or 'OVER_QUERY_LIMIT'
                    print(f"TRAFFIC API Status Error ({model}): {data.get('status')}")
                    return None
                
                # Robust extraction: Ensure routes exist before indexing
                if not data.get('routes'):
                    return None

                route = data['routes'][0]
                leg = route['legs'][0]
                
                # 'duration_in_traffic' is only present if traffic data is available
                # Fallback to standard 'duration' if missing
                duration_node = leg.get('duration_in_traffic', leg.get('duration'))

                return {
                    "model_used": model,
                    "seconds": duration_node['value'],
                    "human_readable": duration_node['text'],
                    "distance_meters": leg['distance']['value'],
                    "polyline": route['overview_polyline']['points'] 
                }
                
        except Exception as e:
            print(f"TRAFFIC System Error ({model}): {e}")
            return None

    async def get_traffic_metrics(
        self, 
        origin: str, 
        destination: str,
        departure_time: Union[int, str] = "now"
    ) -> Dict[str, Any]:
        """
        Orchestrates parallel requests to build the Triangular Distribution.
        Returns: 'min', 'mode', 'max' (in minutes) and 'polyline'.
        """
        # SAFETY LOCK: Uses the centralized config flag to prevent real API calls.
        if config.USE_MOCK_DATA:
            return mocks.get_mock_traffic()

        if not self.api_key:
            print("No Traffic API Key found. Using Mock.")
            return mocks.get_mock_traffic()

        async with aiohttp.ClientSession() as session:
            # 1. Define the 3 concurrent tasks
            task_opt = self._fetch_single_route(session, origin, destination, "optimistic", departure_time)
            task_best = self._fetch_single_route(session, origin, destination, "best_guess", departure_time)
            task_pess = self._fetch_single_route(session, origin, destination, "pessimistic", departure_time)
            
            # 2. Fire them all at once (AsyncIO Scatter/Gather pattern)
            results = await asyncio.gather(task_opt, task_best, task_pess)
            
            clean_data = {}
            
            for res in results:
                if res:
                    mins = round(res["seconds"] / 60.0, 2)
                    
                    if res["model_used"] == "best_guess":
                        clean_data["polyline"] = res["polyline"]
                        clean_data["mode"] = mins
                    elif res["model_used"] == "optimistic":
                        clean_data["min"] = mins
                    elif res["model_used"] == "pessimistic":
                        clean_data["max"] = mins

            # Fail-safe: If API partial failed, fill gaps with the mode
            if "mode" in clean_data:
                if "min" not in clean_data: clean_data["min"] = clean_data["mode"] * 0.9
                if "max" not in clean_data: clean_data["max"] = clean_data["mode"] * 1.2
            
            # If completely failed, return Mock
            if not clean_data:
                return mocks.get_mock_traffic()
                
            return clean_data
# --- UNIT TEST BLOCK ---
if __name__ == "__main__":
    import time
    async def test_run():
        engine = TrafficEngine()
        home = "Stony Brook University, NY"
        jfk = "JFK Airport, NY"
        
        print(f"Fetching PARALLEL traffic models for: {home} -> {jfk}")
        start = time.time()
        
        data = await engine.get_traffic_metrics(home, jfk)
        
        duration = time.time() - start
        print(f"\n✅ Completed in {duration:.2f} seconds")
        print(f"Optimistic (Min): {data.get('min')} mins")
        print(f"Best Guess (Mode): {data.get('mode')} mins")
        print(f"Pessimistic (Max): {data.get('max')} mins")
        
        if 'polyline' in data:
            print(f"Polyline captured: {data['polyline'][:30]}...")

    asyncio.run(test_run())