import sys
import database
import solver
from visualizer import Visualizer
from flight_engine import FlightEngine
from datetime import datetime

def run_assessment(origin, destination, departure_time, flight_time, has_bags, is_precheck, safe_time=None, dead_time=None, gate_deadline=None):
    # The full reporting engine with visualization and dashboard output.
    buffer_mins = (flight_time - departure_time) / 60
    
    print(f"\n\033[94m[*] Generating Comprehensive Report for {destination}...\033[0m")
    
    try:
        # Execute Stochastic Modeling (delegated to Solver).
        print(f"\033[96m[*] Calculating Curb-to-Gate Stochastic Model...\033[0m")
        final_report = solver.run_full_analysis(origin, destination, departure_time, flight_time, has_bags, is_precheck)

        deadline_to_show = gate_deadline if gate_deadline else flight_time
        # Visualization and Dashboard.
        display_dashboard(origin, destination, buffer_mins, final_report, departure_time, safe_time, dead_time, deadline_to_show)

        print(f"\n\033[96m[*] Rendering Risk Profile Visualization...\033[0m")
        viz = Visualizer()
        viz.plot_risk_profile(
            simulated_times=final_report['raw_data'], 
            deadline=buffer_mins, 
            p95_time=final_report['p95_eta']
        )
   
    except Exception as e:
        print(f"\n\033[91m[!] CRITICAL ERROR: {e}\033[0m")

def display_dashboard(origin, dest, buffer, report, departure_time, safe_time, dead_time, gate_deadline):
    # Prints the final data-driven summary to the terminal.
    readable_time = datetime.fromtimestamp(departure_time).strftime('%I:%M %p')

    # Format the advice times
    safe_str = datetime.fromtimestamp(safe_time).strftime('%I:%M %p') if safe_time else "UNREACHABLE"
    dead_str = datetime.fromtimestamp(dead_time).strftime('%I:%M %p') if dead_time else "PAST DEADLINE"

    RESET, BOLD, GREEN, YELLOW, RED = "\033[0m", "\033[1m", "\033[92m", "\033[93m", "\033[91m"
    color = RED if report['risk'] in ["HIGH", "CRITICAL"] else GREEN
    
    print("\n" + "="*60)
    print(f"{BOLD}FLIGHT-RISK TERMINAL v2.0 {RESET}".center(68))
    print("="*60)
    print(f" ROUTE:     {origin} -> {dest}")
    print(f" DEPARTURE: {readable_time}")
    print(f" GATE CLOSES: {datetime.fromtimestamp(gate_deadline).strftime('%I:%M %p')} (Deadline)")    
    print(f"{BOLD}STATISTICAL INSIGHTS:{RESET}")
    print(f"  - Weather Multiplier: {report['multiplier']}x")
    print(f"  - Avg Total Time:     {report['avg_eta']} mins")
    print(f"  - 95% Safe Arrival:   {report['p95_eta']} mins")
    print(f"  - Volatility (Std):   {report['std_dev']} mins")
    
    prob = report['success_probability']
    prob_color = GREEN if prob > 90 else YELLOW if prob > 75 else RED
    print(f"  - Success Probability: {BOLD}{prob_color}{prob}%{RESET}")

    margin = report['buffer_remaining']
    margin_color = GREEN if margin >= 15 else RED
    print(f"  - Safety Margin:      {margin_color}{margin} mins{RESET} (vs 95% Safe)")
    
    print("-" * 60)
    print(f"{BOLD}LOGISTICS ADVICE:{RESET}")
    cert_color = GREEN if safe_time else YELLOW
    print(f"  - {cert_color}Certainty Time:  {safe_str} (95% Probability){RESET}")
    
    dead_color = RED if dead_time else BOLD + RED
    print(f"  - {dead_color}Drop-Dead Time:  {dead_str} (<10% Probability){RESET}")
    print("-" * 60)
    
    print(f" FINAL STATUS: {BOLD}{color}{report['risk']}{RESET} RISK")
    print("="*60 + "\n")


# Interactive CLI.
if __name__ == "__main__":
    print("\n\033[1m" + "FLIGHTRISK: PREDICTIVE LOGISTICS ENGINE" + "\033[0m")
    
    # Initialize the database.
    database.init_db()

    # Initialize the new FlightEngine.
    flight = FlightEngine()
    
    # Get origin of trip.
    user_origin = input("Enter Home/Office Address: ")
    
    # Get Flight Number.
    user_flight_num = input("Enter Flight Number (e.g., B66, AA100): ").upper().replace(" ", "")
    
    # Fetch Live Flight Data.
    flight_info = flight.get_flight_details(user_flight_num)
    
    if not flight_info:
        print("\n\033[91m[!] CRITICAL: Could not retrieve live flight data. Exiting.\033[0m")
        sys.exit()

    user_dest = flight_info['origin_airport'] 
    takeoff_time = flight_info['dep_ts']  
    flight_time = takeoff_time - 900 # Gates close 15 mins before on avg.
        
    print(f"\n\033[92m {user_flight_num} departs at {datetime.fromtimestamp(takeoff_time).strftime('%I:%M %p')}")
    print(f"    Gate Closes at {datetime.fromtimestamp(flight_time).strftime('%I:%M %p')}\033[0m")

    print("\n[Travel Profile]")
    has_bags = input("  Checking bags? (y/n): ").lower() == 'y'
    is_precheck = input("  TSA PreCheck? (y/n): ").lower() == 'y'
    
    # Departure mode selection. 
    print("\n[Departure Mode]")
    print("  1. Depart Now (Auto)")
    print("  2. Test a Specific Time (Manual)")
    mode = input("  Select 1 or 2: ")

    # Now vs custom logic.
    if mode == "2":
        time_input = input("  Enter your planned departure time (e.g., 04:30 AM): ")
        try:
            # Construct a full datetime string using today's date.
            date_part = datetime.now().strftime('%Y-%m-%d')
            full_str = f"{date_part} {time_input}"
            eval_departure = int(datetime.strptime(full_str, '%Y-%m-%d %I:%M %p').timestamp())
        except ValueError:
            print("\033[91m[!] Invalid time format. Defaulting to 'Now'.\033[0m")
            eval_departure = int(datetime.now().timestamp())
    else:
        eval_departure = int(datetime.now().timestamp())

    # Find safe time and dead time.
    safe_dep, dead_dep = solver.find_optimal_departure(user_origin, user_dest, flight_time, has_bags, is_precheck)

    print(f"\033[90m[*] Logging trip data to history...\033[0m")
    
    # We want to log the stats for the SAFE departure time (our recommendation).
    # If no safe time exists, we log the stats to show why it failed.
    log_time = safe_dep if safe_dep else int(datetime.now().timestamp())
    
    # Get the raw numbers using the Solver.
    log_report = solver.run_full_analysis(user_origin, user_dest, log_time, flight_time, has_bags, is_precheck)
    
    # Determine Risk Status Label.
    risk_label = "LOW"
    if log_report['success_probability'] < 95: risk_label = "HIGH"
    if log_report['success_probability'] < 75: risk_label = "CRITICAL"
    if safe_dep is None: risk_label = "UNREACHABLE"

    # SAVE TO DB.
    database.log_trip(
        flight_num=user_flight_num,
        origin=user_origin,
        dest=user_dest,
        multiplier=log_report['multiplier'],
        suggested_time=safe_dep,
        probability=log_report['success_probability'],
        risk_status=risk_label
    )    
    # Run the assessment.
    run_assessment(user_origin, user_dest, eval_departure, flight_time, has_bags, is_precheck, safe_dep, dead_dep, flight_time)