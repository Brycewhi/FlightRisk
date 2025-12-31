import sys
from traffic_engine import TrafficEngine
from weather_engine import WeatherEngine
from risk_engine import RiskEngine
from airport_engine import AirportEngine
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
        airport_times = airport.get_total_airport_time(target_airport, arrival_at_airport, has_bags, is_precheck, iterations=500)

        # Return Probability.
        report = risk.evaluate_trip(traffic_data, weather_report, airport_times, total_buffer_mins)
        return report['success_probability']
    except:
        return 0.0

def find_optimal_departure(origin, destination, flight_time_epoch, has_bags, is_precheck):
    # Searches the timeline for the Drop-Dead and Certainty windows.
    print(f"\n\033[94m[*] Analyzing timeline for flight at {datetime.fromtimestamp(flight_time_epoch).strftime('%I:%M %p')}...\033[0m")
    now = int(datetime.now().timestamp())
    drop_dead_time = None
    certainty_time = None
    
    # Scan from 5 hours before flight down to 45 mins before (10-min steps).
    for mins_before in range(300, 45, -10):
        test_dep = flight_time_epoch - (mins_before * 60)
        
        # Skip any time that is already in the past. 
        if test_dep < now:
            continue
        prob = run_silent_assessment(origin, destination, test_dep, flight_time_epoch, has_bags, is_precheck)
        
        # Capture Drop-Dead Time (Success rises above 1%).
        if drop_dead_time is None and prob > 1.0:
            drop_dead_time = test_dep
            print(f"    [!] Drop-Dead Moment: {datetime.fromtimestamp(drop_dead_time).strftime('%I:%M %p')}")

        # Capture Certainty Time (Success hits 95%).
        if certainty_time is None and prob >= 95.0:
            certainty_time = test_dep
            print(f"    [✓] Certainty Window: {datetime.fromtimestamp(certainty_time).strftime('%I:%M %p')}")
            break # Optimization found.
            
    return certainty_time, drop_dead_time

def run_assessment(origin, destination, departure_time, flight_time, has_bags, is_precheck, safe_time=None, dead_time=None):
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

        # Visualization and Dashboard.
        display_dashboard(origin, destination, buffer_mins, final_report, departure_time, safe_time, dead_time)

        print(f"\n\033[96m[*] Rendering Risk Profile Visualization...\033[0m")
        viz = Visualizer()
        viz.plot_risk_profile(
            simulated_times=final_report['raw_data'], 
            deadline=buffer_mins, 
            p95_time=final_report['p95_eta']
        )
   
    except Exception as e:
        print(f"\n\033[91m[!] CRITICAL ERROR: {e}\033[0m")

def display_dashboard(origin, dest, buffer, report, departure_time, safe_time, dead_time):
    # Prints the final data-driven summary to the terminal.
    readable_time = datetime.fromtimestamp(departure_time).strftime('%I:%M %p')

    # Format the advice times
    safe_str = datetime.fromtimestamp(safe_time).strftime('%I:%M %p') if safe_time else "N/A"
    dead_str = datetime.fromtimestamp(dead_time).strftime('%I:%M %p') if dead_time else "N/A"

    RESET, BOLD, GREEN, YELLOW, RED = "\033[0m", "\033[1m", "\033[92m", "\033[93m", "\033[91m"
    color = RED if report['risk'] in ["HIGH", "CRITICAL"] else GREEN
    
    print("\n" + "="*60)
    print(f"{BOLD}FLIGHT-RISK TERMINAL v2.0 (INTELLIGENT){RESET}".center(68))
    print("="*60)
    print(f" ROUTE:     {origin} -> {dest}")
    print(f" DEPARTURE: {readable_time} (Current Simulation)")
    print(f" WINDOW:    {round(buffer, 1)} minutes total budget")
    print("-" * 60)
    
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
    print(f"  - {GREEN}Certainty Time:  {safe_str} (95% Probability){RESET}")
    print(f"  - {RED}Drop-Dead Time:  {dead_str} (<1% Probability){RESET}")
    print("-" * 60)
    
    print(f" FINAL STATUS: {BOLD}{color}{report['risk']}{RESET} RISK")
    print("="*60 + "\n")

# Interactive CLI.
if __name__ == "__main__":
    print("\n\033[1m" + "✈️  FLIGHTRISK: PREDICTIVE LOGISTICS ENGINE" + "\033[0m")
    
    user_origin = input("Enter Home/Office Address: ")
    user_dest = input("Enter Destination Airport: ") 
    
    print("\n[Travel Profile]")
    has_bags = input("  Checking bags? (y/n): ").lower() == 'y'
    is_precheck = input("  TSA PreCheck? (y/n): ").lower() == 'y'
    
    # Use current time (now) for the actual assessment
    now_epoch = int(datetime.now().timestamp())
    
    # Set flight time (e.g., 2 hours from now)
    flight_time = get_timestamp(hours=2)
    
    # Find the 'Safe' and 'Dead' times for advice.
    safe_dep, dead_dep = find_optimal_departure(user_origin, user_dest, flight_time, has_bags, is_precheck)
    
    # Run assesment for now.
    run_assessment(user_origin, user_dest, now_epoch, flight_time, has_bags, is_precheck)