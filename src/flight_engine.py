import aiohttp
import streamlit as st
import asyncio
import os
from datetime import datetime, timedelta
import config
from typing import Optional, Dict, Any, List
from mocks import get_mock_flight_data  # Mock Data Import

class FlightEngine:
    """
    Validation Layer for external flight data.
    Interfaces with AeroDataBox API via AsyncIO to retrieve real-time scheduled 
    departure and arrival timestamps for stochastic planning.
    """
    
    api_key: str
    base_url: str
    host: str

    def __init__(self) -> None:
        self.api_key = config.RAPID_API_KEY
        self.base_url = "https://aerodatabox.p.rapidapi.com/flights/number/"
        self.host = "aerodatabox.p.rapidapi.com"

    @st.cache_data(ttl=86400) # Keeps the flight data for 24 hours
    async def get_flight_details(_self, flight_number: str) -> Optional[Dict[str, Any]]:
        """
        Coordinates sequential lookups for today and tomorrow to find the 
        next available flight departure.
        Includes a Safety Lock to prevent accidental API credit usage during dev.
        """
        
        # SAFETY LOCK 
        # Unless this environment variable is EXACTLY "True", use mock.
        # This prevents going over API limits.
        if os.getenv("USE_REAL_DATA_DANGEROUS") != "True":
            print(f"SAFE MODE: Using Mock Data for {flight_number}")
            return get_mock_flight_data(flight_number)

        # REAL API CALL (Only executes if unlocked)
        print(f"Fetching real-time data for {flight_number}...")
        
        async with aiohttp.ClientSession() as session:
            # Search today's flights first (current date UTC/local).
            today_date: str = datetime.now().strftime('%Y-%m-%d')
            result = await _self._fetch_and_parse(session, flight_number, today_date)
            
            if result:
                return result

            # Roll over to tomorrow if no future flights remain today.
            tomorrow_date: str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            return await _self._fetch_and_parse(session, flight_number, tomorrow_date)

    async def _fetch_and_parse(
        self, 
        session: aiohttp.ClientSession, 
        flight_number: str, 
        date_str: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves, filters, and parses API response into a standardized flight object.
        """
        url: str = f"{self.base_url}{flight_number}/{date_str}"
        
        headers: Dict[str, str] = {
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
                
                now_epoch: int = int(datetime.now().timestamp())
                valid_flights: List[Dict[str, Any]] = []
                
                for flight in data:
                    dep = flight.get('departure', {})
                    arr = flight.get('arrival', {})
                    
                    # Extract ISO local strings (primary timing data).
                    dep_str: Optional[str] = dep.get('scheduledTime', {}).get('local')
                    arr_str: Optional[str] = arr.get('scheduledTime', {}).get('local')

                    if dep_str:
                        try:
                            # Normalize ISO string to handle varying timezone offsets.
                            clean_dep = dep_str.split('+')[0]
                            dep_ts = int(datetime.fromisoformat(clean_dep).timestamp())
                            
                            # Calculate arrival (defaults to +2 hours if API lacks arrival data).
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
            print(f"FlightEngine System Failure: {e}")
            return None

# Local Unit Test Block.
if __name__ == "__main__":
    # Async wrapper for local testing.
    async def test_run():
        fe = FlightEngine()
        test_num = "B6454" 
        print(f"✈️ Validating Flight {test_num}...")
        
        # NOTE: This will return Mock Data if env var is not set!
        res = await fe.get_flight_details(test_num)
        
        if res:
            # We use datetime.fromtimestamp because the engine returns raw integers
            departure = datetime.fromtimestamp(res['dep_ts']).strftime('%I:%M %p')
            print(f"✅ Flight {test_num} validated: {res['origin_airport']} at {departure}")
        else:
            print(f"❌ No future data for {test_num}")

    asyncio.run(test_run())