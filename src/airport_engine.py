import numpy as np
from datetime import datetime
from typing import List, Tuple, Union

# HIGH-PERFORMANCE IMPORT
# Attempt to load the C++ module. Fallback to SciPy if missing.
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
    Generates synthetic processing times (Queue Theory) based on airport tier,
    seasonality, and time-of-day congestion factors.
    """
    def __init__(self) -> None:
        # Tier 1 Airports (Top 30 Busiest - High Volatility).
        self.tier_1: List[str] = [
            "ATL", "DFW", "DEN", "ORD", "LAX", "JFK", "LAS", "MCO", "MIA", "CLT", 
            "SEA", "PHX", "EWR", "SFO", "IAH", "BOS", "FLL", "MSP", "LGA", "DTW", 
            "PHL", "SLC", "DCA", "SAN", "BWI", "TPA", "AUS", "IAD", "BNA", "MDW"
        ]
        # Tier 2 Airports (Regional Hubs - More Efficient).
        self.tier_2: List[str] = ["PBI", "BUR", "SNA", "HOU", "DAL", "STL", "PDX", "SMF", "OAK", "RDU", "RSW"]

    def _get_tier(self, airport_code: str) -> int:
        """Classifies airport complexity based on IATA code."""
        code = airport_code.upper()
        if code in self.tier_1: return 1
        elif code in self.tier_2: return 2
        else: return 3 

    def _get_base_params(self, airport_code: str) -> Tuple[float, float]:
        """Returns statistical moments (Average, Scale) for the Gamma distribution."""
        tier = self._get_tier(airport_code)
        if tier == 1:
            return 15.0, 4.0  # High chaos (e.g. JFK).
        elif tier == 2:
            return 9.0, 2.0  # Moderate.
        else:
            return 3.0, 1.5  # Efficient (e.g. ISP).

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
        """Simulates ticket counter / bag drop latency using C++ Gamma Engine."""
        if not has_bags:
            return np.random.uniform(0, 3, iterations)
            
        tier = self._get_tier(airport_code)
        
        if tier == 1: avg, scale = 13, 4.0
        elif tier == 2: avg, scale = 9.0, 2.0
        else: avg, scale = 3.0, 1.0

        if epoch_time:
            dt = datetime.fromtimestamp(epoch_time)
            mult = self._get_time_multiplier(dt) * self._get_day_multiplier(dt)
            avg *= mult
            scale *= mult

        shape = avg / scale
        
        # C++ OPTIMIZATION SWAP
        if USE_CPP:
            return flightrisk_cpp.simulate_gamma(shape, scale, iterations)
        else:
            return gamma.rvs(a=shape, scale=scale, size=iterations)

    def simulate_security(
        self, 
        airport_code: str, 
        epoch_time: Union[int, float], 
        is_precheck: bool = False, 
        iterations: int = 1000
    ) -> np.ndarray:
        """Core simulation for TSA security checkpoints using C++ Gamma Engine."""
        dt = datetime.fromtimestamp(epoch_time)
        avg, scale = self._get_base_params(airport_code)
        
        total_mult = self._get_time_multiplier(dt) * self._get_day_multiplier(dt)
        avg *= total_mult
        scale *= total_mult 

        if is_precheck:
            avg *= 0.35
            scale *= 0.4 
            
        shape = avg / scale

        # C++ OPTIMIZATION SWAP
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

    def get_total_airport_time(
        self, 
        airport_code: str, 
        epoch_time: Union[int, float], 
        has_bags: bool, 
        is_precheck: bool, 
        iterations: int = 1000
    ) -> np.ndarray:
        """Aggregates all airport processes."""        
        checkin = self.simulate_checkin(airport_code, has_bags, epoch_time, iterations)
        security = self.simulate_security(airport_code, epoch_time, is_precheck, iterations)
        walk = self.simulate_walk(airport_code, iterations)
        
        return checkin + security + walk