import time
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

# Import sibling modules from the same 'src' package.
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
    is_precheck: bool,
    buffer_minutes: int = 0  
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the data flow between all engines to perform a single 
    point-in-time risk analysis.
    """
    # Initialize Engines.
    traffic = TrafficEngine()
    weather = WeatherEngine()
    risk = RiskEngine()
    airport = AirportEngine()  
    
    # Adjust flight_time to account for 'Time to Kill' buffer.
    # We treat the buffer as if the flight is earlier, creating a safety margin.
    effective_deadline = flight_time - (15 * 60) - (buffer_minutes * 60)
    
    # Calculate the total available time window (in minutes).
    buffer_mins: float = (effective_deadline - departure_time) / 60

    # 1. Gather Traffic Data.
    traffic_data: Dict[str, Any] = {}
    for model in ["optimistic", "best_guess", "pessimistic"]:
        route_res = traffic.get_route(origin, destination, model, departure_time=departure_time)
        
        if route_res is None:
            return None 
        
        traffic_data[model] = route_res
    
    # 2. Gather Weather Data (based on the route polyline).
    route_polyline = traffic_data['best_guess'].get('polyline')
    weather_report = weather.get_route_weather(route_polyline)
    if weather_report is None:
        return None

    # 3. Simulate Airport Queues (Check-in + TSA + Walk).
    drive_time_seconds = traffic_data['best_guess']['seconds']
    est_arrival = departure_time + drive_time_seconds
    
    # Heuristic to detect airport code from destination string.
    target_airport = "JFK" 
    if "LGA" in destination.upper(): target_airport = "LGA"
    elif "EWR" in destination.upper(): target_airport = "EWR"

    checkin_sim = airport.simulate_checkin(target_airport, has_bags, est_arrival, iterations=1000)
    security_sim = airport.simulate_security(target_airport, est_arrival, is_precheck, iterations=1000)
    walk_sim = airport.simulate_walk(target_airport, iterations=1000)
    
    # Sum the stochastic arrays to get total airport time distributions.
    total_airport_delays = checkin_sim + security_sim + walk_sim
    
    airport_stats = {
        "checkin": float(checkin_sim.mean()),
        "security": float(security_sim.mean()),
        "walk": float(walk_sim.mean())
    }

    # 4. Final Stochastic Evaluation (Monte Carlo).
    return risk.evaluate_trip(
        traffic_results=traffic_data, 
        weather_report=weather_report, 
        airport_delays=total_airport_delays, 
        airport_stats=airport_stats,
        buffer_mins=buffer_mins
    )

def find_optimal_departure(
    origin: str, 
    destination: str, 
    flight_time_epoch: int, 
    has_bags: bool, 
    is_precheck: bool, 
    risk_threshold: float = 90.0,
    buffer_minutes: int = 0  
) -> Tuple[Optional[int], Optional[int]]:
    """
    Performs a backward-scanning search to find the 'Latest Safe' and 
    'Drop Dead' departure timestamps.
    """
    current_best_time: Optional[int] = None
    drop_dead_time: Optional[int] = None
    
    # Identify the 'Hard Deadline' (Gate closure + User's custom buffer).
    # This ensures the search starts at the absolute latest the user can arrive.
    hard_deadline_offset = (15 + buffer_minutes) * 60
    start_scan = flight_time_epoch - hard_deadline_offset 
    
    now_epoch = int(time.time())
    
    # Scan backwards for 8 hours (32 steps of 15 mins) to ensure we find a viable time.
    for i in range(32): 
        test_time = start_scan - (i * 900) 
        
        # Guardrail: Don't suggest departure times in the past.
        if test_time < (now_epoch + 300):
            break 
        
        res = run_full_analysis(
            origin, 
            destination, 
            test_time, 
            flight_time_epoch, 
            has_bags, 
            is_precheck,
            buffer_minutes=buffer_minutes 
        )
        if res is None: 
            continue 
            
        prob = res['success_probability']
        
        # Identify the first timestamp (Latest) that satisfies the risk tolerance.
        if prob >= risk_threshold and current_best_time is None:
            current_best_time = test_time
            
        # Identify the absolute latest timestamp with a marginal (10%) success chance.
        if prob >= 10.0 and drop_dead_time is None:
            drop_dead_time = test_time
            
        # Optimization: Exit loop early if we've found a safe time that handles the buffer. 
        if current_best_time:
            break
            
    return current_best_time, drop_dead_time

# Local Unit Test Block.
if __name__ == "__main__":
    print("Testing Solver Orchestration with 30m Buffer...")
    test_flight_time = int(time.time()) + (5 * 3600)
    
    best_time, dead_time = find_optimal_departure(
        "Stony Brook University", "JFK Airport", test_flight_time, True, False, 
        buffer_minutes=30  
    )

    if best_time:
        print(f"✅ Safe Departure (w/ 30m buffer): {datetime.fromtimestamp(best_time).strftime('%I:%M %p')}")
    if dead_time:
        print(f"💀 Drop Dead: {datetime.fromtimestamp(dead_time).strftime('%I:%M %p')}")