import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any

class RiskEngine:
    """
    Stochastic Inference Engine for travel risk quantification.
    
    This class leverages Monte Carlo methods to model the variance in travel arrival 
    times by fusing deterministic traffic data with probabilistic weather and 
    airport operational distributions.
    """
    def __init__(self) -> None:
        # Scalar multipliers for mean travel time impact based on atmospheric conditions.
        self.weather_multipliers: Dict[str, float] = {
            "Clear": 1.0, 
            "Clouds": 1.0, 
            "Mist": 1.05, 
            "Drizzle": 1.08,
            "Fog": 1.15, 
            "Rain": 1.2, 
            "Thunderstorm": 1.35, 
            "Snow": 1.45
        }
        # Standard deviation (volatility) mapping for Gaussian noise in weather modeling.
        self.volatility_map: Dict[str, float] = {
            "Clear": 0.01, 
            "Clouds": 0.02, 
            "Rain": 0.10, 
            "Thunderstorm": 0.15, 
            "Snow": 0.20
        }
        # Weighted influence of corridor segments on the total impact mean.
        # Heavily weighted toward the 'end' (destination) to reflect terminal arrival priority.
        self.weights: Dict[str, float] = {
            "start": 0.15, 
            "mid": 0.25, 
            "end": 0.65
        }

    def calculate_weather_impact(self, weather_report: Dict[str, Any]) -> Tuple[float, str]:
        """
        Calculates a unified, weighted weather multiplier and identifies primary risk condition.

        Args:
            weather_report: Dictionary containing sampled weather data for Start, Midpoint, and Destination.
            
        Returns:
            A tuple of (total_multiplier, primary_condition).
        """
        total_multiplier: float = 0
        primary_condition: str = "Clear"
        # Mapping UI labels to logic keys.
        mapping: Dict[str, str] = {
            "start": "Start", 
            "mid": "Midpoint", 
            "end": "Destination"
        }
        for model_key, weather_key in mapping.items():
            point_data = weather_report.get(weather_key, {})
            condition = point_data.get('condition', 'Clear')
            impact = self.weather_multipliers.get(condition, 1.0)

            # Apply linear combination of weighted impacts.
            total_multiplier += impact * self.weights[model_key]
            # Destination condition is designated as the primary environmental driver.
            if weather_key == "Destination": 
                primary_condition = condition
        return round(total_multiplier, 2), primary_condition
    
    def evaluate_trip(
        self, 
        traffic_results: Dict[str, Any], 
        weather_report: Dict[str, Any], 
        airport_delays: float, 
        airport_stats: Optional[Dict[str, float]] = None, 
        buffer_mins: float = 120
    ) -> Dict[str, Any]:
        """
        Executes 1,000 iterations of a Monte Carlo simulation to generate a risk profile.

        Args:
            traffic_results: Dictionary containing optimistic, best_guess, and pessimistic bounds.
            weather_report: Segmented weather conditions.
            airport_delays: Total static or simulated delay from airport operations (mins).
            airport_stats: Optional granular breakdown of TSA/Check-in/Walk times.
            buffer_mins: The available time window before gate closure.

        Returns:
            Comprehensive results dictionary with statistical eta and success probability.
        """
        # Set deterministic seed for statistical reproducibility and debugging.
        np.random.seed(16)
        
        impact_mean, condition = self.calculate_weather_impact(weather_report)
        volatility = self.volatility_map.get(condition, 0.05)
        
        # Extract traffic vectors and convert from seconds to minutes.
        opt = traffic_results['optimistic']['seconds'] / 60
        best = traffic_results['best_guess']['seconds'] / 60
        pess = traffic_results['pessimistic']['seconds'] / 60
        
        # Guardrail: Enforce logical consistency for the triangular distribution density.
        if opt >= best: opt = best - 1
        if pess <= best: pess = best + 1

        iterations = 1000

        # Generate traffic samples using a Triangular Distribution.
        traffic_samples = np.random.triangular(opt, best, pess, iterations)
        
        # Inject stochastic weather noise via Normal Distribution.
        if impact_mean > 1.02: 
            weather_samples = np.random.normal(impact_mean, volatility, iterations)
            drive_times = traffic_samples * weather_samples
        else:
            drive_times = traffic_samples

        # Compute total trip time including airport overhead.
        total_trip_times = drive_times + airport_delays
        df = pd.Series(total_trip_times)

        # Statistical extraction of the risk profile.
        avg_time = df.mean()
        p95_time = df.quantile(0.95)
        success_prob = (df < buffer_mins).mean() * 100
        safety_buffer = buffer_mins - p95_time
        
        # Construct granular time breakdown for dashboard visualization.
        avg_drive = drive_times.mean()
        if airport_stats:
            breakdown = {
                "drive": int(avg_drive),
                "tsa": int(airport_stats.get('checkin', 0) + airport_stats.get('security', 0)),
                "walk": int(airport_stats.get('walk', 0))
            }
        else:
            # Fallback heuristic if granular stats are unavailable.
            breakdown = {
                "drive": int(avg_drive),
                "tsa": int(avg_time * 0.3), 
                "walk": int(avg_time * 0.1)
            }

        return {
            "avg_eta": round(avg_time, 1),
            "p95_eta": round(p95_time, 1),
            "success_probability": round(success_prob, 1),
            "buffer_remaining": round(safety_buffer, 1),
            "multiplier": impact_mean,
            "condition": condition,
            "raw_data": df.tolist(),
            "breakdown": breakdown 
        }


# Local Unit Test
if __name__ == "__main__":
    print("Testing RiskEngine Monte Carlo Logic...")
    engine = RiskEngine()

    # Mock Traffic Data (30m optimistic, 45m best guess, 70m pessimistic).
    mock_traffic = {
        'optimistic': {'seconds': 30 * 60},
        'best_guess': {'seconds': 45 * 60},
        'pessimistic': {'seconds': 70 * 60}
    }

    # Mock Weather Data (Heavy Snow Scenario).
    mock_weather = {
        'Start': {'condition': 'Snow'},
        'Midpoint': {'condition': 'Snow'},
        'Destination': {'condition': 'Snow'}
    }

    # Mock Airport Stats.
    mock_stats = {
        'checkin': 15,
        'security': 25,
        'walk': 10
    }
    total_airport_time = sum(mock_stats.values()) # 50 mins.

    # Run Evaluation.
    # We set a buffer of 120 mins to see if we'd make it.
    report = engine.evaluate_trip(traffic_results=mock_traffic, weather_report=mock_weather, airport_delays=total_airport_time, airport_stats=mock_stats, buffer_mins=120)

    # Print Results to Terminal.
    print("-" * 30)
    print(f"Condition: {report['condition']}")
    print(f"Weather Multiplier: {report['multiplier']}x")
    print(f"Average Total ETA: {report['avg_eta']} mins")
    print(f"Worst Case (P95): {report['p95_eta']} mins")
    print(f"Success Probability: {report['success_probability']}%")
    print(f"Time Breakdown: {report['breakdown']}")
    print("-" * 30)

    # Simple logic check.
    if report['p95_eta'] > 100:
        print("✅ Logic Check Passed: Snow correctly increased the worst-case ETA.")
    else:
        print("❌ Logic Check Failed: Snow didn't seem to impact the simulation correctly.")
