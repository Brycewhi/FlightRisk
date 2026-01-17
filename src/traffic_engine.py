import aiohttp
import asyncio
import config
from typing import Optional, Dict, Union, Any

class TrafficEngine:
    """
    Sensing layer for geospatial data acquisition. 
    Interfaces with Google Maps Directions API via AsyncIO to provide 
    duration variance required for stochastic risk modeling.
    """
    api_key: str
    base_url: str

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
        # Google API requires integer for timestamps.
        if isinstance(departure_time, (float)):
            departure_time = int(departure_time)
            
        # Parameter configuration for predictive traffic analytics.
        params: Dict[str, Union[str, int]] = {
            "origin": origin,
            "destination": destination,
            "departure_time": departure_time, 
            "traffic_model": model, 
            "key": self.api_key,
            "mode": "driving"
        }

        try:
            async with session.get(self.base_url, params=params) as response:
                # Handle non-200 HTTP statuses.
                if response.status != 200:
                    print(f"API Error ({model}): Status {response.status}")
                    return None
                    
                data = await response.json()

                # Handle non-OK API statuses (e.g., zero results, quota exceeded).
                if data['status'] != 'OK':
                    print(f"API Status Error ({model}): {data['status']}")
                    if 'error_message' in data:
                        print(f"Reason: {data['error_message']}")
                    return None
                
                # Extract specific route data.
                # Navigate hierarchy: A single-leg trip corresponds to the primary route.
                route = data['routes'][0]
                leg = route['legs'][0]

                return {
                    "model_used": model,
                    # Use .get() as fallback: Use baseline duration if traffic-adjusted value is null.
                    "seconds": leg.get('duration_in_traffic', leg['duration'])['value'],
                    "human_readable": leg.get('duration_in_traffic', leg['duration'])['text'],
                    "distance_meters": leg['distance']['value'],
                    "polyline": route['overview_polyline']['points'] # Captured for weather sampling.
                }
                
        except Exception as e:
            # Catch network/connection level failures to prevent engine crashes.
            print(f"Traffic System Error ({model}): {e}")
            return None

    async def get_traffic_metrics(
        self, 
        origin: str, 
        destination: str,
        departure_time: Union[int, str] = "now"
    ) -> Dict[str, Any]:
        """
        Orchestrates parallel requests to build the Triangular Distribution.
        
        Returns:
            Dict containing:
            - 'min' (optimistic minutes)
            - 'mode' (best_guess minutes)
            - 'max' (pessimistic minutes)
            - 'polyline' (from best_guess route)
        """
        async with aiohttp.ClientSession() as session:
            # 1. Define the 3 tasks.
            task_opt = self._fetch_single_route(session, origin, destination, "optimistic", departure_time)
            task_best = self._fetch_single_route(session, origin, destination, "best_guess", departure_time)
            task_pess = self._fetch_single_route(session, origin, destination, "pessimistic", departure_time)
            
            # 2. Await them all simultaneously.
            # The total wait time is now equal to the SLOWEST request, not the sum of all 3.
            results = await asyncio.gather(task_opt, task_best, task_pess)
            
            # 3. Parse and Clean Data for the Stochastic Model.
            clean_data = {}
            
            for res in results:
                if res:
                    # Store polyline from the "best_guess" route as the canonical path.
                    if res["model_used"] == "best_guess":
                        clean_data["polyline"] = res["polyline"]
                        clean_data["mode"] = round(res["seconds"] / 60, 2)
                    elif res["model_used"] == "optimistic":
                        clean_data["min"] = round(res["seconds"] / 60, 2)
                    elif res["model_used"] == "pessimistic":
                        clean_data["max"] = round(res["seconds"] / 60, 2)

            # Sanity Check: Ensure we have all 3 points for the Triangle.
            if len(clean_data) < 3:
                print("Warning: Partial traffic data received. Distribution may be incomplete.")
                
            return clean_data

# Local Unit Test Block.
if __name__ == "__main__":
    import time
    
    # Async wrapper for local testing.
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