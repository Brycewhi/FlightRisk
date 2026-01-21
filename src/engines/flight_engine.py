import aiohttp
import asyncio
from datetime import datetime, timedelta
import config
from typing import Optional, Dict, Any
import logging
import sys
import os

# Add parent directory to path to import mocks
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tests import mocks

logger = logging.getLogger(__name__)

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
        
        Returns:
            Dict with flight details or None if not found
        """
        
        # SAFETY LOCK via centralized Config
        if config.USE_MOCK_DATA:
            logger.info(f"SAFE MODE: Using Mock Data for {flight_number}")
            return mocks.get_mock_flight_data(flight_number)

        # REAL API CALL (Only executes if unlocked)
        logger.debug(f"Fetching real-time data for {flight_number}...")
        
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
        Handles ISO 8601 timestamp parsing with timezone offsets.
        """
        url = f"{self.base_url}{flight_number}/{date_str}"
        
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }

        try:
            async with session.get(url, headers=headers, timeout=5.0) as response:
                if response.status != 200:
                    logger.warning(f"Flight API returned {response.status} for {flight_number}")
                    return None
                
                data = await response.json()
                if not data: 
                    logger.debug(f"No flight data returned for {flight_number} on {date_str}")
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
                            # Robust ISO 8601 parsing: handle +HH:MM, -HH:MM, and Z formats
                            dep_ts = self._parse_iso_timestamp(dep_str)
                            
                            # Calculate arrival
                            if arr_str:
                                arr_ts = self._parse_iso_timestamp(arr_str)
                            else:
                                # Fallback: assume 2-hour flight
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
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Failed to parse timestamp for {flight_number}: {e}")
                            continue

                # Identify and return the chronological 'next' flight.
                if valid_flights:
                    valid_flights.sort(key=lambda x: x['dep_ts'])
                    logger.info(f"Found {len(valid_flights)} valid flights for {flight_number}")
                    return valid_flights[0]
                
                logger.debug(f"No valid future flights for {flight_number}")
                return None
            
        except asyncio.TimeoutError:
            logger.warning(f"Flight API timeout for {flight_number}")
            return None
        except Exception as e:
            logger.error(f"Flight Engine critical failure for {flight_number}: {e}")
            return None

    @staticmethod
    def _parse_iso_timestamp(iso_str: str) -> int:
        """
        Robustly parses ISO 8601 timestamps.
        Handles formats like:
        - "2025-01-21T14:30:00+05:00"
        - "2025-01-21T14:30:00-05:00"
        - "2025-01-21T14:30:00Z"
        
        Returns:
            Unix timestamp (seconds since epoch)
        """
        # Normalize Zulu time
        if iso_str.endswith('Z'):
            iso_str = iso_str.replace('Z', '+00:00')
        
        try:
            # Split on the last '+' or '-' to separate datetime from offset
            # This handles both +HH:MM and -HH:MM formats
            if '+' in iso_str or iso_str.count('-') > 2:  # -2 for YYYY-MM-DD part
                # Use fromisoformat which handles offsets in Python 3.7+
                dt = datetime.fromisoformat(iso_str)
            else:
                # No timezone info, assume UTC
                dt = datetime.fromisoformat(iso_str)
            
            return int(dt.timestamp())
        except Exception:
            # Fallback: try removing timezone entirely
            try:
                clean_iso = iso_str.split('+')[0].split('-')
                # Reconstruct just YYYY-MM-DD HH:MM:SS
                if len(clean_iso) >= 3:
                    cleaned = f"{clean_iso[0]}-{clean_iso[1]}-{clean_iso[2]}"
                    dt = datetime.fromisoformat(cleaned)
                    return int(dt.timestamp())
            except:
                pass
            
            raise ValueError(f"Could not parse ISO timestamp: {iso_str}")

# --- UNIT TEST BLOCK ---
if __name__ == "__main__":
    async def test_run():
        fe = FlightEngine()
        test_num = "B6454" 
        logger.info(f"✈️ Validating Flight {test_num}...")
        
        async with aiohttp.ClientSession() as session:
            res = await fe.get_flight_details(session, test_num)
            
        if res:
            departure = datetime.fromtimestamp(res['dep_ts']).strftime('%I:%M %p')
            logger.info(f"✅ Flight {test_num} validated: {res['origin_airport']} at {departure}")
        else:
            logger.info(f"❌ No future data for {test_num}")

    asyncio.run(test_run())