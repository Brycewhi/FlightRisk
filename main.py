import sys
from traffic_engine import TrafficEngine
from weather_engine import WeatherEngine
from risk_engine import RiskEngine
from datetime import datetime, timedelta

def get_timestamp(days=0, hours=0, minutes=0):
    # Generates a Unix timestamp for any point in the future. e.g. get_timestamp(days=2, hours=5) -> 2 days and 5 hours from now
    future_date = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes)
    
    # Google requires an integer
    return int(future_date.timestamp())


def run_assessment(origin, destination, buffer_mins):
    print(f"\n\033[94m[*] Initializing FlightRisk Assessment for {destination}...\033[0m")

    # Generate future timestamp
    scheduled_time = get_timestamp(minutes=90)
    # Initialize engines.
    traffic = TrafficEngine()
    weather = WeatherEngine()
    risk = RiskEngine()
    
    try:
        # Fetch multi-model traffic
        traffic_data = {}
        for model in ["optimistic", "best_guess", "pessimistic"]:
            res = traffic.get_route(origin, destination, model, departure_time=scheduled_time)
            if res is None:
                raise ValueError(f"Traffic Engine failed to retrieve {model} data.")
            traffic_data[model] = res
            
        # Extract polyline from best_guess model for WeatherEngine. 
        route_polyline = traffic_data['best_guess'].get('polyline')
        if not route_polyline:
            raise ValueError("Could not retrieve route geometry for weather sampling.")
        
        # Fetch weather along route.
        weather_report = weather.get_route_weather(route_polyline)

        # Run risk analysis
        final_report = risk.evaluate_trip(traffic_data, weather_report, buffer_mins)

        # Display dashboard
        display_dashboard(origin, destination, buffer_mins, final_report, scheduled_time)
   
    except Exception as e:
        print(f"\n\033[91m[!] CRITICAL ERROR: {e}\033[0m")

def display_dashboard(origin, dest, buffer, report, departure_time):
    # Convert Unix integer back to human-readable string.
    readable_time = datetime.fromtimestamp(departure_time).strftime('%I:%M %p')

    # ANSI Color Codes.
    BLUE, CYAN, RESET = "\033[94m", "\033[96m", "\033[0m"
    BOLD, RED, GREEN = "\033[1m", "\033[91m", "\033[92m"
    
    color = RED if report['risk'] in ["HIGH", "CRITICAL"] else GREEN
    
    print("\n" + "="*60)
    print(f"{BOLD}FLIGHT-RISK TERMINAL v1.0{RESET}".center(68))
    print("="*60)
    print(f" ROUTE:     {origin} -> {dest}")
    print(f" DEPARTURE: {readable_time} (Leaving Later)")
    print(f" WINDOW:    {buffer} minutes to departure")
    print("-" * 60)
    
    print(f"{BOLD}ANALYSIS RESULTS:{RESET}")
    print(f"  - Weather Penalty:  {report['multiplier']}x")
    print(f"  - Adjusted ETA:     {report['adjusted_eta']} mins")
    print(f"  - Model Confidence: {report['confidence']}%")
    print(f"  - Safety Margin:    {report['buffer']} mins remaining")
    
    print("-" * 60)
    print(f" FINAL STATUS: {BOLD}{color}{report['risk']}{RESET}")
    
    if report['risk'] != "LOW":
        print(f"{RED}{BOLD} RECOMMENDATION: Adjust departure time immediately.{RESET}")
    else:
        print(f"{GREEN} RECOMMENDATION: Departure window is safe.{RESET}")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Test Case
    run_assessment("Stony Brook University, NY", "JFK Airport, NY", 120)

