import time
import asyncio
import aiohttp
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

# Engine Imports
from traffic_engine import TrafficEngine
from weather_engine import WeatherEngine
from risk_engine import RiskEngine
from airport_engine import AirportEngine

# Initialize Engines
traffic_engine = TrafficEngine()
weather_engine = WeatherEngine()
risk_engine = RiskEngine()
airport_engine = AirportEngine()

async def run_full_analysis(
    origin: str, 
    destination: str, 
    departure_time: int, 
    flight_time: int, 
    has_bags: bool, 
    is_precheck: bool,
    buffer_minutes: int = 0  
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the Async data flow between all engines.
    """
    
    effective_deadline = flight_time - (15 * 60) - (buffer_minutes * 60)
    buffer_mins: float = (effective_deadline - departure_time) / 60

    # Create a single Shared Session for all requests.
    async with aiohttp.ClientSession() as session:
        
        # STEP 1: ASYNC TRAFFIC FETCH 
        # TrafficEngine handles its own requests, but we await the result here.
        traffic_metrics = await traffic_engine.get_traffic_metrics(
            origin, destination, departure_time
        )
        
        if not traffic_metrics or 'polyline' not in traffic_metrics:
            return None

        # STEP 2: ASYNC WEATHER FETCH 
        route_polyline = traffic_metrics['polyline']

        weather_report = await weather_engine.get_route_weather(route_polyline, session)
        
        if weather_report is None:
            return None

    # STEP 3: SYNC AIRPORT SIMULATION 
    drive_time_seconds = traffic_metrics['mode'] * 60 
    est_arrival = departure_time + drive_time_seconds
    
    target_airport = "JFK" 
    if "LGA" in destination.upper(): target_airport = "LGA"
    elif "EWR" in destination.upper(): target_airport = "EWR"

    checkin_sim = airport_engine.simulate_checkin(target_airport, has_bags, est_arrival, iterations=1000)
    security_sim = airport_engine.simulate_security(target_airport, est_arrival, is_precheck, iterations=1000)
    walk_sim = airport_engine.simulate_walk(target_airport, iterations=1000)
    
    total_airport_delays = checkin_sim + security_sim + walk_sim
    
    airport_stats = {
        "checkin": float(np.mean(checkin_sim)),
        "security": float(np.mean(security_sim)),
        "walk": float(np.mean(walk_sim))
    }

    # STEP 4: ADAPTER LAYER 
    formatted_traffic = {
        "optimistic": {"seconds": traffic_metrics['min'] * 60},
        "best_guess": {"seconds": traffic_metrics['mode'] * 60},
        "pessimistic": {"seconds": traffic_metrics['max'] * 60}
    }

    # STEP 5: FINAL EVALUATION 
    return risk_engine.evaluate_trip(
        traffic_results=formatted_traffic, 
        weather_report=weather_report, 
        airport_delays=total_airport_delays, 
        airport_stats=airport_stats, 
        buffer_mins=buffer_mins
    )

async def find_optimal_departure(
    origin: str, 
    destination: str, 
    flight_time_epoch: int, 
    has_bags: bool, 
    is_precheck: bool, 
    risk_threshold: float = 90.0,
    buffer_minutes: int = 0  
) -> Tuple[Optional[int], Optional[int]]:
    """
    High-Precision Solver (Async).
    """
    hard_deadline_offset = (15 + buffer_minutes) * 60
    start_scan = flight_time_epoch - hard_deadline_offset 
    
    step_seconds = 300 
    max_slots = 48 
    
    now_epoch = int(time.time())
    memo = {}

    async def get_prob_for_slot(i: int) -> float:
        if i in memo: return memo[i]
        
        test_time = start_scan - (i * step_seconds)
        
        if test_time < (now_epoch + 300): 
            return 0.0
            
        res = await run_full_analysis(
            origin, destination, test_time, flight_time_epoch, 
            has_bags, is_precheck, buffer_minutes
        )
        
        prob = res['success_probability'] if res else 0.0
        memo[i] = prob
        return prob

    # Binary Search 1
    optimal_idx = None
    low, high = 0, max_slots

    while low <= high:
        mid = (low + high) // 2
        p = await get_prob_for_slot(mid)
        
        if p >= risk_threshold:
            optimal_idx = mid   
            high = mid - 1      
        else:
            low = mid + 1       

    # Binary Search 2
    drop_dead_idx = None
    search_limit = optimal_idx if optimal_idx is not None else max_slots
    low, high = 0, search_limit
    
    while low <= high:
        mid = (low + high) // 2
        p = await get_prob_for_slot(mid)
        
        if p >= 10.0:
            drop_dead_idx = mid 
            high = mid - 1      
        else:
            low = mid + 1

    opt_time = (start_scan - (optimal_idx * step_seconds)) if optimal_idx is not None else None
    dead_time = (start_scan - (drop_dead_idx * step_seconds)) if drop_dead_idx is not None else None
    
    return opt_time, dead_time

# Local Unit Test Block
if __name__ == "__main__":
    print("Testing Async Solver Orchestration...")
    
    async def test_run():
        test_flight_time = int(time.time()) + (5 * 3600)
        
        start = time.time()
        best_time, dead_time = await find_optimal_departure(
            "Stony Brook University, NY", "JFK Airport, NY", test_flight_time, True, False, 
            buffer_minutes=30  
        )
        duration = time.time() - start

        if best_time:
            print(f"✅ Safe Departure: {datetime.fromtimestamp(best_time).strftime('%I:%M %p')}")
        if dead_time:
            print(f"💀 Drop Dead: {datetime.fromtimestamp(dead_time).strftime('%I:%M %p')}")
        
        print(f"Calculation Time: {duration:.2f} seconds")

    asyncio.run(test_run())