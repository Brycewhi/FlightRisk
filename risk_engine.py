class RiskEngine:
    def __init__(self):
        # Values representing a multiplier of how much each weather condition impacts traffic (Based on general Dept of Transportation stats).
        self.weather_multipiers = {
            "Clear": 1.0,
            "Clouds": 1.05,
            "Mist": 1.10,
            "Drizzle": 1.15,
            "Fog": 1.20,
            "Rain": 1.25,
            "Thunderstorm": 1.40,
            "Snow": 1.50
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
        mapping = {
            "start": "Start",
            "mid": "Midpoint",
            "end": "Destination"
        }
        for model_key, weather_key in mapping.items():
            point_data = weather_report.get(weather_key, {})
            condition = point_data.get('condition', 'Clear')
            
            # Weighted calculation of weather impact.
            impact = self.weather_multipiers.get(condition, 1.0)
            total_multiplier += impact * self.weights[model_key]
            
        return round(total_multiplier, 2)
    
    def calculate_confidence(self, opt_min, pess_min, best_guess_min):
        # Measures model reliability using a variance ratio. High spread between Optimistic and Pessimistic estimates = Low Confidence.
        if best_guess_min == 0: return 0

        # Calculate spread relative to best_guess.
        variance_ratio = (pess_min - opt_min) / best_guess_min

        # Transform variance into 0-100% confidence scale.
        confidence = max(0, 100 * (1-variance_ratio))
        return int(confidence)
    
    def evaluate_trip(self, traffic_results, weather_report, buffer_mins=120):
        # Merges traffic variance, weather impact, and user time constraints to provide a final risk assessment.
        # Calculate weather impact.
        impact = self.calculate_weather_impact(weather_report)

        # Normalize traffic data to minutes. 
        opt = traffic_results['optimistic']['seconds'] /60
        best_guess = traffic_results['best_guess']['seconds'] /60
        pess = traffic_results['pessimistic']['seconds'] /60

        # Worst case scenario eta.
        adjusted_eta = pess * impact
        
        # Determine model pediction confidence.
        confidence = self.calculate_confidence(opt, best_guess, pess)

        # Calculate remaining time to make flight.
        remaining = buffer_mins - adjusted_eta
        
        # Categorize risk based on remaining time.
        return {
            "adjusted_eta": round(adjusted_eta, 1),
            "confidence": confidence,
            "buffer": round(remaining, 1),
            "multiplier": impact,
            "risk": "CRITICAL" if remaining < 20 else "HIGH" if remaining < 45 else "LOW"
        }

# Local Unit Test Block.
if __name__ == "__main__":
    # Initialize the Engine.
    engine = RiskEngine()

    # TEST 1: Weighting Logic.
    # Goal: Prove that weather at the Destination (0.60 weight) .
    # impacts the score more than weather at the Start (0.15 weight).
    
    jfk_storm = {
        "Start": {"condition": "Clear"}, 
        "Midpoint": {"condition": "Clear"}, 
        "Destination": {"condition": "Thunderstorm"} # Heavy Weight.
    }
    
    sbu_storm = {
        "Start": {"condition": "Thunderstorm"}, # Light Weight.
        "Midpoint": {"condition": "Clear"}, 
        "Destination": {"condition": "Clear"}
    }
    
    impact_jfk = engine.calculate_weather_impact(jfk_storm)
    impact_sbu = engine.calculate_weather_impact(sbu_storm) 
    
    print(f"   - Multiplier for JFK Storm: {impact_jfk}")
    print(f"   - Multiplier for SBU Storm: {impact_sbu}")

    # TEST 2: Volatility and Confidence.
    # Goal: Prove that high variance between traffic models reduces confidence.

    # 40 min best case vs 100 min worst case (High Uncertainty).
    conf_low = engine.calculate_confidence(40, 100, 60)
    
    # 55 min best case vs 65 min worst case (High Stability).
    conf_high = engine.calculate_confidence(55, 65, 60)
    
    print(f"   - High Variance Confidence: {conf_low}%")
    print(f"   - Low Variance Confidence:  {conf_high}%")

    # TEST 3: Integrated Evaluation.
    # Goal: Verify the final adjusted ETA and Risk Status.
    
    dummy_traffic = {
        'optimistic': {'duration_seconds': 2400},  # 40 mins
        'best_guess': {'duration_seconds': 3000},  # 50 mins
        'pessimistic': {'duration_seconds': 3600}   # 60 mins
    }
    
    # Simulating a 1.25x impact (Rain everywhere).
    rainy_day = {
        "Start": {"condition": "Rain"}, 
        "Midpoint": {"condition": "Rain"}, 
        "Destination": {"condition": "Rain"}
    }
    
    # Run evaluation with a tight 80-minute buffer.
    result = engine.evaluate_trip(dummy_traffic, rainy_day, buffer_mins=80)
    
    print(f"   - Adjusted ETA (Pessimistic * Weather): {result['adjusted_eta']} mins")
    print(f"   - Remaining Buffer: {result['buffer']} mins")
    print(f"   - Risk Level: {result['risk']}")
  