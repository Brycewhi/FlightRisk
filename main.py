"""
FLIGHT RISK 

Goal: Quantify the probability of a missed flight by synthesizing 
Traffic Variance, Geospatial Weather, and Airport Congestion.

This script acts as the central controller, managing the data flow 
between the TrafficEngine and the WeatherEngine.
"""
from traffic_engine import TrafficEngine
from weather_engine import WeatherEngine

def run_flight_risk_analysis():
    # Initialize specialist engines
    traffic = TrafficEngine()
    weather = WeatherEngine()
    
    # Define route parameters (Stony Brook to JFK)
    home = "Stony Brook University, NY"
    jfk = "JFK Airport, NY"
    
    print(f"Initializing Full Analysis: {home} -> {jfk}\n")

    # STEP 1: Traffic Variance Check
    # We use the 'pessimistic' model to establish the worst-case travel time.
    route_res = traffic.get_route(home, jfk, model="pessimistic")
    
    if route_res:
        print("Traffic Analysis Complete")
        print(f"   Estimated Time (Pessimistic): {route_res['human_readable']}")
        print(f"   Raw Travel Time: {route_res['seconds']} seconds")
        
        # STEP 2: Geospatial Weather
        # Passing the route polyline to the weather engine for spatial sampling.
        print("\nAnalyzing weather conditions at 3 points along the route...\n")
        weather_report = weather.get_route_weather(route_res['polyline'])
        
        if weather_report:
            # Iterating through sampled points (Start, Midpoint, Destination)
            for location, data in weather_report.items():
                # Displaying specific town/area names provided by the API
                print(f"Location: {location} ({data['location_name']})")
                print(f"   Condition: {data['condition']} ({data['description']})")
                print(f"   Temperature: {data['temp']} F")
        else:
            print("Warning: Weather analysis unavailable. Check API key status.")
            
    else:
        print("Error: Route could not be analyzed. Check address strings.")
    
    
if __name__ == "__main__":
    run_flight_risk_analysis()