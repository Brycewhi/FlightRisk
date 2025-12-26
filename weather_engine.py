import requests
import polyline
import config

class WeatherEngine:
    """
    Service class to handle geospatial weather data.
    Decodes route geometry to analyze atmospheric conditions at specific trip intervals.
    """

    def __init__(self):
        # Initialize credentials from config.
        self.api_key = config.OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    def get_route_weather(self, encoded_polyline: str):
        """
        Performs spatial sampling along the route polyline.
        Fetches weather data for the Origin, Midpoint, and Destination.
        """
        try:
            # Decode the compressed polyline into a list of (Lat, Lon) coordinates.
            coordinates = polyline.decode(encoded_polyline)
            if not coordinates:
                return None
            
            # Define our sampling indices.
            indices = {
                "Start": 0,
                "Midpoint": len(coordinates) // 2,
                "Destination": len(coordinates) - 1
            }

            route_weather_report = {}

            # Iterate through samples to build a comprehensive risk profile.
            for label, index in indices.items():
                lat, lon = coordinates[index]

                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "imperial" 
                }

                response = requests.get(self.base_url, params=params)                
                if response.status_code == 200:
                    data = response.json()
                    # Ensure weather list is not empty
                    weather_main = data['weather'][0] if data.get('weather') else {'main': 'Clear', 'description': 'no data'}

                    # Store key metrics for the Risk Engine.
                    route_weather_report[label] = {
                        "temp": data['main']['temp'],
                        "condition": weather_main['main'], # e.g. 'Rain', 'Snow'
                        "description": weather_main['description'],
                        "location_name": data.get('name', label)
                    }
                else:
                    print(f"Weather API Error at {label}: Status {response.status_code}")

            return route_weather_report if route_weather_report else None

        except Exception as e:
            # Catching decoding errors or network timeouts.
            print(f"Weather Engine System Error: {e}")
            return None
        
# Local Unit Test Block
if __name__ == "__main__":
    test_engine = WeatherEngine()
    
    # This is a sample encoded polyline string (represents a short path).
    # We use this to test if our decoding and sampling logic works in isolation.
    sample_polyline = r"uzpwFvps|U" 
    
    print("Running Local Weather Engine Test...")
    test_report = test_engine.get_route_weather(sample_polyline)
    
    if test_report:
        print("Spatial Sampling Successful!")
        for loc, data in test_report.items():
            print(f"   {loc}: {data['condition']} - {data['temp']}°F")
    else:
        print("Test Failed. Check error message above.")