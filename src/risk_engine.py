import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any


# HIGH-PERFORMANCE IMPORT
try:
    import flightrisk_cpp
    USE_CPP = True
except ImportError:
    USE_CPP = False
    print("⚠️ WARNING: C++ Module (flightrisk_cpp) not found. Using Python fallback.")


class RiskEngine:
    """
    Stochastic Inference Engine for travel risk quantification.
    
    HYBRID ARCHITECTURE:
    - Logic/Weights: Handled in Python.
    - Monte Carlo Simulation: Offloaded to C++ (flightrisk_cpp) for 100x speedup.
    """
    def __init__(self) -> None:
        self.weather_multipliers: Dict[str, float] = {
            "Clear": 1.0, "Clouds": 1.0, "Mist": 1.05, "Drizzle": 1.08,
            "Fog": 1.15, "Rain": 1.2, "Thunderstorm": 1.35, "Snow": 1.45
        }
        self.volatility_map: Dict[str, float] = {
            "Clear": 0.01, "Clouds": 0.02, "Rain": 0.10, 
            "Thunderstorm": 0.15, "Snow": 0.20
        }
        self.weights: Dict[str, float] = {
            "start": 0.15, "mid": 0.25, "end": 0.65
        }

    def _triangular_to_normal(self, opt: float, mode: float, pess: float) -> Tuple[float, float]:
        """
        Approximates Triangular distribution parameters (Min, Mode, Max)
        into Normal distribution parameters (Mean, StdDev) for the C++ engine.
        """
        mean = (opt + mode + pess) / 3.0
        # Variance of Triangular = (a^2 + b^2 + c^2 - ab - ac - bc) / 18
        variance = (opt**2 + mode**2 + pess**2 - (opt*mode) - (opt*pess) - (mode*pess)) / 18.0
        return mean, np.sqrt(variance)

    def calculate_weather_impact(self, weather_report: Dict[str, Any]) -> Tuple[float, str]:
        """Calculates weighted weather multiplier."""
        total_multiplier: float = 0
        primary_condition: str = "Clear"
        mapping: Dict[str, str] = {"start": "Start", "mid": "Midpoint", "end": "Destination"}
        
        for model_key, weather_key in mapping.items():
            point_data = weather_report.get(weather_key, {})
            condition = point_data.get('condition', 'Clear')
            impact = self.weather_multipliers.get(condition, 1.0)
            
            total_multiplier += impact * self.weights[model_key]
            if weather_key == "Destination": 
                primary_condition = condition
                
        return round(total_multiplier, 2), primary_condition
    
    def evaluate_trip(
        self, 
        traffic_results: Dict[str, Any], 
        weather_report: Dict[str, Any], 
        airport_delays: Any, 
        airport_stats: Optional[Dict[str, float]] = None, 
        buffer_mins: float = 120
    ) -> Dict[str, Any]:
        """
        Executes Monte Carlo simulation.
        If C++ module is available, it calculates Probability via compiled code.
        """
        # 1. Weather Logic
        impact_mean, condition = self.calculate_weather_impact(weather_report)
        volatility = self.volatility_map.get(condition, 0.05)
        
        # 2. Traffic Stats (Convert Seconds -> Minutes)
        opt = traffic_results['optimistic']['seconds'] / 60
        best = traffic_results['best_guess']['seconds'] / 60
        pess = traffic_results['pessimistic']['seconds'] / 60
        
        # Enforce Logical Consistency
        if opt >= best: opt = best - 1
        if pess <= best: pess = best + 1

        # Apply Weather Multiplier to Traffic Estimates
        if impact_mean > 1.0:
            opt *= impact_mean
            best *= impact_mean
            pess *= (impact_mean * 1.1) 

        # C++ ACCELERATION PATH
        if USE_CPP:
            traffic_mean, traffic_std = self._triangular_to_normal(opt, best, pess)
            # Combine Traffic Volatility with Weather Volatility (Sum of Variances)
            traffic_std = np.sqrt(traffic_std**2 + (traffic_mean * volatility)**2)

            # Estimate TSA Parameters (Reverse Engineering Gamma)
            tsa_mean = airport_stats.get('security', 20.0) if airport_stats else 20.0
            tsa_scale = 4.0 if condition in ["Rain", "Snow"] else 2.0
            tsa_shape = tsa_mean / tsa_scale
            
            walk_time = airport_stats.get('walk', 10.0) if airport_stats else 10.0

            # EXECUTE C++ SIMULATION (100k iterations)
            failure_prob = flightrisk_cpp.calculate_risk(
                buffer_mins, traffic_mean, traffic_std,
                tsa_shape, tsa_scale, walk_time, 100000
            )
            
            # Calculate Derived Stats (for UI display)
            success_prob = (1.0 - failure_prob) * 100
            avg_eta = traffic_mean + tsa_mean + walk_time
            total_std = np.sqrt(traffic_std**2 + (tsa_mean * 0.5)**2) 
            p95_eta = avg_eta + (1.645 * total_std)
            safety_buffer = buffer_mins - p95_eta
            
            # Generate small sample for KDE charts (Python-side)
            raw_data = np.random.normal(avg_eta, total_std, 1000).tolist()

        
        # PYTHON PATH (Fallback)
        else:
            iterations = 1000
            traffic_samples = np.random.triangular(opt, best, pess, iterations)
            
            if impact_mean > 1.02: 
                traffic_samples *= np.random.normal(1.0, volatility, iterations)

            if isinstance(airport_delays, (float, int)):
                total_trip_times = traffic_samples + airport_delays
            else:
                total_trip_times = traffic_samples + airport_delays[:iterations]

            df = pd.Series(total_trip_times)
            avg_eta = df.mean()
            p95_eta = df.quantile(0.95)
            success_prob = (df < buffer_mins).mean() * 100
            safety_buffer = buffer_mins - p95_eta
            raw_data = df.tolist()

        # Granular Breakdown for Dashboard
        if airport_stats:
            breakdown = {
                "drive": int(traffic_results['best_guess']['seconds'] / 60),
                "tsa": int(airport_stats.get('checkin', 0) + airport_stats.get('security', 0)),
                "walk": int(airport_stats.get('walk', 0))
            }
        else:
            breakdown = {"drive": 45, "tsa": 20, "walk": 10}

        if success_prob >= 95:
            risk_label = "VERY LOW"
        elif success_prob >= 80:
            risk_label = "LOW"
        elif success_prob >= 60:
            risk_label = "MODERATE"
        else:
            risk_label = "CRITICAL"

        return {
            "avg_eta": round(avg_eta, 1),
            "p95_eta": round(p95_eta, 1),
            "success_probability": round(success_prob, 1),
            "risk": risk_label,
            "buffer_remaining": round(safety_buffer, 1),
            "multiplier": impact_mean,
            "condition": condition,
            "raw_data": raw_data,
            "breakdown": breakdown 
        }