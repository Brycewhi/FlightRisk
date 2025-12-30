import numpy as np
import pandas as pd

class RiskEngine:
    def __init__(self):
        # Values representing a multiplier of how much each weather condition impacts traffic (Based on general Dept of Transportation stats).
        self.weather_multipliers = {
            "Clear": 1.0,
            "Clouds": 1.05,
            "Mist": 1.10,
            "Drizzle": 1.15,
            "Fog": 1.20,
            "Rain": 1.25,
            "Thunderstorm": 1.40,
            "Snow": 1.50
        }
        # Volatility mapping for Normal Distribution.
        self.volatility_map = {
            "Clear": 0.02,
            "Clouds": 0.03,
            "Drizzle": 0.05,
            "Mist": 0.08,
            "Fog": 0.10,
            "Haze": 0.10,
            "Rain": 0.12,
            "Thunderstorm": 0.20,
            "Snow": 0.25,
            "Squall": 0.40
        }
        # Weights representing the severity of weather impact on each point on route.
        # Priority given to destination as there is no time to cut down on at the end.
        self.weights = {
            "start": 0.15,
            "mid": 0.25,
            "end": 0.65
        }
    def calculate_weather_impact(self, weather_report):
        # Calculate a weighted average of weather impact along the route. 
        total_multiplier = 0
        primary_condition = "Clear"
        mapping = {
            "start": "Start",
            "mid": "Midpoint",
            "end": "Destination"
        }
        for model_key, weather_key in mapping.items():
            point_data = weather_report.get(weather_key, {})
            condition = point_data.get('condition', 'Clear')
            
            # Weighted calculation of weather impact.
            impact = self.weather_multipliers.get(condition, 1.0)
            total_multiplier += impact * self.weights[model_key]
            
            # Use destination weather to set volatility of simulation.
            if weather_key == "Destination":
                primary_condition = condition

        return round(total_multiplier, 2), primary_condition
    
    def evaluate_trip(self, traffic_results, weather_report, airport_delays, buffer_mins=120):
        # Setup Data.
        np.random.seed(16)
        impact_mean, condition = self.calculate_weather_impact(weather_report)
        volatility = self.volatility_map.get(condition, 0.05)
        
        # Normalize traffic (using 'seconds' from API output)
        opt = traffic_results['optimistic']['seconds'] / 60
        best = traffic_results['best_guess']['seconds'] / 60
        pess = traffic_results['pessimistic']['seconds'] / 60

        # The Monte Carlo Sim.
        iterations = 1000
        # Traffic uses Triangular distribution, Weather uses Normal distribution (Bell Curve)
        traffic_samples = np.random.triangular(opt, best, pess, iterations)
        weather_samples = np.random.normal(impact_mean, volatility, iterations)
        
        # Drive Time = Raw Traffic * Weather Multiplier
        # Total Time = Drive Time + Airport Processing (Bags + Security + Walk)
        drive_times = traffic_samples * weather_samples
        total_trip_times = drive_times + airport_delays
        df = pd.Series(total_trip_times)

        # Statistical analysis.
        avg_time = df.mean()
        p95_time = df.quantile(0.95)
        std_dev = df.std()
        success_prob = (df < buffer_mins).mean() * 100
        
        # Calculate a safety buffer 'remaining' based on the 95% safety margin
        safety_buffer = buffer_mins - p95_time

        return {
            "avg_eta": round(avg_time, 1),
            "p95_eta": round(p95_time, 1),
            "std_dev": round(std_dev, 1),
            "success_probability": round(success_prob, 1),
            "buffer_remaining": round(safety_buffer, 1),
            "multiplier": impact_mean,
            # Risk is based on probability, not just one number.
            "risk": "CRITICAL" if success_prob < 75 else "HIGH" if success_prob < 90 else "LOW",
            "raw_data": df.tolist() # Convert series back to list for visualizer 
        }
    
# Local Unit Test Block.
if __name__ == "__main__":
    # Initialize the Engine.
    engine = RiskEngine()

    # Create Dummy Airport Data
    # We simulate a Tier 1 Airport (Avg ~60 mins curb to gate time, High Variance)
    dummy_airport_delays = np.random.gamma(shape=10.0, scale=6.0, size=1000)

    # Test 1: Weather Impact and Volatility.
    dummy_traffic = {
        'optimistic': {'seconds': 2400},  # 40 mins
        'best_guess': {'seconds': 3000},  # 50 mins
        'pessimistic': {'seconds': 4800}  # 80 mins
    }
    
    clear_day = {
        "Start": {"condition": "Clear"}, 
        "Midpoint": {"condition": "Clear"}, 
        "Destination": {"condition": "Clear"}
    }
    
    snowy_day = {
        "Start": {"condition": "Snow"}, 
        "Midpoint": {"condition": "Snow"}, 
        "Destination": {"condition": "Snow"}
    }
    
    # Passing dummy data
    res_clear = engine.evaluate_trip(dummy_traffic, clear_day, dummy_airport_delays, buffer_mins=180)
    res_snow = engine.evaluate_trip(dummy_traffic, snowy_day, dummy_airport_delays, buffer_mins=180)
    
    print(f"--- TEST 1: WEATHER + AIRPORT INTEGRATION ---")
    print(f"CLEAR: Avg={res_clear['avg_eta']}m, P95={res_clear['p95_eta']}m")
    print(f"SNOW:  Avg={res_snow['avg_eta']}m, P95={res_snow['p95_eta']}m")

    # Test 2: Tail Risk (P95 vs Average)
    tight_traffic = {
        'optimistic': {'seconds': 3600},  # 60 mins
        'best_guess': {'seconds': 4200},  # 70 mins
        'pessimistic': {'seconds': 6000}  # 100 mins
    }
    
    # User only has 150 minutes total. 
    # 70 min drive + ~60 min airport = 130 mins avg.
    # But P95 might push over 150 due to volatility.
    res_tight = engine.evaluate_trip(tight_traffic, clear_day, dummy_airport_delays, buffer_mins=150)
    
    print(f"\n--- TEST 2: TAIL RISK (Deadline = 150 mins) ---")
    print(f"Average Trip: {res_tight['avg_eta']} mins")
    print(f"95% Risk Time: {res_tight['p95_eta']} mins")
    print(f"Success Probability: {res_tight['success_probability']}%")
    print(f"Risk Status: {res_tight['risk']}")

    # Volatility and buffer logic
    print(f"\n--- TEST 3: SAFETY BUFFER & VOLATILITY ---")
    print(f"   - Clear Day Volatility (std_dev): {res_clear['std_dev']} mins")
    print(f"   - Snowy Day Volatility (std_dev): {res_snow['std_dev']} mins")
    
    # Logic Check:
    gap = res_clear['buffer_remaining'] - res_snow['buffer_remaining']
    print(f"   - Volatility 'Tax': {round(gap, 1)} mins lost to weather uncertainty.")
    
    if res_snow['buffer_remaining'] < res_clear['buffer_remaining']:
        print("   - SUCCESS: Engine correctly identified that weather reduces the safety margin.")