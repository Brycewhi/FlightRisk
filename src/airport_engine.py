import numpy as np
from datetime import datetime
from typing import List, Tuple, Union, Optional, Dict, Any
import config
import aiohttp
import asyncio
import mocks

# HIGH-PERFORMANCE IMPORT
try:
    import flightrisk_cpp 
    USE_CPP = True
except ImportError:
    from scipy.stats import gamma 
    USE_CPP = False
    print("WARNING: C++ Module not found. Running in slower mode.")

class AirportEngine:
    """
    Simulation engine for airport terminal operations.
    Hybrid Architecture:
    1. Tries to fetch Real-Time TSA Wait Times (API).
    2. Fallback: Uses Queue Theory based on Airport Tier & Time-of-Day.
    """
    
    def __init__(self) -> None:
        self.api_key = config.RAPID_API_KEY
        self.host = "tsa-wait-times.p.rapidapi.com"
        self.base_url = "https://tsa-wait-times.p.rapidapi.com/airports/"
        
        # Tier 1 Airports (Top 30 Busiest - High Volatility).
        self.tier_1: List[str] = [
            "ATL", "DFW", "DEN", "ORD", "LAX", "JFK", "LAS", "MCO", "MIA", "CLT", 
            "SEA", "PHX", "EWR", "SFO", "IAH", "BOS", "FLL", "MSP", "LGA", "DTW", 
            "PHL", "SLC", "DCA", "SAN", "BWI", "TPA", "AUS", "IAD", "BNA", "MDW"
        ]
        # Tier 2 Airports (Regional Hubs - More Efficient).
        self.tier_2: List[str] = ["PBI", "BUR", "SNA", "HOU", "DAL", "STL", "PDX", "SMF", "OAK", "RDU", "RSW"]

    async def _fetch_live_wait_time(self, session: aiohttp.ClientSession, airport_code: str) -> Optional[float]:
        """
        Async fetch for live TSA data.
        Returns: Wait time in minutes (float) or None if API fails.
        """
        # Mock Mode
        if config.USE_MOCK_DATA:
            return mocks.get_mock_tsa_wait(airport_code)

        if not self.api_key:
            return None

        # Clean IATA code (e.g. "JFK International" -> "JFK")
        code = airport_code.split()[0].strip().upper()[:3]
        url = f"{self.base_url}{code}"
        
        headers = {
            "x-rapidapi-host": self.host,
            "x-rapidapi-key": self.api_key
        }

        try:
            # Short timeout to prevent blocking the main solver
            async with session.get(url, headers=headers, timeout=2.5) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Robust parsing for different API response shapes
                    if isinstance(data, dict):
                        return float(data.get('wait_minutes', data.get('estimated_wait_time', 20.0)))
                    elif isinstance(data, list) and len(data) > 0:
                        return float(data[0].get('wait_minutes', 20.0))
                        
                return None
        except Exception:
            return None

    def _get_tier(self, airport_code: str) -> int:
        """Classifies airport complexity based on IATA code."""
        code = airport_code.upper()
        if any(t in code for t in self.tier_1): return 1
        elif any(t in code for t in self.tier_2): return 2
        else: return 3 

    def _get_base_params(self, airport_code: str, real_mean: Optional[float] = None) -> Tuple[float, float]:
        """
        Returns statistical moments (Average, Scale) for the Gamma distribution.
        CRITICAL: If 'real_mean' is provided, it OVERRIDES the tier-based average.
        """
        # 1. Determine the Mean (Average Wait)
        if real_mean is not None:
            avg = real_mean
            # If we have real data, variance is usually proportional to the mean
            scale = avg * 0.25 
        else:
            # Fallback to Heuristics
            tier = self._get_tier(airport_code)
            if tier == 1:
                avg, scale = 15.0, 4.0  # High chaos (e.g. JFK).
            elif tier == 2:
                avg, scale = 9.0, 2.0  # Moderate.
            else:
                avg, scale = 3.0, 1.5  # Efficient (e.g. ISP).
        
        return avg, scale

    def _get_time_multiplier(self, dt_object: datetime) -> float:
        """Calculates congestion factor based on hour of day (Rush Hour logic)."""
        hour = dt_object.hour
        if 5 <= hour < 9: return 1.3
        elif 15 <= hour < 19: return 1.2
        elif (10 <= hour < 14) or (hour >= 21): return 0.7   
        return 1.0

    def _get_day_multiplier(self, dt_object: datetime) -> float:
        """Calculates seasonality and weekend congestion factors."""
        day = dt_object.weekday()
        month = dt_object.month
        multiplier = 1.0
        
        if day == 4 or day == 6: multiplier *= 1.15 
        if day == 1 or day == 2: multiplier *= 0.85
        if month in [6,7,8,11,12]: multiplier *= 1.1
            
        return multiplier

    def simulate_checkin(
        self, 
        airport_code: str, 
        has_bags: bool, 
        epoch_time: Union[int, float], 
        iterations: int = 1000
    ) -> np.ndarray:
        """Simulates ticket counter / bag drop latency."""
        if not has_bags:
            return np.random.uniform(0, 3, iterations)
            
        tier = self._get_tier(airport_code)
        
        if tier == 1: avg, scale = 13.0, 4.0
        elif tier == 2: avg, scale = 9.0, 2.0
        else: avg, scale = 3.0, 1.0

        if epoch_time:
            dt = datetime.fromtimestamp(epoch_time)
            mult = self._get_time_multiplier(dt) * self._get_day_multiplier(dt)
            avg *= mult
            scale *= mult

        shape = avg / scale
        
        if USE_CPP:
            return flightrisk_cpp.simulate_gamma(shape, scale, iterations)
        else:
            return gamma.rvs(a=shape, scale=scale, size=iterations)

    def simulate_security(
        self, 
        airport_code: str, 
        epoch_time: Union[int, float], 
        is_precheck: bool = False, 
        iterations: int = 1000,
        real_mean: Optional[float] = None 
    ) -> np.ndarray:
        """Core simulation for TSA security checkpoints."""
        dt = datetime.fromtimestamp(epoch_time)
        
        # HYBRID LOGIC: Use real mean if available, else heuristic
        avg, scale = self._get_base_params(airport_code, real_mean)
        
        # Only apply multipliers if we are using heuristics (Real data already includes congestion)
        if real_mean is None:
            total_mult = self._get_time_multiplier(dt) * self._get_day_multiplier(dt)
            avg *= total_mult
            scale *= total_mult 

        if is_precheck:
            avg *= 0.35
            scale *= 0.4 
            
        shape = avg / scale

        if USE_CPP:
            return flightrisk_cpp.simulate_gamma(shape, scale, iterations)
        else:
            return gamma.rvs(a=shape, scale=scale, size=iterations)

    def simulate_walk(self, airport_code: str, iterations: int = 1000) -> np.ndarray:
        """Simulates terminal transit time (Normal Distribution)."""
        tier = self._get_tier(airport_code)
        if tier == 1: return np.random.normal(12, 5, iterations)
        elif tier == 2: return np.random.normal(7, 2, iterations)
        else: return np.random.normal(3, 1, iterations)

    async def get_total_airport_time(
        self, 
        session: aiohttp.ClientSession, 
        airport_code: str, 
        epoch_time: Union[int, float], 
        has_bags: bool, 
        is_precheck: bool, 
        iterations: int = 1000
    ) -> Tuple[np.ndarray, Dict[str, Any]]: 
        """Aggregates all airport processes."""
        
        # 1. Try to fetch Live Data
        real_wait = await self._fetch_live_wait_time(session, airport_code)
        
        # 2. Run Simulations
        checkin = self.simulate_checkin(airport_code, has_bags, epoch_time, iterations)
        
        # Pass the real_wait to security logic
        security = self.simulate_security(airport_code, epoch_time, is_precheck, iterations, real_mean=real_wait)
        
        walk = self.simulate_walk(airport_code, iterations)
        
        total_dist = checkin + security + walk
        
        return total_dist, {
            "checkin": float(np.mean(checkin)),
            "security": float(np.mean(security)),
            "walk": float(np.mean(walk)),
            "used_live_data": real_wait is not None
        }

# --- UNIT TEST BLOCK ---
if __name__ == "__main__":
    async def test_run():
        print("Testing Airport Engine...")
        engine = AirportEngine()
        async with aiohttp.ClientSession() as session:
            # Simulate a JFK trip with bags
            dists, stats = await engine.get_total_airport_time(
                session, "JFK", int(datetime.now().timestamp()), True, False
            )
            print(f"JFK Stats (Has Bags, No Precheck): {stats}")
            print(f"Used Live Data? {stats['used_live_data']}")
    
    asyncio.run(test_run())