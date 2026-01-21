import time
import asyncio
import aiohttp
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

from traffic_engine import TrafficEngine
from weather_engine import WeatherEngine
from risk_engine import RiskEngine
from airport_engine import AirportEngine

class Solver:
    """
    Orchestrator Class.
    Manages the lifecycle of a request across all engines.
    """
    def __init__(self):
        self.traffic = TrafficEngine()
        self.weather = WeatherEngine()
        self.risk = RiskEngine()
        self.airport = AirportEngine()

    async def run_full_analysis(
        self,
        session: aiohttp.ClientSession, 
        origin: str, 
        destination: str, 
        departure_time: int, 
        flight_time: int, 
        has_bags: bool, 
        is_precheck: bool,
        buffer_minutes: int = 0  
    ) -> Optional[Dict[str, Any]]:
        """
        Runs the full check for a SINGLE point in time.
        """
        
        effective_deadline = flight_time - (15 * 60) - (buffer_minutes * 60)
        buffer_mins = (effective_deadline - departure_time) / 60.0

        # STEP 1: ASYNC TRAFFIC
        traffic_metrics = await self.traffic.get_traffic_metrics(origin, destination, departure_time)
        if not traffic_metrics or 'polyline' not in traffic_metrics:
            return None

        # STEP 2: ASYNC WEATHER & AIRPORT (Parallel)
        # We fetch weather for the route AND airport wait times simultaneously
        route_polyline = traffic_metrics['polyline']
        
        weather_task = self.weather.get_route_weather(route_polyline, session)
        
        # Calculate arrival at airport (Departure + Drive Time)
        drive_time_sec = traffic_metrics['mode'] * 60
        est_arrival = departure_time + drive_time_sec
        
        # Determine Airport Code from Destination String
        target_airport = "JFK" 
        if "LGA" in destination.upper(): target_airport = "LGA"
        elif "EWR" in destination.upper(): target_airport = "EWR"
        elif "LHR" in destination.upper(): target_airport = "LHR"

        # Call the Hybrid Airport Engine (API + Math)
        airport_task = self.airport.get_total_airport_time(
            session, target_airport, est_arrival, has_bags, is_precheck
        )

        # Wait for both
        weather_report, (total_airport_delays, airport_stats) = await asyncio.gather(weather_task, airport_task)
        
        if weather_report is None:
            return None

        # STEP 3: ADAPTER LAYER 
        formatted_traffic = {
            "optimistic": {"seconds": traffic_metrics['min'] * 60},
            "best_guess": {"seconds": traffic_metrics['mode'] * 60},
            "pessimistic": {"seconds": traffic_metrics['max'] * 60}
        }

        # STEP 4: FINAL EVALUATION 
        return self.risk.evaluate_trip(
            traffic_results=formatted_traffic, 
            weather_report=weather_report, 
            airport_delays=total_airport_delays, 
            airport_stats=airport_stats, 
            buffer_mins=buffer_mins
        )

    async def find_optimal_departure(
        self,
        origin: str, 
        destination: str, 
        flight_time_epoch: int, 
        has_bags: bool, 
        is_precheck: bool, 
        risk_threshold: float = 90.0,
        buffer_minutes: int = 0  
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Sweeps backward in time to find the 'Optimal' and 'Drop Dead' times.
        """
        hard_deadline_offset = (15 + buffer_minutes) * 60
        start_scan = flight_time_epoch - hard_deadline_offset 
        
        step_seconds = 300 
        max_slots = 48 
        
        now_epoch = int(time.time())
        memo = {}

        async with aiohttp.ClientSession() as session:
            async def get_prob_for_slot(i: int) -> float:
                if i in memo: return memo[i]
                
                test_time = start_scan - (i * step_seconds)
                if test_time < (now_epoch + 300): return 0.0
                    
                res = await self.run_full_analysis(
                    session, origin, destination, test_time, flight_time_epoch, 
                    has_bags, is_precheck, buffer_minutes
                )
                
                prob = res['success_probability'] if res else 0.0
                memo[i] = prob
                return prob

            # Binary Search 1: Optimal Time (e.g. 90% success)
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

            # Binary Search 2: Drop Dead Time (e.g. 10% success)
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
        solver = Solver()
        test_flight_time = int(time.time()) + (5 * 3600)
        
        start = time.time()
        best_time, dead_time = await solver.find_optimal_departure(
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