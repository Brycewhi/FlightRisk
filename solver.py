import time
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any


# Import engines.
from traffic_engine import TrafficEngine
from weather_engine import WeatherEngine
from risk_engine import RiskEngine
from airport_engine import AirportEngine

def run_full_analysis(
    origin: str, 
    destination: str, 
    departure_time: int, 
    flight_time: int, 
    has_bags: bool, 
    is_precheck: bool
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the data flow between all engines to perform a single 
    point-in-time risk analysis.
    """
    # Initialize Engines
    traffic = TrafficEngine()
    weather = WeatherEngine()
    risk = RiskEngine()
    airport = AirportEngine()  
    
    buffer_mins: float = (flight_time - departure_time) / 60

    
    # Gather Traffic and Weather Data
    traffic_data: Dict[str, Any] = {}
    for model in ["optimistic", "best_guess", "pessimistic"]:
        route_res = traffic.get_route(origin, destination, model, departure_time=departure_time)
        
        # Fault Tolerance: If any traffic model fails, the entire analysis is invalid.
        if route_res is None:
            return None 
        
        traffic_data[model] = route_res
    
    # Spatial weather sampling based on the 'best_guess' route geometry.
    route_polyline = traffic_data['best_guess'].get('polyline')
    weather_report = weather.get_route_weather(route_polyline)
    if weather_report is None:
        return None

    # Airport Queue Simulation.
    drive_time_seconds = traffic_data['best_guess']['seconds']
    est_arrival = departure_time + drive_time_seconds
    
    # Basic IATA Resolver.
    target_airport = "JFK" 
    if "LGA" in destination.upper(): target_airport = "LGA"
    elif "EWR" in destination.upper(): target_airport = "EWR"

    # Generate 1,000-sample distributions for each airport segment.
    checkin_sim = airport.simulate_checkin(target_airport, has_bags, est_arrival, iterations=1000)
    security_sim = airport.simulate_security(target_airport, est_arrival, is_precheck, iterations=1000)
    walk_sim = airport.simulate_walk(target_airport, iterations=1000)
    
    # Aggregate airport delays for the Monte Carlo engine.
    total_airport_delays = checkin_sim + security_sim + walk_sim
    
    # Metadate for the UI breakdown.
    airport_stats = {
        "checkin": float(checkin_sim.mean()),
        "security": float(security_sim.mean()),
        "walk": float(walk_sim.mean())
    }

    # Final Stochastic Evaluation.
    return risk.evaluate_trip(
        traffic_results=traffic_data, 
        weather_report=weather_report, 
        airport_delays=total_airport_delays, 
        airport_stats=airport_stats,  # Passing the breakdown.
        buffer_mins=buffer_mins
    )

def find_optimal_departure(
    origin: str, 
    destination: str, 
    flight_time_epoch: int, 
    has_bags: bool, 
    is_precheck: bool, 
    risk_threshold: float = 90.0
) -> Tuple[Optional[int], Optional[int]]:
    """
    Performs a backward-scanning search to find the 'Latest Safe' and 
    'Drop Dead' departure timestamps.
    """
    current_best_time: Optional[int] = None
    drop_dead_time: Optional[int] = None
    
    # Start scanning 45 mins before flight time and walk backwards for ~7.5 hours.
    start_scan = flight_time_epoch - (45 * 60) 
    now_epoch = int(time.time())
    
    for i in range(30): 
        test_time = start_scan - (i * 900) # 15 minute steps.
        
        # Guardrail: Don't suggest departure times in the past.
        if test_time < (now_epoch + 300):
            break 
        
        res = run_full_analysis(origin, destination, test_time, flight_time_epoch, has_bags, is_precheck)
        if res is None: 
            continue 
            
        prob = res['success_probability']
        
        # Identify the first timestamp (Latest) that satisfies the risk tolerance.
        if prob >= risk_threshold and current_best_time is None:
            current_best_time = test_time
            
        # Identify the absolute latest timestamp with a marginal (10%) success chance.
        if prob >= 10.0 and drop_dead_time is None:
            drop_dead_time = test_time
            
        # Optimization: Exit loop early if both thresholds are identified. 
        if current_best_time and drop_dead_time:
            break
            
    return current_best_time, drop_dead_time

# Local Unit Test Block.
if __name__ == "__main__":
    print("Testing Solver Orchestration...")
    test_flight_time = int(time.time()) + (5 * 3600)
    
    best_time, dead_time = find_optimal_departure(
        "Stony Brook University", "JFK Airport", test_flight_time, True, False
    )

    if best_time:
        print(f"✅ Safe Departure: {datetime.fromtimestamp(best_time).strftime('%I:%M %p')}")
    if dead_time:
        print(f"💀 Drop Dead: {datetime.fromtimestamp(dead_time).strftime('%I:%M %p')}")