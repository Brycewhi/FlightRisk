import requests
import urllib.parse
import config

class TrafficEngine:
    """
    Class to interface with Google Maps Directions API.
    Designed to extract geospatial data and travel time variance for risk modeling.
    """
    def __init__(self):
        # Initialize with credentials from config.
        self.api_key = config.GOOGLE_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api/directions/json"

    def get_route(self, origin: str, destination:str, model: str = "best_guess", departure_time = "now") -> dict:
        """
        Calculates trip duration using probabalistic traffic models.

        Args:
            origin: Starting address or Place ID.
            destination: Target address or Place ID.
            model: 'best_guess', 'optimistic', or 'pessimistic'.
        
        Returns: 
            Dict containing raw seconds (for computation) and polyline (for mapping).
        """
        # Google API requires integer for timestamps
        if isinstance(departure_time, (int, float)):
            departure_time = int(departure_time)
            
        # Parameter configuration for live traffic analysis.
        params = {
            "origin": origin,
            "destination": destination,
            "departure_time": departure_time, # Timestamp
            "traffic_model": model, # Defines risk profile for the duration.
            "key": self.api_key,
            "mode": "driving"

        }
        try:
            # Execute the network request
            response = requests.get(self.base_url, params = params)
            data = response.json()

            # Handle API-level errors (e.g. invalid addresses).
            if data['status'] != 'OK':
                print(f"API Error: {data['status']}")
                if 'error_message' in data:
                    print(f"Reason: {data['error_message']}")
                return None
            
            # Extract specific route data
            route = data['routes'][0]
            leg = route['legs'][0]

            return {
                # Use .get() to fall back to standard duration if live traffic data is null.
                "seconds": leg.get('duration_in_traffic', leg['duration'])['value'],
                "human_readable": leg.get('duration_in_traffic', leg['duration'])['text'],
                "distance_meters": leg['distance']['value'],
                "polyline": route['overview_polyline']['points'], # Captured for weather integration.
                "model_used": model
            }
        except Exception as e:
            # Log system level errors.
            print(f"Traffic System System Error: {e}")
            return None

# Local Unit Test Block.
# Only executed if the file is run directly, not when imported.
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

