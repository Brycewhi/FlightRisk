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
    
    def evaluate_trip(self, traffic_results, weather_report, buffer_mins=120):
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
        
        # Hadamard Product 
        simulated_times = traffic_samples * weather_samples
        df = pd.Series(simulated_times)

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
            "risk": "CRITICAL" if success_prob < 75 else "HIGH" if success_prob < 90 else "LOW"
        }
    
# Local Unit Test Block.
if __name__ == "__main__":
    # Initialize the Engine.
    engine = RiskEngine()

    # Test 1: Weather Impact and Volatility. Snowy day should create larger safety gap than a clear day.
    dummy_traffic = {
        'optimistic': {'seconds': 2400},  # 40 mins
        'best_guess': {'seconds': 3000},  # 50 mins
        'pessimistic': {'seconds': 4800}   # 80 mins
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
    
    res_clear = engine.evaluate_trip(dummy_traffic, clear_day, buffer_mins=120)
    res_snow = engine.evaluate_trip(dummy_traffic, snowy_day, buffer_mins=120)
    
    # In snow, the P95 should be significantly higher due to the volatility map.
    print(f"--- TEST 1: WEATHER IMPACT ---")
    print(f"CLEAR: Avg={res_clear['avg_eta']}m, P95={res_clear['p95_eta']}m, Prob={res_clear['success_probability']}%")
    print(f"SNOW:  Avg={res_snow['avg_eta']}m, P95={res_snow['p95_eta']}m, Prob={res_snow['success_probability']}%")

    # Test 2: Tail Risk (P95 vs Average)
    # Shows that even if the average is under the deadline, the P95 can flag a risk.
    
    tight_traffic = {
        'optimistic': {'seconds': 3600},  # 60 mins
        'best_guess': {'seconds': 4200},  # 70 mins
        'pessimistic': {'seconds': 6000}   # 100 mins
    }
    
    # User only has 90 minutes. P95 will be > buffer_mins.
    res_tight = engine.evaluate_trip(tight_traffic, clear_day, buffer_mins=90)
    
    # This shows why we don't just use the average to decide when to leave.
    print(f"\n--- TEST 2: TAIL RISK (Deadline = 90 mins) ---")
    print(f"Average Trip: {res_tight['avg_eta']} mins")
    print(f"95% Risk Time: {res_tight['p95_eta']} mins")
    print(f"Success Probability: {res_tight['success_probability']}%")
    print(f"Risk Status: {res_tight['risk']}")
    

    # TEST 3: Volatility and buffer logic
    # Show that "Uncertainty" (Snow) decreases your safety buffer faster than "Certainty" (Clear)
    print(f"\n--- TEST 3: SAFETY BUFFER & VOLATILITY ---")
    
    # Compare the safety buffer left in both scenarios.
    print(f"   - Clear Day Volatility (std_dev): {res_clear['std_dev']} mins")
    print(f"   - Snowy Day Volatility (std_dev): {res_snow['std_dev']} mins")
    print(f"   - Clear Day Buffer: {res_clear['buffer_remaining']} mins")
    print(f"   - Snowy Day Buffer: {res_snow['buffer_remaining']} mins")
    
    # Logic Check:
    gap = res_clear['buffer_remaining'] - res_snow['buffer_remaining']
    print(f"   - Volatility 'Tax': {round(gap, 1)} mins lost to weather uncertainty.")
    
    if res_snow['buffer_remaining'] < res_clear['buffer_remaining']:
        print("   - SUCCESS: Engine correctly identified that weather reduces the safety margin.")