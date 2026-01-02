import requests
from datetime import datetime
import config

class FlightEngine:
    def __init__(self):
        self.api_key = config.RAPID_API_KEY
        self.base_url = "https://aerodatabox.p.rapidapi.com/flights/number/"
        self.host = "aerodatabox.p.rapidapi.com"

    def get_flight_details(self, flight_number: str):
        today_date = datetime.now().strftime('%Y-%m-%d')
        url = f"{self.base_url}{flight_number}/{today_date}"
        
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if not data: return None
                
                for flight in data:
                    dep = flight.get('departure', {})
                    arr = flight.get('arrival', {})

                    dep_sched = dep.get('scheduledTime', {})
                    arr_sched = arr.get('scheduledTime', {})

                    dep_str = dep_sched.get('local')
                    arr_str = arr_sched.get('local')

                    if dep_str and arr_str:
                        # Convert ISO format to Unix Epoch.
                        dep_ts = int(datetime.fromisoformat(dep_str).timestamp())
                        arr_ts = int(datetime.fromisoformat(arr_str).timestamp())

                        return {
                            "flight_num": flight_number,
                            "dep_ts": dep_ts,
                            "arr_ts": arr_ts,
                            "origin_airport": dep.get('airport', {}).get('name', 'Origin'),
                            "dest_airport": arr.get('airport', {}).get('name', 'Destination'),
                            "duration_mins": (arr_ts - dep_ts) // 60,
                            "status": flight.get('status', 'Unknown')
                        }
                return None
            return None
        except Exception as e:
            print(f"FlightEngine Error: {e}")
            return None

# Unit Test.
if __name__ == "__main__":
    flight = FlightEngine()
    result = flight.get_flight_details("B66")
    if result:
        print(f"\n SUCCESS! Flight B66 departs {result['origin_airport']} at {datetime.fromtimestamp(result['dep_ts'])}")
    else:
        print("\n FAIL! No flight data found.")