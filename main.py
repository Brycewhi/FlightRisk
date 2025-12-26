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
    YELLOW = "\033[93m"
    
    color = RED if report['risk'] in ["HIGH", "CRITICAL"] else GREEN
    
    print("\n" + "="*60)
    print(f"{BOLD}FLIGHT-RISK TERMINAL v2.0 (STOCHASTIC){RESET}".center(68))
    print("="*60)
    print(f" ROUTE:     {origin} -> {dest}")
    print(f" DEPARTURE: {readable_time} (Leaving Later)")
    print(f" WINDOW:    {buffer} minutes to departure")
    print("-" * 60)
    
    print(f"{BOLD}STATISTICAL ANALYSIS RESULTS:{RESET}")
    print(f"  - Weather Multiplier: {report['multiplier']}x")
    print(f"  - Avg Arrival Time:   {report['avg_eta']} mins")
    print(f"  - 95% Safe Arrival:   {report['p95_eta']} mins")
    print(f"  - Volatility (Std): {report['std_dev']} mins")
    
    # Highlight success prob metric. 
    prob_color = GREEN if report['success_probability'] > 90 else YELLOW if report['success_probability'] > 75 else RED
    print(f"  - Success Probability: {BOLD}{prob_color}{report['success_probability']}%{RESET}")

    # Calculate Safety Margin (based on P95).
    print(f"  - Safety Margin:      {report['buffer_remaining']} mins remaining (95% CI)")
    
    # Determine final risk.
    print("-" * 60)
    print(f" FINAL STATUS: {BOLD}{color}{report['risk']}{RESET}")
    
    # Recommendations based on probability.
    if report['risk'] != "LOW":
        print(f"{RED}{BOLD} RECOMMENDATION: Risk of missing flight is {100 - report['success_probability']}%.{RESET}")
        print(f"{RED} ADVICE: Leave {abs(int(report['buffer_remaining'])) + 15} mins earlier than planned.{RESET}")
    else:
        print(f"{GREEN} RECOMMENDATION: High statistical probability of success.{RESET}")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Test Case
    run_assessment("Stony Brook University, NY", "JFK Airport, NY", 120)

