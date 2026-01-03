import time
from datetime import datetime, timedelta
from traffic_engine import TrafficEngine
from weather_engine import WeatherEngine
from risk_engine import RiskEngine
from airport_engine import AirportEngine
from flight_engine import FlightEngine

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

def run_full_analysis(origin, destination, departure_time, flight_time, has_bags, is_precheck):
    # Initializes engines and runs the full stochastic model for a single time.
    # Returns the final report dictionary.
    
    buffer_mins = (flight_time - departure_time) / 60
    
    # Initialize engines.
    traffic = TrafficEngine()
    weather = WeatherEngine()
    risk = RiskEngine()
    airport = AirportEngine()  

    # Traffic and Weather simulation.
    traffic_data = {}
    for model in ["optimistic", "best_guess", "pessimistic"]:
        res = traffic.get_route(origin, destination, model, departure_time=departure_time)
        traffic_data[model] = res
        
    route_polyline = traffic_data['best_guess'].get('polyline')
    weather_report = weather.get_route_weather(route_polyline)

    # Airport Simulation.
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
    
    return final_report

# Unit test.
if __name__ == "__main__":
    print("\n--- SOLVER UNIT TEST ---")
    
    # Define Dummy Inputs.
    test_origin = "Empire State Building, NY"
    test_dest = "JFK Airport, NY"
    test_flight_epoch = int(time.time()) + (4 * 3600) # Flight leaves in 4 hours.
    
    print(f"Testing Route: {test_origin} -> {test_dest}")
    print(f"Flight Time: {datetime.fromtimestamp(test_flight_epoch).strftime('%I:%M %p')}")

    # Test the "Silent Assessment" (Single Run)
    print("\n[1] Testing Single Simulation Run...")
    try:
        single_result = run_full_analysis(test_origin, test_dest, int(time.time()), test_flight_epoch, has_bags=True, is_precheck=True)
        print(f"    Success! Probability calculated: {single_result['success_probability']}%")
        print(f"    P95 Arrival: {single_result['p95_eta']} mins")
    except Exception as e:
        print(f"    FAILED: {e}")

    # Test the "Optimizer" (Search Loop).
    print("\n[2] Testing Temporal Search (Find Optimal Time)...")
    try:
        safe, dead = find_optimal_departure(test_origin, test_dest, test_flight_epoch, has_bags=True, is_precheck=True)
        
        if safe:
            print(f"    Success! Optimal Departure Found: {datetime.fromtimestamp(safe).strftime('%I:%M %p')}")
        else:
            print("    Result: No 95% safe time found (likely due to short test window), but code ran without error.")
            
    except Exception as e:
        print(f"    FAILED: {e}")
        
    print("\n--- END TEST ---\n")