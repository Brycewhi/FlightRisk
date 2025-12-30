import numpy as np
from scipy.stats import gamma, norm
from datetime import datetime

class AirportEngine:
    def __init__(self):
        # Tier 1 Airports (Top 30 Busiest).
        self.tier_1 = [
            "ATL", "DFW", "DEN", "ORD", "LAX", "JFK", "LAS", "MCO", "MIA", "CLT", 
            "SEA", "PHX", "EWR", "SFO", "IAH", "BOS", "FLL", "MSP", "LGA", "DTW", 
            "PHL", "SLC", "DCA", "SAN", "BWI", "TPA", "AUS", "IAD", "BNA", "MDW"
        ]
        # Tier 2 Airports (More Efficient Airports).
        self.tier_2 = ["PBI", "BUR", "SNA", "HOU", "DAL", "STL", "PDX", "SMF", "OAK", "RDU", "RSW"]

    def _get_tier(self, airport_code):
        # Helper to classify airport tier.
        code = airport_code.upper()
        if code in self.tier_1: return 1
        elif code in self.tier_2: return 2
        else: return 3

    def _get_base_params(self, airport_code):
        # Returns standard TSA line (avg, scale) based on tier.
        tier = self._get_tier(airport_code)
        if tier == 1:
            return 25, 4.0  # High chaos.
        elif tier == 2:
            return 15, 2.5  # Medium chaos.
        else:
            return 10, 1.5  # Low chaos.

    def _get_time_multiplier(self, dt_object):
        # Returns a multiplier based on hour of day.
        # Peak: 5am-9am (Morning Rush) and 3pm-7pm (Evening Rush).
        hour = dt_object.hour
        
        # Morning Rush (Business travelers + Early flights).
        if 5 <= hour < 9:
            return 1.3
        
        # Evening Rush (Post-work + International departures).
        elif 15 <= hour < 19:
            return 1.2
        
        # The quicker times (Mid-day or Late Night).
        elif (10 <= hour < 14) or (hour >= 21):
            return 0.7
            
        # Standard rate.
        else:
            return 1.0

    def _get_day_multiplier(self, dt_object):
        # Returns a multiplier based on day of week and month (Holiday Season). 
        # Weekday: 0=Mon, 6=Sun.
        day = dt_object.weekday()
        month = dt_object.month
        
        multiplier = 1.0
        
        # Weekend Penalty (Friday & Sunday are heaviest).
        if day == 4 or day == 6: 
            multiplier *= 1.15
            
        # Mid-Week Bonus (Tuesday & Wednesday are lightest).
        if day == 1 or day == 2:
            multiplier *= 0.85
            
        # Holiday Season Penalty (Summer/Nov/Dec).
        if month in [6,7,8,11,12]:
            multiplier *= 1.1
            
        return multiplier

    def simulate_checkin(self, airport_code, has_bags, epoch_time, iterations=1000):
        # Simulates time spent at the ticket counter / bag drop.
        # Digital check-in (No bags): Almost 0 time, with slight noise.
        if not has_bags:
            return np.random.uniform(0, 5, iterations)
            
        tier = self._get_tier(airport_code)
        
        # Base stats for Bag Drop lines.
        if tier == 1:
            avg, scale = 18, 4.0 # Big hubs have chaotic bag lines.
        elif tier == 2:
            avg, scale = 10, 2.0
        else:
            avg, scale = 5, 1.0  # Regional is quick.

        # Apply time multipliers (Holidays = longer bag lines).
        if epoch_time:
            dt = datetime.fromtimestamp(epoch_time)
            mult = self._get_time_multiplier(dt) * self._get_day_multiplier(dt)
            avg *= mult
            scale *= mult

        shape = avg / scale
        return gamma.rvs(a=shape, scale=scale, size=iterations)

    def simulate_security(self, airport_code, epoch_time, is_precheck=False, iterations=1000):
        # Main simulation function integrating all variables.
        # epoch_time: The Unix timestamp of your arrival at the airport.
        
        # Convert timestamp to datetime object.
        dt = datetime.fromtimestamp(epoch_time)
        
        # Get Base Stats.
        avg, scale = self._get_base_params(airport_code)
        
        # Calculate Multipliers.
        time_mult = self._get_time_multiplier(dt)
        day_mult = self._get_day_multiplier(dt)
        total_mult = time_mult * day_mult
        
        # Apply Multipliers to the Base Stats.
        # Both average wait and volatility increase during rush hour.
        avg *= total_mult
        scale *= total_mult 

        # Apply TSA PreCheck Reduction.
        if is_precheck:
            avg *= 0.35
            scale *= 0.4
            
        # Generate Gamma Distribution
        # Mean = Shape * Scale -> Shape = Mean / Scale
        shape = avg / scale
        
        return gamma.rvs(a=shape, scale=scale, size=iterations)

    def simulate_walk(self, airport_code, iterations=1000):
        # Simulates the walk/train ride from Security to the Gate.
        # Uses Normal Distribution because walking speed is consistent.
        
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

    def get_total_airport_time(self, airport_code, epoch_time, has_bags, is_precheck, iterations=1000):
        # Helper function to get the sum of all 3 distinct processes (Curb-to-Gate).
        
        checkin_times = self.simulate_checkin(airport_code, has_bags, epoch_time, iterations)
        security_times = self.simulate_security(airport_code, epoch_time, is_precheck, iterations)
        walk_times = self.simulate_walk(airport_code, iterations)
        
        # Vectorized Sum: Returns 1,000 total scenarios.
        return checkin_times + security_times + walk_times

if __name__ == "__main__":
    print("\n--- ✈️  AIRPORT ENGINE DIAGNOSTIC TEST ✈️  ---")
    
    # Initialize the Engine.
    ae = AirportEngine()
    now_time = int(datetime.now().timestamp())
    
    # Test Tier Logic (JFK vs ISP).
    print("\n[TEST 1] Comparing Tier 1 (JFK) vs Tier 3 (ISP)...")
    jfk_waits = ae.simulate_security("JFK", now_time)
    isp_waits = ae.simulate_security("ISP", now_time)
    
    print(f"   > JFK Average Wait:  {np.mean(jfk_waits):.1f} min (Expected: High)")
    print(f"   > ISP Average Wait:  {np.mean(isp_waits):.1f} min (Expected: Low)")
    
    # Test PreCheck Logic.
    print("\n[TEST 2] Testing PreCheck Benefit at LAX...")
    std_waits = ae.simulate_security("LAX", now_time, is_precheck=False)
    pre_waits = ae.simulate_security("LAX", now_time, is_precheck=True)
    
    print(f"   > Standard Lane:     {np.mean(std_waits):.1f} min")
    print(f"   > PreCheck Lane:     {np.mean(pre_waits):.1f} min (Should be ~60% lower)")

    # Test Full Curb-to-Gate.
    print("\n[TEST 3] Testing Full Curb-to-Gate Experience (JFK + Bags)...")
    total_time = ae.get_total_airport_time("JFK", now_time, has_bags=True, is_precheck=False)
    print(f"   > Total Airport Time: {np.mean(total_time):.1f} min (Includes Bag Drop + TSA + Walk)")
    
    print("\n--- DIAGNOSTIC COMPLETE ---")