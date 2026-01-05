import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any

# Internal Imports.
import database
import solver
from visualizer import Visualizer
from flight_engine import FlightEngine

# ANSI Color Codes For Terminal.
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
    """
    Renders a data-driven summary to the terminal.
    """
    readable_dep = datetime.fromtimestamp(departure_time).strftime('%I:%M %p')
    gate_str = datetime.fromtimestamp(gate_deadline).strftime('%I:%M %p')

    # Color-code the success probability.
    prob = report['success_probability']
    prob_color = GREEN if prob > 90 else YELLOW if prob > 75 else RED
    
    # Color-code the risk status.
    risk_status = report.get('risk', 'UNKNOWN')
    risk_color = RED if risk_status in ["HIGH", "CRITICAL"] else GREEN

    print("\n" + "="*60)
    print(f"{BOLD}FLIGHT-RISK TERMINAL v2.0{RESET}".center(68))
    print("="*60)
    print(f" {BOLD}ROUTE:{RESET}     {origin} -> {dest}")
    print(f" {BOLD}DEPARTURE:{RESET} {readable_dep}")
    print(f" {BOLD}DEADLINE:{RESET}  {gate_str} (Gate Closure)")    
    
    print(f"\n{BOLD}STATISTICAL INSIGHTS:{RESET}")
    print(f"  - Weather Impact:     {report['multiplier']}x")
    print(f"  - Avg Total Time:     {report['avg_eta']} mins")
    print(f"  - 95% Safe Arrival:   {report['p95_eta']} mins")
    print(f"  - Success Probability: {BOLD}{prob_color}{prob}%{RESET}")

    # Display Safety Margin relative to the 95th percentile.
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

def run_assessment(
    origin: str, 
    destination: str, 
    departure_time: int, 
    flight_time: int, 
    has_bags: bool, 
    is_precheck: bool, 
    safe_time: Optional[int] = None, 
    dead_time: Optional[int] = None
) -> None:
    """
    Orchestrates the analysis and launches the Visualizer.
    """
    print(f"{CYAN}[*] Generating Stochastic Model for {destination}...{RESET}")
    
    try:
        # Execute Full Analysis using solver.
        final_report = solver.run_full_analysis(origin, destination, departure_time, flight_time, has_bags, is_precheck)

        if not final_report:
            print(f"{RED}[!] Simulation failed. Check API connectivity.{RESET}")
            return

        # Print Terminal Dashboard.
        display_dashboard(origin, destination, final_report, departure_time, safe_time, dead_time, flight_time)

        # Generate Kernel Density Estimation Plot.
        print(f"{CYAN}[*] Rendering Risk Profile Visualization...{RESET}")
        viz = Visualizer()
        viz.plot_risk_profile(simulated_times=final_report['raw_data'], deadline=(flight_time - departure_time) / 60, p95_time=final_report['p95_eta'])
   
    except Exception as e:
        print(f"\n{RED}[!] CRITICAL ERROR: {e}{RESET}")

# Local Unit Test Block.
if __name__ == "__main__":
    database.init_db() 
    flight_engine = FlightEngine() 
    
    print(f"\n{BOLD}{CYAN}FLIGHT-RISK: PREDICTIVE LOGISTICS ENGINE{RESET}")
    
    # User Input Layer.
    user_origin = input(f"{BOLD}Enter Home/Office Address:{RESET} ")
    user_flight_num = input(f"{BOLD}Enter Flight Number (e.g., B66):{RESET} ").upper().strip()
    
    # Fetch Live Flight Data.
    print(f"{GRAY}[*] Fetching flight data...{RESET}")
    flight_info = flight_engine.get_flight_details(user_flight_num)
    
    if not flight_info:
        print(f"{RED}[!] CRITICAL: Could not retrieve flight data for {user_flight_num}.{RESET}")
        sys.exit()

    # Apply 15-minute gate closure buffer.
    user_dest = flight_info['origin_airport'] 
    gate_time = flight_info['dep_ts'] - 900 
        
    print(f"{GREEN}Confirmed: {user_flight_num} departs {user_dest} at {datetime.fromtimestamp(flight_info['dep_ts']).strftime('%I:%M %p')}{RESET}")

    has_bags = input(f" Checking bags? (y/n): ").lower() == 'y'
    is_precheck = input(f" TSA PreCheck? (y/n): ").lower() == 'y'
    
    # Find Optimal Windows using solver.
    print(f"{GRAY}[*] Scanning for optimal departure windows...{RESET}")
    safe_dep, dead_dep = solver.find_optimal_departure(user_origin, user_dest, gate_time, has_bags, is_precheck)

    # Persistence (Database Logging)
    print(f"{GRAY}[*] Logging trip to history...{RESET}")
    
    # Log the 'Safe Departure' result as our primary recommendation.
    log_time = safe_dep if safe_dep else int(time.time())
    log_report = solver.run_full_analysis(user_origin, user_dest, log_time, gate_time, has_bags, is_precheck)
    
    if log_report:
        database.log_trip(
            flight_num=user_flight_num,
            origin=user_origin,
            dest=user_dest,
            multiplier=log_report['multiplier'],
            suggested_time=safe_dep,
            probability=log_report['success_probability'],
            risk_status=log_report.get('risk', 'UNKNOWN')
        )

    # Final Assessment.
    # Defaulting current evaluation to 'Now' for the dashboard display.
    run_assessment(user_origin, user_dest, int(time.time()), gate_time, has_bags, is_precheck, safe_dep, dead_dep)