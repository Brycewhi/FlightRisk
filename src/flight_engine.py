import aiohttp
import asyncio
from datetime import datetime, timedelta
import config
from typing import Optional, Dict, Any
import mocks 

class FlightEngine:
    """
    Validation Layer for external flight data.
    Interfaces with AeroDataBox API via AsyncIO.
    """
    
    def __init__(self) -> None:
        self.api_key = config.RAPID_API_KEY
        self.base_url = "https://aerodatabox.p.rapidapi.com/flights/number/"
        self.host = "aerodatabox.p.rapidapi.com"

    async def get_flight_details(self, session: aiohttp.ClientSession, flight_number: str) -> Optional[Dict[str, Any]]:
        """
        Coordinates sequential lookups for today and tomorrow.
        """
        
        # SAFETY LOCK via centralized Config
        if config.USE_MOCK_DATA:
            print(f"SAFE MODE: Using Mock Data for {flight_number}")
            return mocks.get_mock_flight_data(flight_number)

        # REAL API CALL (Only executes if unlocked)
        print(f"Fetching real-time data for {flight_number}...")
        
        # Search today's flights first (current date UTC/local).
        today_date = datetime.now().strftime('%Y-%m-%d')
        result = await self._fetch_and_parse(session, flight_number, today_date)
        
        if result:
            return result

        # Roll over to tomorrow if no future flights remain today.
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        return await self._fetch_and_parse(session, flight_number, tomorrow_date)

    async def _fetch_and_parse(
        self, 
        session: aiohttp.ClientSession, 
        flight_number: str, 
        date_str: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves, filters, and parses API response.
        """
        url = f"{self.base_url}{flight_number}/{date_str}"
        
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }

        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                if not data: 
                    return None
                
                now_epoch = int(datetime.now().timestamp())
                valid_flights = []
                
                for flight in data:
                    dep = flight.get('departure', {})
                    arr = flight.get('arrival', {})
                    
                    dep_str = dep.get('scheduledTime', {}).get('local')
                    arr_str = arr.get('scheduledTime', {}).get('local')

                    if dep_str:
                        try:
                            # Normalize ISO string to handle varying timezone offsets.
                            clean_dep = dep_str.split('+')[0]
                            dep_ts = int(datetime.fromisoformat(clean_dep).timestamp())
                            
                            # Calculate arrival
                            if arr_str:
                                clean_arr = arr_str.split('+')[0]
                                arr_ts = int(datetime.fromisoformat(clean_arr).timestamp())
                            else:
                                arr_ts = dep_ts + 7200

                            # Guardrail: Exclude flights that have already departed.
                            if dep_ts > now_epoch:
                                valid_flights.append({
                                    "flight_num": flight_number,
                                    "dep_ts": dep_ts,
                                    "arr_ts": arr_ts,
                                    "origin_airport": dep.get('airport', {}).get('name', 'Origin'),
                                    "dest_airport": arr.get('airport', {}).get('name', 'Destination'),
                                    "duration_mins": (arr_ts - dep_ts) // 60,
                                    "status": flight.get('status', 'Scheduled')
                                })
                        except (ValueError, TypeError):
                            continue

                # Identify and return the chronological 'next' flight.
                if valid_flights:
                    valid_flights.sort(key=lambda x: x['dep_ts'])
                    return valid_flights[0]
                    
                return None
            
        except Exception as e:
            print(f"FLIGHT System Failure: {e}")
            return None

# --- UNIT TEST BLOCK ---
if __name__ == "__main__":
    async def test_run():
        fe = FlightEngine()
        test_num = "B6454" 
        print(f"✈️ Validating Flight {test_num}...")
        
        async with aiohttp.ClientSession() as session:
            res = await fe.get_flight_details(session, test_num)
            
        if res:
            departure = datetime.fromtimestamp(res['dep_ts']).strftime('%I:%M %p')
            print(f"✅ Flight {test_num} validated: {res['origin_airport']} at {departure}")
        else:
            print(f"❌ No future data for {test_num}")

    asyncio.run(test_run())