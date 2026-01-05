import requests
import config
from typing import Optional, Dict, Union, Any

class TrafficEngine:
    """
    Sensing layer for geospatial data acquisition. 
    Interfaces with Google Maps Directions API to provide duration variance 
    required for stochastic risk modeling.
    """
    api_key: str
    base_url: str
    def __init__(self) -> None:
        self.api_key = config.GOOGLE_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api/directions/json"

    def get_route(
        self, 
        origin: str, 
        destination: str, 
        model: str = "best_guess", 
        departure_time: Union[int, float, str] = "now"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves trip duration estimates using probabilistic traffic models.

        Args:
            origin: Departure address or coordinate string.
            destination: Arrival address or coordinate string.
            model: Statistical traffic model ('best_guess', 'optimistic', 'pessimistic').
            departure_time: Epoch timestamp for predictive analysis.
        
        Returns: 
            Dict containing duration (seconds), polyline (for corridor weather), 
            and metadata. Returns None on API-level or network failure.
        """
        # Google API requires integer for timestamps.
        if isinstance(departure_time, (int, float)):
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
            response = requests.get(self.base_url, params = params)
            data = response.json()

            # Handle non-OK statuses (e.g., zero results, quota exceeded).            
            if data['status'] != 'OK':
                print(f"API Error: {data['status']}")
                if 'error_message' in data:
                    print(f"Reason: {data['error_message']}")
                return None
            
            # Extract specific route data.
            # Navigate hierarchy: A single-leg trip corresponds to the primary route.
            route = data['routes'][0]
            leg = route['legs'][0]

            return {
                # Use .get() as fallback: Use baseline duration if traffic-adjusted value is null.
                "seconds": leg.get('duration_in_traffic', leg['duration'])['value'],
                "human_readable": leg.get('duration_in_traffic', leg['duration'])['text'],
                "distance_meters": leg['distance']['value'],
                "polyline": route['overview_polyline']['points'], # Captured for weather sampling.
                "model_used": model
            }
        except Exception as e:
            # Catch network/connection level failures to prevent engine crashes.
            print(f"Traffic System Error: {e}")
            return None

# Local Unit Test Block.
if __name__ == "__main__":
    engine = TrafficEngine()
    
    # Test coordinates.
    home = "Stony Brook University"
    jfk = "JFK Airport"
    
    print(f"Testing 'Safe' model (Pessimistic)...")
    safe_res = engine.get_route(home, jfk, model="pessimistic")
    
    if safe_res:
        print(f"Time: {safe_res['human_readable']} ({safe_res['seconds']}s)")
        print(f"Path Data (Polyline): {safe_res['polyline'][:20]}...")   

