import numpy as np
from scipy.stats import gamma
from datetime import datetime
from typing import List, Tuple, Union, Optional

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
        else: return 3 # Tier 3 -> small regional airports.

    def _get_base_params(self, airport_code: str) -> Tuple[float, float]:
        """
        Returns statistical moments (Average, Scale) for the Gamma distribution.
        Higher scale indicates higher variance (chaos).
        """
        tier = self._get_tier(airport_code)
        if tier == 1:
            return 25.0, 4.0  # High chaos (e.g. JFK).
        elif tier == 2:
            return 15.0, 2.5  # Moderate.
        else:
            return 10.0, 1.5  # Efficient (e.g. ISP).

    def _get_time_multiplier(self, dt_object: datetime) -> float:
        """Calculates congestion factor based on hour of day (Rush Hour logic)."""
        hour = dt_object.hour
        
        # Morning Rush (Business travelers + Early flights).
        if 5 <= hour < 9: return 1.3
        # Evening Rush (Post-work + International departures).
        elif 15 <= hour < 19: return 1.2
        # Off-Peak (Mid-day or Late Night).
        elif (10 <= hour < 14) or (hour >= 21): return 0.7   
        
        return 1.0

    def _get_day_multiplier(self, dt_object: datetime) -> float:
        """Calculates seasonality and weekend congestion factors."""
        day = dt_object.weekday() # 0=Mon, 6=Sun
        month = dt_object.month
        
        multiplier = 1.0
        
        # Weekend Penalty (Friday & Sunday are peak travel days).
        if day == 4 or day == 6: 
            multiplier *= 1.15 
        # Mid-Week Bonus (Tuesday & Wednesday are lightest).
        if day == 1 or day == 2:
            multiplier *= 0.85
            
        # Holiday Season Penalty (Summer/Nov/Dec).
        if month in [6,7,8,11,12]:
            multiplier *= 1.1
            
        return multiplier

    def simulate_checkin(
        self, 
        airport_code: str, 
        has_bags: bool, 
        epoch_time: Union[int, float], 
        iterations: int = 1000
    ) -> np.ndarray:
        """Simulates ticket counter / bag drop latency using Gamma distribution."""
        if not has_bags:
            # Digital check-in is near-instantaneous with minor noise.
            return np.random.uniform(0, 5, iterations)
            
        tier = self._get_tier(airport_code)
        
        # Base stats for Bag Drop lines.
        if tier == 1:
            avg, scale = 18, 4.0 # Big hubs have chaotic bag lines.
        elif tier == 2:
            avg, scale = 10, 2.0
        else:
            avg, scale = 5, 1.0  # Regional is quick.

        # Apply temporal multipliers to simulate bag queues (Holidays = longer bag lines).
        if epoch_time:
            dt = datetime.fromtimestamp(epoch_time)
            mult = self._get_time_multiplier(dt) * self._get_day_multiplier(dt)
            avg *= mult
            scale *= mult # Variance increases with congestion.

        # Gamma Shape Calculation: Mean = Shape * Scale -> Shape = Mean / Scale
        shape = avg / scale
        return gamma.rvs(a=shape, scale=scale, size=iterations)

    def simulate_security(
        self, 
        airport_code: str, 
        epoch_time: Union[int, float], 
        is_precheck: bool = False, 
        iterations: int = 1000
    ) -> np.ndarray:
        """
        Core simulation for TSA security checkpoints.
        Fusion of base airport efficiency and real-time congestion factors.
        """
        
        dt = datetime.fromtimestamp(epoch_time)
        avg, scale = self._get_base_params(airport_code)
        
        # Composite Multiplier
        total_mult = self._get_time_multiplier(dt) * self._get_day_multiplier(dt)
        
        avg *= total_mult
        scale *= total_mult 

        # TSA PreCheck Efficiency Benefit        
        if is_precheck:
            avg *= 0.35 # 65% faster on average.
            scale *= 0.4 # Significantly less variance (predictable).
            
        shape = avg / scale
        return gamma.rvs(a=shape, scale=scale, size=iterations)

    def simulate_walk(self, airport_code: str, iterations: int = 1000) -> np.ndarray:
        """
        Simulates terminal transit time (Post-Security to Gate).
        Uses Normal Distribution as walking speed is generally consistent.
        """
        
        tier = self._get_tier(airport_code)
        
        if tier == 1:
            # JFK/ATL/LAX: You often take a train or walk 1 mile.
            # Avg: 12 mins, Std Dev: 5 mins.
            return np.random.normal(12, 5, iterations)
        elif tier == 2:
            # BUR/PBI: Medium walk. Avg: 7 mins.
            return np.random.normal(7, 2, iterations)
        else:
            # ISP: The gate is right there. Avg: 3 mins.
            return np.random.normal(3, 1, iterations)

    def get_total_airport_time(
        self, 
        airport_code: str, 
        epoch_time: Union[int, float], 
        has_bags: bool, 
        is_precheck: bool, 
        iterations: int = 1000
    ) -> np.ndarray:
        """
        Aggregates all airport processes into a single vector of total duration.
        Returns a 1,000-sample array representing the full 'Curb-to-Gate' experience.
        """        
        checkin = self.simulate_checkin(airport_code, has_bags, epoch_time, iterations)
        security = self.simulate_security(airport_code, epoch_time, is_precheck, iterations)
        walk = self.simulate_walk(airport_code, iterations)
        
        # Vectorized summation of stochastic arrays.
        return checkin + security + walk

# Local Unit Test Block.
if __name__ == "__main__":
    print("\n ✈️  AIRPORT ENGINE DIAGNOSTIC TEST ✈️ ")
    ae = AirportEngine()
    now_time = int(datetime.now().timestamp())
    
    # Test 1: Tier Logic Validation.
    print("\n[TEST 1] Comparing Tier 1 (JFK) vs Tier 3 (ISP)...")
    jfk_waits = ae.simulate_security("JFK", now_time)
    isp_waits = ae.simulate_security("ISP", now_time)
    
    assert np.mean(jfk_waits) > np.mean(isp_waits), "LOGIC FAIL: JFK should be slower than ISP"
    print(f"   > JFK Avg: {np.mean(jfk_waits):.1f} min | ISP Avg: {np.mean(isp_waits):.1f} min")
    
    # Test 2: PreCheck Logic Validation.
    print("\n[TEST 2] Testing PreCheck Benefit at LAX...")
    std = ae.simulate_security("LAX", now_time, is_precheck=False)
    pre = ae.simulate_security("LAX", now_time, is_precheck=True)
    
    assert np.mean(pre) < np.mean(std), "LOGIC FAIL: PreCheck should be faster"
    print(f"   > Standard: {np.mean(std):.1f} min | PreCheck: {np.mean(pre):.1f} min")
    print("   ✅ Logic Verified: PreCheck correctly reduces wait times.")