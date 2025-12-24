from traffic_engine import TrafficEngine
from weather_engine import WeatherEngine
from risk_engine import RiskEngine

def main():
    # Initialize engines.
    traffic = TrafficEngine()
    weather = WeatherEngine()
    risk = RiskEngine()

    # We create a dictionary to store the 3 different traffic scenarios.
    models = ["optimistic", "best_guess", "pessimistic"]
    traffic_data = {}
    
    # Fetch traffic data for 3 models.
    for m in models:
        # We call traffic engine 3 times, once for each model.
        traffic_data[m] = traffic.get_route("Stony Brook, NY", "JFK Airport, NY", model=m)
    
    # 3. Get Weather (Using the path from one of the traffic results).
    route_polyline = traffic_data['best_guess']['polyline']
    weather_report = weather.get_route_weather(route_polyline)

    # 4. Calculate risk
    assessment = risk.evaluate_trip(traffic_data, weather_report, buffer_mins=120)

    # 5. Print results.
    print(f"Weather Impact Multiplier: {assessment['multiplier']}x")
    print(f"Statistical Confidence:    {assessment['confidence']}%")
    print(f"Final Risk Level:          {assessment['risk']}")

if __name__ == "__main__":
    main()