import sys
import time
import database
from traffic_engine import TrafficEngine
from weather_engine import WeatherEngine
from risk_engine import RiskEngine
from airport_engine import AirportEngine
from flight_engine import FlightEngine
from datetime import datetime, timedelta
from visualizer import Visualizer


def get_timestamp(days=0, hours=0, minutes=0):
    # Generates a Unix timestamp for future travel simulation.
    future_date = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes)
    return int(future_date.timestamp())

def run_silent_assessment(origin, destination, departure_epoch, flight_epoch, has_bags, is_precheck):
    # Runs a stripped-down simulation to find success probability without printing.
    traffic = TrafficEngine()
    weather = WeatherEngine()
    risk = RiskEngine()
    airport = AirportEngine()
    flight = FlightEngine()
    
    # Calculate the minutes available for this specific test run.
    total_buffer_mins = (flight_epoch - departure_epoch) / 60
    
    try:
        # Fetch Traffic.
        traffic_data = {}
        for model in ["optimistic", "best_guess", "pessimistic"]:
            traffic_data[model] = traffic.get_route(origin, destination, model, departure_time=departure_epoch)
        
        # Fetch Weather.
        route_polyline = traffic_data['best_guess'].get('polyline')
        weather_report = weather.get_route_weather(route_polyline)
        
        # Airport Processing.
        drive_time_sec = traffic_data['best_guess']['seconds']
        arrival_at_airport = departure_epoch + drive_time_sec
        
        # Simple airport code extractor.
        target_airport = "JFK"
        for key in ["LGA", "LAX", "EWR", "PBI", "BUR", "FLL", "RSW", "ISP"]:
            if key in destination.upper(): target_airport = key

        # Low iterations (500) for faster search performance.
        airport_times = airport.get_total_airport_time(target_airport, arrival_at_airport, has_bags, is_precheck, iterations=1000)

        # Return Probability.
        report = risk.evaluate_trip(traffic_data, weather_report, airport_times, total_buffer_mins)
        return report['success_probability']
    except Exception as e:
        # If the API fails, print why.
        print(f"\033[91m[!] Silent Assessment Failed: {e}\033[0m")
        return 0.0

def find_optimal_departure(origin, destination, flight_time_epoch, has_bags, is_precheck):
    # Searches the timeline for the Drop-Dead and Certainty windows.
    print(f"\n\033[94m[*] Analyzing timeline for flight with gate closing at {datetime.fromtimestamp(flight_time_epoch).strftime('%I:%M %p')}...\033[0m")
    now = int(datetime.now().timestamp())
    
    drop_dead_time = None
    certainty_time = None
    highest_prob_seen = 0.0
    
    for mins_before in range(45, 360, 15):
        test_dep = flight_time_epoch - (mins_before * 60)
        
        # If the scanner tries to check a time in the past, force it to check 'now' instead.
        is_past = False
        if test_dep < now:
            test_dep = now
            is_past = True 
            
        # Pause for 0.1s to prevent API connection errors.
        time.sleep(0.1)
        
        prob = run_silent_assessment(origin, destination, test_dep, flight_time_epoch, has_bags, is_precheck)
        
        # Track the best probability found so far.
        if prob > highest_prob_seen:
            highest_prob_seen = prob

        # Capture Drop-Dead Time (> 10%).
        if drop_dead_time is None and prob > 10.0:
            drop_dead_time = test_dep

        # Capture Certainty Time (> 95%).
        if certainty_time is None and prob >= 95.0:
            certainty_time = test_dep
            print(f"    [✓] Certainty Window: {datetime.fromtimestamp(certainty_time).strftime('%I:%M %p')}")
            break 

        
        # If we just checked 'now', we can't look further back. Stop scanning.
        if is_past:
            break

    # Reporting. 
    if certainty_time is None:
        print(f"    \033[93m[!] Warning: 95% Certainty unreachable. Max possible: {highest_prob_seen}%\033[0m")
        
    if drop_dead_time is None:
        print(f"    \033[91m[!] Alert: No viable 'Drop-Dead' window found.\033[0m")
            
    return certainty_time, drop_dead_time

def run_assessment(origin, destination, departure_time, flight_time, has_bags, is_precheck, safe_time=None, dead_time=None, gate_deadline=None):
    # The full reporting engine with visualization and dashboard output.
    buffer_mins = (flight_time - departure_time) / 60
    
    print(f"\n\033[94m[*] Generating Comprehensive Report for {destination}...\033[0m")

    # Initialize engines.
    traffic = TrafficEngine()
    weather = WeatherEngine()
    risk = RiskEngine()
    airport = AirportEngine()  
    
    try:
        # Traffic and Weather simulation.
        traffic_data = {}
        for model in ["optimistic", "best_guess", "pessimistic"]:
            res = traffic.get_route(origin, destination, model, departure_time=departure_time)
            traffic_data[model] = res
            
        route_polyline = traffic_data['best_guess'].get('polyline')
        weather_report = weather.get_route_weather(route_polyline)

        # Airport Simulation.
        print(f"\033[96m[*] Calculating Curb-to-Gate Stochastic Model...\033[0m")
        drive_time_seconds = traffic_data['best_guess']['seconds']
        est_arrival_at_airport = departure_time + drive_time_seconds
        
        # Smart Airport Parser.
        dest_upper = destination.upper()
        target_airport = "JFK" 
        keywords = {
            "JFK": "JFK", "KENNEDY": "JFK", "LGA": "LGA", "EWR": "EWR", 
            "LAX": "LAX", "SFO": "SFO", "ORD": "ORD", "ATL": "ATL", 
            "MIA": "MIA", "MCO": "MCO", "FLL": "FLL", "BUR": "BUR", 
            "PBI": "PBI", "RSW": "RSW", "ISP": "ISP"
        }

        for key, code in keywords.items():
            if key in dest_upper:
                target_airport = code
                break
        
        # Execute Stochastic Modeling.
        airport_processing_time = airport.get_total_airport_time(
            airport_code=target_airport, 
            epoch_time=est_arrival_at_airport, 
            has_bags=has_bags, 
            is_precheck=is_precheck, 
            iterations=1000
        )

        # Risk Analysis.
        final_report = risk.evaluate_trip(traffic_data, weather_report, airport_processing_time, buffer_mins)
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
    safe_dep, dead_dep = find_optimal_departure(user_origin, user_dest, flight_time, has_bags, is_precheck)

    print(f"\033[90m[*] Logging trip data to history...\033[0m")
    
    # We want to log the stats for the SAFE departure time (our recommendation).
    # If no safe time exists, we log the stats to show why it failed.
    log_time = safe_dep if safe_dep else int(datetime.now().timestamp())
    
    # Briefly calculate stats for this specific time so we can save them.
    # We create temporary engines just for this data capture.
    temp_traffic = TrafficEngine()
    temp_weather = WeatherEngine()
    temp_risk = RiskEngine()
    temp_airport = AirportEngine()
    
    # Get the raw numbers.
    t_data = temp_traffic.get_route(user_origin, user_dest, "best_guess", departure_time=log_time)
    w_data = temp_weather.get_route_weather(t_data['polyline'])
    
    dest_upper = user_dest.upper()
    log_airport = "JFK" # Fallback.
    airport_map = {
        "LGA": "LGA", "LAGUARDIA": "LGA",
        "EWR": "EWR", "NEWARK": "EWR",
        "JFK": "JFK", "KENNEDY": "JFK",
        "LAX": "LAX", "SFO": "SFO", "ORD": "ORD",
        "MIA": "MIA", "MCO": "MCO", "FLL": "FLL",
        "ATL": "ATL", "PBI": "PBI", "RSW": "RSW",
        "BUR": "BUR", "ISP": "ISP"
    }
    for key, code in airport_map.items():
        if key in dest_upper:
            log_airport = code
            break
    
    a_time = temp_airport.get_total_airport_time(log_airport, log_time + t_data['seconds'], has_bags, is_precheck, iterations=1000)
    
    # Get final report for the log.
    log_report = temp_risk.evaluate_trip({'best_guess': t_data, 'optimistic': t_data, 'pessimistic': t_data}, w_data, a_time, (flight_time - log_time)/60)
    
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