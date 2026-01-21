import sys
import asyncio
import time
import aiohttp
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Optional, Dict, Any

# Internal Imports
import database
from solver import Solver 
from visualizer import Visualizer
from flight_engine import FlightEngine

# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
GRAY = "\033[90m"

def display_dashboard(
    origin: str, 
    dest: str, 
    report: Dict[str, Any], 
    departure_time: int, 
    safe_time: Optional[int], 
    dead_time: Optional[int], 
    gate_deadline: int
) -> None:
    """Renders a data-driven summary to the terminal."""
    readable_dep = datetime.fromtimestamp(departure_time).strftime('%I:%M %p')
    gate_str = datetime.fromtimestamp(gate_deadline).strftime('%I:%M %p')

    prob = report['success_probability']
    prob_color = GREEN if prob > 90 else YELLOW if prob > 75 else RED
    
    risk_status = report.get('risk', 'UNKNOWN')
    risk_color = RED if risk_status in ["HIGH", "CRITICAL"] else GREEN

    print("\n" + "="*60)
    print(f"{BOLD}FLIGHT-RISK TERMINAL v3.0 (ASYNC KERNEL){RESET}".center(68))
    print("="*60)
    print(f" {BOLD}ROUTE:{RESET}     {origin} -> {dest}")
    print(f" {BOLD}DEPARTURE:{RESET} {readable_dep}")
    print(f" {BOLD}DEADLINE:{RESET}  {gate_str} (Gate Closure)")    
    
    print(f"\n{BOLD}STATISTICAL INSIGHTS:{RESET}")
    print(f"  - Weather Impact:     {report['multiplier']}x")
    print(f"  - Avg Total Time:     {report['avg_eta']} mins")
    print(f"  - 95% Safe Arrival:   {report['p95_eta']} mins")
    print(f"  - Success Probability: {BOLD}{prob_color}{prob}%{RESET}")

    margin = report['buffer_remaining']
    margin_color = GREEN if margin >= 15 else RED
    print(f"  - Safety Margin:      {margin_color}{margin} mins{RESET}")
    
    print("-" * 60)
    print(f"{BOLD}LOGISTICS ADVICE:{RESET}")
    safe_str = datetime.fromtimestamp(safe_time).strftime('%I:%M %p') if safe_time else "UNREACHABLE"
    print(f"  - {GREEN}Recommended Departure: {safe_str} (95% Probability){RESET}")
    
    dead_str = datetime.fromtimestamp(dead_time).strftime('%I:%M %p') if dead_time else "PAST DEADLINE"
    print(f"  - {RED}Drop-Dead Time:        {dead_str} (<10% Probability){RESET}")
    print("-" * 60)
    
    print(f" FINAL STATUS: {BOLD}{risk_color}{risk_status}{RESET} RISK")
    print("="*60 + "\n")

async def run_cli():
    # Initialize components
    try:
        database.init_db()
    except Exception:
        pass 

    # INSTANTIATE CLASSES
    flight_engine = FlightEngine() 
    solver_instance = Solver() # Created instance of Solver class
    
    print(f"\n{BOLD}{CYAN}FLIGHT-RISK: PREDICTIVE LOGISTICS ENGINE{RESET}")
    
    # 1. User Input
    user_origin = input(f"{BOLD}Enter Home/Office Address:{RESET} ")
    user_flight_num = input(f"{BOLD}Enter Flight Number (e.g., DL482):{RESET} ").upper().strip()
    
    # 2. Async Session Management
    async with aiohttp.ClientSession() as session:
        print(f"{GRAY}[*] Fetching flight data...{RESET}")
        
        # Pass session to flight engine
        flight_info = await flight_engine.get_flight_details(session, user_flight_num)
        
        if not flight_info:
            print(f"{RED}[!] CRITICAL: Could not retrieve flight data for {user_flight_num}.{RESET}")
            return

        user_dest = flight_info['origin_airport'] 
        gate_time = flight_info['dep_ts'] - 900 
            
        print(f"{GREEN}Confirmed: {user_flight_num} departs {user_dest} at {datetime.fromtimestamp(flight_info['dep_ts']).strftime('%I:%M %p')}{RESET}")

        has_bags = input(f" Checking bags? (y/n): ").lower() == 'y'
        is_precheck = input(f" TSA PreCheck? (y/n): ").lower() == 'y'
        
        # 3. Optimal Window Scan
        # Note: solver.find_optimal_departure manages its own session internally,
        # so we don't need to pass 'session' here.
        print(f"{GRAY}[*] Scanning for optimal departure windows...{RESET}")
        safe_dep, dead_dep = await solver_instance.find_optimal_departure(
            user_origin, user_dest, flight_info['dep_ts'], has_bags, is_precheck
        )

        # 4. Full Analysis
        # Note: Your solver.run_full_analysis DOES require 'session' passed in.
        print(f"{CYAN}[*] Generating Stochastic Model for {user_dest}...{RESET}")
        current_time = int(time.time())
        
        final_report = await solver_instance.run_full_analysis(
            session, user_origin, user_dest, current_time, 
            flight_info['dep_ts'], has_bags, is_precheck
        )

        if not final_report:
            print(f"{RED}[!] Simulation failed. Check API connectivity.{RESET}")
            return

        # 5. Display Results
        display_dashboard(user_origin, user_dest, final_report, current_time, safe_dep, dead_dep, gate_time)

        # 6. Visualization
        print(f"{CYAN}[*] Rendering Risk Profile Visualization...{RESET}")
        viz = Visualizer()
        
        total_budget = final_report['p95_eta'] + final_report['buffer_remaining']
        
        fig = viz.plot_risk_profile(
            simulated_times=final_report['raw_data'], 
            deadline=total_budget, 
            p95_time=final_report['p95_eta']
        )
        
        # Save to file instead of popup (more reliable for async CLI)
        filename = f"risk_profile_{user_flight_num}.png"
        fig.savefig(filename)
        print(f"{GREEN}[✓] Plot saved to {filename}{RESET}")

if __name__ == "__main__":
    try:
        asyncio.run(run_cli())
    except KeyboardInterrupt:
        print("\n\n[!] Operation cancelled by user.")
        sys.exit()