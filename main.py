import sys
from traffic_engine import TrafficEngine
from weather_engine import WeatherEngine
from risk_engine import RiskEngine
from airport_engine import AirportEngine  
from datetime import datetime, timedelta
from visualizer import Visualizer

def get_timestamp(days=0, hours=0, minutes=0):
    # Generates a Unix timestamp for any point in the future.
    future_date = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes)
    return int(future_date.timestamp())

def run_assessment(origin, destination, buffer_mins):
    print(f"\n\033[94m[*] Initializing FlightRisk Assessment for {destination}...\033[0m")

    # Define departure time (when you leave home).
    scheduled_departure = get_timestamp(minutes=0) 
    
    # Initialize engines
    traffic = TrafficEngine()
    weather = WeatherEngine()
    risk = RiskEngine()
    airport = AirportEngine()  
    
    try:
        # Traffic and Weather simulation.
        traffic_data = {}
        for model in ["optimistic", "best_guess", "pessimistic"]:
            res = traffic.get_route(origin, destination, model, departure_time=scheduled_departure)
            if res is None:
                raise ValueError(f"Traffic Engine failed to retrieve {model} data.")
            traffic_data[model] = res
            
        route_polyline = traffic_data['best_guess'].get('polyline')
        if not route_polyline:
            raise ValueError("Could not retrieve route geometry for weather sampling.")
        
        weather_report = weather.get_route_weather(route_polyline)

        # Airport Simulation.
        print(f"\033[96m[*] Simulating Curb-to-Gate Time...\033[0m")
        
        # Estimate arrival at airport.
        # This ensures the 'Time of Day' multiplier is accurate for when you actually walk in.
        drive_time_seconds = traffic_data['best_guess']['seconds']
        est_arrival_at_airport = scheduled_departure + drive_time_seconds
        
        # Smart Airport Parser (Maps City/Keywords to Airport Codes).
        dest_upper = destination.upper()
        target_airport = "JFK" # Default to a Tier 1 Hub if unknown (Safety Net).
        
        keywords = {
            # Tier 1 Hub.
            "JFK": "JFK", "KENNEDY": "JFK", "NY": "JFK",
            "LGA": "LGA", "LAGUARDIA": "LGA",
            "EWR": "EWR", "NEWARK": "EWR",
            "LAX": "LAX", "LOS ANGELES": "LAX",
            "SFO": "SFO", "FRANCISCO": "SFO",
            "ORD": "ORD", "OHARE": "ORD", "CHICAGO": "ORD",
            "ATL": "ATL", "ATLANTA": "ATL",
            "DFW": "DFW", "DALLAS": "DFW",
            "DEN": "DEN", "DENVER": "DEN",
            "MIA": "MIA", "MIAMI": "MIA",
            "MCO": "MCO", "ORLANDO": "MCO",
            "LAS": "LAS", "VEGAS": "LAS",
            "SEA": "SEA", "SEATTLE": "SEA",
            "BOS": "BOS", "LOGAN": "BOS", "BOSTON": "BOS",
            "FLL": "FLL", "LAUDERDALE": "FLL", "HOLLYWOOD": "FLL", 
            
            # TIER 2 and 3.
            "BUR": "BUR", "BURBANK": "BUR",
            "PBI": "PBI", "PALM BEACH": "PBI",
            "RSW": "RSW", "MYERS": "RSW", "SOUTHWEST": "RSW",
            "ISP": "ISP", "ISLIP": "ISP", "MACARTHUR": "ISP"
        }

        # Scan the destination string for any of these keywords.
        for key, code in keywords.items():
            if key in dest_upper:
                target_airport = code
                break
        
        print(f"\033[96m    -> Detected Airport Profile: {target_airport}\033[0m")

        # Run the simulation.
        airport_processing_time = airport.get_total_airport_time(airport_code=target_airport, epoch_time=est_arrival_at_airport, has_bags=True, is_precheck=False, iterations=1000)

        # Risk analysis.
        final_report = risk.evaluate_trip(traffic_data, weather_report, airport_processing_time, buffer_mins)

        # Visualization.
        display_dashboard(origin, destination, buffer_mins, final_report, scheduled_departure)

        print(f"\n\033[96m[*] Generating Risk Profile Graph...\033[0m")
        viz = Visualizer()
        viz.plot_risk_profile(simulated_times=final_report['raw_data'], deadline=buffer_mins, p95_time=final_report['p95_eta'])
   
    except Exception as e:
        print(f"\n\033[91m[!] CRITICAL ERROR: {e}\033[0m")

def display_dashboard(origin, dest, buffer, report, departure_time):
    readable_time = datetime.fromtimestamp(departure_time).strftime('%I:%M %p')

    # ANSI Color Codes.
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    
    color = RED if report['risk'] in ["HIGH", "CRITICAL"] else GREEN
    
    print("\n" + "="*60)
    print(f"{BOLD}FLIGHT-RISK TERMINAL v2.0 (DOOR-TO-GATE){RESET}".center(68))
    print("="*60)
    print(f" ROUTE:     {origin} -> {dest}")
    print(f" DEPARTURE: {readable_time}")
    print(f" WINDOW:    {buffer} minutes total")
    print("-" * 60)
    
    print(f"{BOLD}STATISTICAL ANALYSIS RESULTS:{RESET}")
    print(f"  - Weather Multiplier: {report['multiplier']}x")
    print(f"  - Avg Total Time:     {report['avg_eta']} mins")
    print(f"  - 95% Safe Arrival:   {report['p95_eta']} mins")
    print(f"  - Volatility (Std):   {report['std_dev']} mins")
    
    # Highlight success prob metric.
    prob = report['success_probability']
    prob_color = GREEN if prob > 90 else YELLOW if prob > 75 else RED
    print(f"  - Success Probability: {BOLD}{prob_color}{prob}%{RESET}")

    # Calculate Safety Margin.
    margin = report['buffer_remaining']
    margin_sign = "+" if margin >= 0 else ""
    margin_color = GREEN if margin >= 15 else RED
    print(f"  - Safety Margin:      {margin_color}{margin_sign}{margin} mins{RESET} (vs 95% Worst Case)")
    
    print("-" * 60)
    print(f" FINAL RISK STATUS: {BOLD}{color}{report['risk']}{RESET}")
    
    if report['risk'] != "LOW":
        rec_time = abs(int(margin)) + 15
        print(f"{RED}{BOLD} RECOMMENDATION: High risk of missing flight!{RESET}")
        print(f"{RED} ADVICE: Leave {rec_time} mins earlier than planned.{RESET}")
    else:
        print(f"{GREEN} RECOMMENDATION: You are safe to leave at this time.{RESET}")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Test Case
    run_assessment("3160 Skillman Ave, Oceanside NY", "JFK", 150)